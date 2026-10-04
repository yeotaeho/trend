# 결정 행 판단 기준 테스트 — 점수 결정의 당시 임계값, 잡 시작 때 정한 설정 이력 id·배포 커밋(#39)
from datetime import UTC, datetime
from types import SimpleNamespace

from app.config import get_rules
from app.db import prefs
from app.db.models import Decision, Item, Source
from app.db.users import DEFAULT_USER_ID
from app.jobs import pipeline
from app.pipeline.dedupe import Verdict
from app.pipeline.triage import TriageItem
from app.schemas import Kind, Stage

CRITERIA = {"settings_rev": 7, "git_sha": "abc1234"}


class _Session:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


async def test_score_decision_keeps_threshold_and_criteria():
    rules = get_rules()
    item = Item(id=1, title="t", published_at=datetime.now(UTC), raw={})
    source = Source(name="rss:x", type="rss", config={}, trust_score=0.0)
    tri = TriageItem(idx=0, relevance=0.0, reason="무관", kind=Kind.OTHER, topics=[])
    verdict = Verdict(kind="independent", cluster_id=1, mention_count=0)
    session = _Session()

    token = pipeline._criteria.set(CRITERIA)
    try:
        judged = await pipeline._judge(session, rules, item, source, verdict, tri)  # type: ignore[arg-type]
    finally:
        pipeline._criteria.reset(token)

    assert judged is False  # 점수 탈락이라 판정을 부르지 않는다
    (decision,) = session.added
    assert isinstance(decision, Decision)
    assert (decision.stage, decision.passed) == (Stage.SCORE.value, False)
    assert decision.details["threshold"] == rules.scoring.threshold
    assert {k: decision.details[k] for k in CRITERIA} == CRITERIA


def test_record_outside_a_job_adds_no_criteria():
    decision = pipeline._record(Item(id=1, title="t"), Stage.RULE, True, {"reason": "x"})
    assert decision.details == {"reason": "x"}


async def test_decision_criteria_reads_latest_revision_and_git_sha(monkeypatch):
    async def latest(_session, user_id):
        assert user_id == DEFAULT_USER_ID
        return 7

    monkeypatch.setattr(prefs, "latest_revision_id", latest)
    monkeypatch.setattr(pipeline, "get_settings", lambda: SimpleNamespace(git_sha="abc1234"))
    assert await pipeline.decision_criteria(None) == CRITERIA  # type: ignore[arg-type]

    # 로컬은 배포 커밋이 비어 있다. 빈 문자열 대신 null 로 남긴다.
    monkeypatch.setattr(pipeline, "get_settings", lambda: SimpleNamespace(git_sha=""))
    assert (await pipeline.decision_criteria(None))["git_sha"] is None  # type: ignore[arg-type]
