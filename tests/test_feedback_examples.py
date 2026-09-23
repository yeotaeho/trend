# 피드백 사례 테스트 — 👍/👎 와 제목을 한 줄로, 판정 결정 행에 사례 {item_id, verdict, title} 저장

from datetime import UTC, datetime
from types import SimpleNamespace

from app.config import Rules
from app.db.models import Decision, Item, Source
from app.jobs import notify, pipeline
from app.pipeline.dedupe import Verdict
from app.pipeline.feedback import FeedbackExample, examples_details, format_examples
from app.pipeline.llm import LLMResult
from app.pipeline.triage import TriageItem
from app.schemas import Category, Kind, LLMVerdict

EXAMPLES = [
    FeedbackExample(11, "useful", "[릴리즈] uv 0.12.9"),
    FeedbackExample(12, "useless", "Original English title"),
]


def test_format_examples():
    assert format_examples(EXAMPLES) == '👍 "[릴리즈] uv 0.12.9" · 👎 "Original English title"'


def test_empty_is_empty_string():
    assert format_examples([]) == ""


def test_examples_details_shape():
    assert examples_details(EXAMPLES) == [
        {"item_id": 11, "verdict": "useful", "title": "[릴리즈] uv 0.12.9"},
        {"item_id": 12, "verdict": "useless", "title": "Original English title"},
    ]


class _Session:
    """add·commit 만 쓰는 판정 경로용 가짜 세션."""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        pass

    def llm_decision(self) -> Decision:
        (row,) = [d for d in self.added if isinstance(d, Decision) and d.stage == "llm"]
        return row


def _patch_judge_path(monkeypatch, module, examples: list[FeedbackExample], prompts: list[str]):
    async def body_for_judge(_item):
        return "body", False

    async def reserve_call(_kind):
        return "call-1"

    async def nearest(_session, _item_id, *, k):
        return examples

    async def judge(_rules, *, source, title, body, examples):
        prompts.append(examples)
        verdict = LLMVerdict(
            worth_notifying=False,
            importance=2,
            category=Category.UNKNOWN,
            title_ko="t",
            summary_ko="s",
        )
        return LLMResult(verdict=verdict, model="m", tokens_in=1, tokens_out=1)

    monkeypatch.setattr(module.llm, "body_for_judge", body_for_judge)
    monkeypatch.setattr(module.llm, "judge", judge)
    monkeypatch.setattr(module, "reserve_call", reserve_call)
    monkeypatch.setattr(module, "nearest_feedback", nearest)


def _item() -> Item:
    return Item(id=1, title="item", raw={}, published_at=datetime.now(UTC), score=0.4)


async def test_judge_decision_keeps_examples(monkeypatch):
    prompts: list[str] = []
    _patch_judge_path(monkeypatch, pipeline, EXAMPLES, prompts)
    session = _Session()
    tri = TriageItem(idx=1, relevance=1.0, reason="r", kind=Kind.RELEASE_MAJOR, topics=[])
    called = await pipeline._judge(
        session,
        Rules(),
        _item(),
        Source(name="rss:x", trust_score=1.0),
        Verdict("independent", 1, 1),
        tri,
    )
    assert called
    assert session.llm_decision().details["examples"] == examples_details(EXAMPLES)
    assert prompts == [format_examples(EXAMPLES)]  # 프롬프트에 넣은 사례와 저장한 사례가 같다


async def test_judge_without_examples_stores_empty_list(monkeypatch):
    _patch_judge_path(monkeypatch, pipeline, [], [])
    session = _Session()
    tri = TriageItem(idx=1, relevance=1.0, reason="r", kind=Kind.RELEASE_MAJOR, topics=[])
    await pipeline._judge(
        session,
        Rules(),
        _item(),
        Source(name="rss:x", trust_score=1.0),
        Verdict("independent", 1, 1),
        tri,
    )
    assert session.llm_decision().details["examples"] == []


async def test_explore_decision_keeps_examples(monkeypatch):
    _patch_judge_path(monkeypatch, notify, EXAMPLES, [])

    async def not_sent(*_args):
        return False

    async def candidate(*_args):
        return (_item(), Source(name="rss:x"))

    monkeypatch.setattr(notify, "_explore_sent_today", not_sent)
    monkeypatch.setattr(notify, "_explore_candidate", candidate)
    session = _Session()
    noon_kst = datetime(2026, 9, 24, 3, tzinfo=UTC)
    sent = await notify._explore(
        session,
        Rules(),
        SimpleNamespace(channel="discord"),
        now=noon_kst,
    )
    decision = session.llm_decision()
    assert not sent and decision.details["explore"] is True
    assert decision.details["examples"] == examples_details(EXAMPLES)
