# LLM 관문 (3단계) — 본문 보강(trafilatura) 후 Claude 로 요약·태깅·알릴 가치 판단

from __future__ import annotations

from dataclasses import dataclass

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
- title_ko: `[태그] 무엇 — 핵심 한 줄` 형식. 태그 예) 새 모델, 릴리즈, MCP, 기법, 커뮤니티, 영상.
- summary_ko: 2~3줄. 무엇이 달라졌고 왜 중요한지. 원문에 없는 내용을 지어내지 않는다.
- tags: 소문자 영문 키워드 2~5개.
- "유사 피드백" 은 사용자가 비슷한 글에 남긴 👍/👎 다.
  importance 와 worth_notifying 에 강하게 반영한다.
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


async def enrich_body(url: str) -> str | None:
    """body 가 짧을 때만 원문을 받아 본문을 추출한다. 실패해도 예외를 올리지 않는다."""
    try:
        async with httpx.AsyncClient(timeout=ENRICH_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "tech-radar/0.1"})
            response.raise_for_status()
        return trafilatura.extract(response.text) or None
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
