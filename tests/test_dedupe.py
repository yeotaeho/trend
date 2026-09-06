# 중복·관련 분류 테스트 — 임계값, 생존자 기준, 버전 예외, 같은 소스 미집계, NULL 클러스터

from app.config import DedupeConfig
from app.pipeline.dedupe import Candidate, classify, version_tokens

CFG = DedupeConfig()


def cand(id: int, sim: float, source_id: int = 2, cluster_id: int | None = None, title: str = "t"):
    return Candidate(id=id, source_id=source_id, cluster_id=cluster_id, title=title, sim=sim)


def run(dup=None, related=(), title="Claude Fable 5.1 released", source_id=1):
    return classify(
        item_id=100,
        own_source_id=source_id,
        own_title=title,
        dup=dup,
        related=list(related),
        cfg=CFG,
    )


def test_version_tokens():
    assert version_tokens("Next.js v16.4.0-canary.14 released") == {"v16.4.0-canary.14"}
    assert version_tokens("uv 0.12.9 and 0.12.8 compared") == {"0.12.9", "0.12.8"}
    assert version_tokens("no version here") == frozenset()


def test_dup_inherits_cluster_of_survivor():
    v = run(dup=cand(5, 0.97, cluster_id=3))
    assert v.kind == "dup" and v.cluster_id == 3


def test_dup_with_null_cluster_uses_candidate_id():
    v = run(dup=cand(5, 0.97, cluster_id=None))
    assert v.kind == "dup" and v.cluster_id == 5


def test_below_dup_threshold_is_not_dup():
    # 0.93 은 표본에서 "같은 채널의 다른 영상" 이었다. 중복이 아니라 관련이어야 한다.
    v = run(dup=cand(5, 0.93), related=[cand(5, 0.93)])
    assert v.kind == "related" and v.cluster_id == 5


def test_different_version_demotes_dup_to_related():
    v = run(
        dup=cand(5, 0.97, title="Next.js v16.4.0-canary.13"),
        related=[cand(5, 0.97, title="Next.js v16.4.0-canary.13")],
        title="Next.js v16.4.0-canary.14",
    )
    assert v.kind == "related"


def test_missing_version_on_one_side_keeps_dup():
    v = run(dup=cand(5, 0.97, title="Next.js canary release"), title="Next.js v16.4.0-canary.14")
    assert v.kind == "dup"


def test_independent_gets_own_id():
    v = run()
    assert v.kind == "independent" and v.cluster_id == 100 and v.mention_count == 1


def test_mention_count_excludes_own_source_but_clusters_still_inherit():
    v = run(related=[cand(5, 0.85, source_id=1, cluster_id=9)])
    assert v.kind == "related" and v.cluster_id == 9 and v.mention_count == 1


def test_mention_count_distinct_other_sources():
    v = run(
        related=[cand(5, 0.9, source_id=2), cand(6, 0.85, source_id=3), cand(7, 0.81, source_id=2)]
    )
    assert v.mention_count == 3
