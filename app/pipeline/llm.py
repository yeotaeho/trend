# LLM 관문 (3단계) — 본문 보강(trafilatura) 후 Claude 로 요약·태깅·알릴 가치 판단

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
import trafilatura
from anthropic import AsyncAnthropic

from app.config import PolicyConfig, Rules, get_settings
from app.db.models import Item
from app.log import get_logger
from app.schemas import LLMVerdict

ENRICH_MIN_CHARS = 300
ENRICH_TIMEOUT = 10.0
PROMPT_BODY_CHARS = 2000
MAX_REDIRECTS = 5

SYSTEM_PROMPT = """\
너는 개인용 개발 트렌드 알림기의 마지막 관문이다.
주어진 항목이 이 사용자에게 알릴 가치가 있는지 판단하고, 한국어로 요약한다.

사용자 정책:
{policy}

판단 기준
- worth_notifying: 새 모델·릴리즈·기법·도구처럼 사용자가 알아야 할 변화면 true.
  홍보·구인·잡담·이미 널리 알려진 내용이면 false.
- importance: 5=당장 알아야 할 큰 변화, 4=중요한 릴리즈·발표, 3=알아두면 좋음,
  2=참고, 1=거의 무의미.
  논문은 코드·가중치·데모가 공개됐거나 사용자 스택에 바로 적용할 수 있는 구체적 기법일 때만 4 이상.
  서베이·포지션·전망·벤치마크 제안은 아무리 주제가 맞아도 3 이하.
- title_ko: `[태그] 무엇 — 핵심 한 줄` 형식. 태그 예) 새 모델, 릴리즈, MCP, 기법, 커뮤니티, 영상.
- summary_ko: 2~3줄. 무엇이 달라졌고 왜 중요한지. 원문에 없는 내용을 지어내지 않는다.
- tags: 소문자 영문 키워드 2~5개.
- "유사 피드백" 은 사용자가 비슷한 글에 남긴 👍/👎 다. 참고하되, 이 항목 자체의 변화 크기와
  새로움을 우선한다. 같은 출처·같은 화자라는 이유만으로 같은 판정을 내리지 않는다.
"""

USER_TEMPLATE = """\
소스: {source}
제목: {title}
{examples}본문:
{body}
"""

log = get_logger(__name__)


@dataclass(slots=True)
class LLMResult:
    verdict: LLMVerdict
    model: str
    tokens_in: int
    tokens_out: int


def all_global(addresses: list[str]) -> bool:
    """전부 공인 주소여야 연다. 사설·루프백·링크로컬(VM 메타데이터)·예약 대역이
    하나라도 있으면 막는다. 빈 목록(해석 실패)도 막는다.
    """
    return bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses)


async def resolve(host: str) -> list[str]:
    """호스트의 주소 전부. 이벤트 루프의 getaddrinfo 라 블로킹하지 않는다."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except socket.gaierror:
        return []
    return sorted({str(info[4][0]) for info in infos})


async def _allowed(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    return all_global(await resolve(parts.hostname))


async def enrich_body(url: str) -> str | None:
    """body 가 짧을 때만 원문을 받아 본문을 추출한다. 실패해도 예외를 올리지 않는다.

    피드·HN 이 준 링크는 사용자 제출 URL 이다. 사설·링크로컬 주소를 가리킬 수 있으므로
    리다이렉트를 직접 따라가며 홉마다 목적지를 검사한다.
    ponytail: 해석과 연결 사이의 DNS 리바인딩은 막지 않는다. 필요해지면 연결된 소켓의
    peer 주소를 재검사한다.
    """
    try:
        async with httpx.AsyncClient(timeout=ENRICH_TIMEOUT, follow_redirects=False) as client:
            for _ in range(MAX_REDIRECTS + 1):
                if not await _allowed(url):
                    log.info("llm.enrich_blocked", url=url)
                    return None
                response = await client.get(url, headers={"User-Agent": "tech-radar/0.1"})
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                return trafilatura.extract(response.text) or None
        log.info("llm.enrich_too_many_redirects", url=url)
        return None
    except Exception as exc:
        log.info("llm.enrich_failed", url=url, error=str(exc))
        return None


async def body_for_judge(item: Item) -> tuple[str | None, bool]:
    """본문이 짧으면 원문을 받아 보강한다. (본문, 보강 실패 여부). 결과는 summary_raw 에 남긴다."""
    body = item.summary_raw
    if body and len(body) >= ENRICH_MIN_CHARS:
        return body, False
    enriched = await enrich_body(item.url)
    if enriched:
        item.summary_raw = enriched[:3000]
        return enriched, False
    return body, True


def client() -> AsyncAnthropic:
    # SDK 기본 재시도(429·5xx 2회)를 끈다. 재시도는 예약(reserve_call) 없이 나가는 호출이라
    # 일일 상한을 깨뜨린다. 기반 실패는 항목을 NEW 로 남기고 다음 잡이 새 예약으로 다시 시도한다.
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key, max_retries=0)


def render_policy(policy: PolicyConfig) -> str:
    """선별·판정 프롬프트가 같은 문장을 읽는다."""
    parts = ["관심:", policy.interests.strip(), "관심 없음:", policy.not_interested.strip()]
    if policy.focus_repos:
        parts.append("특히 주목하는 저장소: " + ", ".join(policy.focus_repos))
    if policy.focus_stack:
        parts.append("특히 주목하는 스택·용어: " + ", ".join(policy.focus_stack))
    if policy.categories:
        # 앱에서 고른 taxonomy slug. 힌트일 뿐 거름망이 아니다.
        parts.append("관심 카테고리: " + ", ".join(policy.categories))
    return "\n".join(parts)


async def judge(
    rules: Rules, *, source: str, title: str, body: str | None, examples: str = ""
) -> LLMResult:
    """한 번의 호출로 판단·요약·태깅을 구조화 출력으로 받는다. examples 는 최근접 피드백 한 줄."""
    settings = get_settings()
    response = await client().messages.parse(
        model=settings.llm_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(policy=render_policy(rules.policy)),
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    source=source,
                    title=title,
                    examples=f"유사 피드백: {examples}\n" if examples else "",
                    body=(body or "")[:PROMPT_BODY_CHARS],
                ),
            }
        ],
        output_format=LLMVerdict,
    )
    verdict = response.parsed_output
    assert verdict is not None  # output_format 을 준 호출은 항상 파싱된 결과를 준다.
    return LLMResult(
        verdict=verdict,
        model=response.model,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
    )
