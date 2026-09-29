# 프롬프트 문구 테스트 — 피드백 사례 과일반화 문구 제거, 판정의 논문 눈금, 분류표·관심 카테고리 주입

from app.config import DEFAULT_TAXONOMY, PolicyConfig, get_rules
from app.pipeline.llm import SYSTEM_PROMPT as JUDGE_PROMPT
from app.pipeline.llm import render_policy
from app.pipeline.triage import SYSTEM_PROMPT as TRIAGE_PROMPT
from app.pipeline.triage import system_prompt


def test_feedback_is_a_hint_not_an_order():
    # 같은 채널·같은 화자라는 이유만으로 같은 판정을 내리면 안 된다.
    assert "강하게" not in TRIAGE_PROMPT
    assert "강하게" not in JUDGE_PROMPT


def test_judge_has_a_rubric_for_papers():
    # 2026-09-08 SDLC 서베이가 importance 4 를 받았다.
    # 논문은 공개 산출물이나 직접 적용 가능성이 있어야 4.
    assert "논문" in JUDGE_PROMPT
    assert "서베이" in JUDGE_PROMPT


def test_rendered_prompts_carry_taxonomy_and_categories():
    # 실제 rules.yaml 로 렌더한 스냅샷.
    # 선별은 분류표 12개를, 두 프롬프트 모두 관심 카테고리 줄을 받는다.
    rules = get_rules()
    triage = system_prompt(rules)
    judge = JUDGE_PROMPT.format(policy=render_policy(rules.policy))
    assert len(rules.policy.taxonomy) == 12
    assert [t for t in rules.policy.taxonomy if f"\n- {t}" in triage] == rules.policy.taxonomy
    line = "관심 카테고리: " + ", ".join(rules.policy.categories)
    assert line in triage and line in judge


def test_categories_line_lists_selected_slugs_only():
    text = render_policy(PolicyConfig(categories=["agent", "video"]))
    assert text.endswith("관심 카테고리: agent, video")
    assert "llm-model" not in text


def test_categories_default_to_whole_taxonomy():
    text = render_policy(PolicyConfig())
    assert "관심 카테고리: " + ", ".join(DEFAULT_TAXONOMY) in text
