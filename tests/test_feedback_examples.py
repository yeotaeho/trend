# 피드백 사례 서식 테스트 — 👍/👎 와 제목을 한 줄로

from app.pipeline.feedback import FeedbackExample, format_examples


def test_format_examples():
    text = format_examples(
        [FeedbackExample("useful", "[릴리즈] uv 0.12.9"), FeedbackExample("useless", "[영상] 잡담")]
    )
    assert text == '👍 "[릴리즈] uv 0.12.9" · 👎 "[영상] 잡담"'


def test_empty_is_empty_string():
    assert format_examples([]) == ""
