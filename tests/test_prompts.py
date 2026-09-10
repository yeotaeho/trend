# 프롬프트 문구 테스트 — 피드백 사례 과일반화 문구 제거, 판정의 논문 눈금

from app.pipeline.llm import SYSTEM_PROMPT as JUDGE_PROMPT
from app.pipeline.triage import SYSTEM_PROMPT as TRIAGE_PROMPT


def test_feedback_is_a_hint_not_an_order():
    # 같은 채널·같은 화자라는 이유만으로 같은 판정을 내리면 안 된다.
    assert "강하게" not in TRIAGE_PROMPT
    assert "강하게" not in JUDGE_PROMPT


def test_judge_has_a_rubric_for_papers():
    # 2026-09-08 SDLC 서베이가 importance 4 를 받았다.
    # 논문은 공개 산출물이나 직접 적용 가능성이 있어야 4.
    assert "논문" in JUDGE_PROMPT
    assert "서베이" in JUDGE_PROMPT
