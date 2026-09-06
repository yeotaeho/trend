# LLM 선별 배치 — 25건을 한 호출에 넣어 관련도 0~1 과 이유를 받는다. 정독은 판정이 한다

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from app.config import Rules, get_settings
from app.pipeline.llm import client, render_policy

REASON_CHARS = 200

SYSTEM_PROMPT = """\
너는 개인용 개발 트렌드 알림기의 선별 단계다. 항목마다 "이 사용자가 읽을 후보인가" 를 0~1 로 매긴다.
정독·요약은 다음 단계가 하니 여기서는 관련도만 빠르게 판단한다.

사용자 정책:
{policy}

relevance 눈금
- 0.9 이상: 새 모델·릴리즈·기법·도구의 직접적인 변화. 사용자가 알아야 할 것.
- 0.6: 관심 주제의 일반적인 글. 읽으면 도움이 되지만 변화는 아님.
- 0.3: 주변부. 관심 주제와 스치는 정도.
- 0: 무관, 홍보, 구인, 스폰서, 잡담.
목록에 없는 새 이름·용어라도 문맥이 정책과 맞으면 높게 준다. 키워드가 아니라 뜻으로 판단한다.
"유사 피드백" 이 붙은 항목은 사용자가 비슷한 글에 남긴 👍/👎 이니 강하게 참고한다.
reason 은 20단어 이내 한국어 한 문장.
모든 항목에 대해 idx 를 그대로 돌려준다.
"""


@dataclass(slots=True, frozen=True)
class TriageEntry:
    idx: int
    source: str
    title: str
    snippet: str
    examples: str = ""  # 3단계에서 채운다. 비어 있으면 줄이 붙지 않는다


class TriageItem(BaseModel):
    idx: int
    relevance: float
    reason: str


class TriageBatch(BaseModel):
    items: list[TriageItem]


class TriageBatchError(RuntimeError):
    """응답 전체가 프로토콜에 맞지 않는다. 25건 공통이라 항목 탓이 아니다."""


def build_user_content(entries: list[TriageEntry]) -> str:
    blocks = []
    for e in entries:
        block = f"[{e.idx}] {e.source} | {e.title}"
        if e.snippet:
            block += f"\n{e.snippet}"
        if e.examples:
            block += f"\n    유사 피드백: {e.examples}"
        blocks.append(block)
    return "\n\n".join(blocks)


def parse_triage(
    batch: TriageBatch, expected: list[int]
) -> tuple[dict[int, TriageItem], list[int]]:
    """(유효 결과, 항목 실패 idx). 개수·미지 idx 는 배치 실패다."""
    if len(batch.items) != len(expected):
        raise TriageBatchError(f"응답 {len(batch.items)}건, 기대 {len(expected)}건")
    known = set(expected)
    if any(it.idx not in known for it in batch.items):
        raise TriageBatchError("기대하지 않은 idx 가 있음")

    ok: dict[int, TriageItem] = {}
    for it in batch.items:
        if it.idx in ok or not 0.0 <= it.relevance <= 1.0:
            continue
        ok[it.idx] = TriageItem(idx=it.idx, relevance=it.relevance, reason=it.reason[:REASON_CHARS])
    failed = [idx for idx in expected if idx not in ok]
    return ok, failed


async def call_triage(rules: Rules, entries: list[TriageEntry]) -> TriageBatch:
    """한 번의 호출. 기반 실패(네트워크·5xx·429·인증)는 SDK 예외로 올라온다.

    시스템 블록에 cache_control 을 건다. 다만 캐시는 모델별 최소 접두(수백~수천 토큰) 이상일 때만
    걸리므로 정책 문장이 짧으면 그냥 통과한다. 비용은 없다.
    """
    response = await client().messages.parse(
        model=get_settings().llm_model,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT.format(policy=render_policy(rules.policy)),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": build_user_content(entries)}],
        output_format=TriageBatch,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise TriageBatchError("구조화 출력이 비어 있음")
    return parsed
