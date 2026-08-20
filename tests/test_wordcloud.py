import pytest

from core.errors import TaskCancelled
from core.wordcloud_gen import WordCloudGenerator


def test_cancelled_generation_preserves_the_previous_image():
    generator = WordCloudGenerator()
    assert generator.generate("기존 표현 기존 표현")
    previous = generator.get_wordcloud()
    checks = iter((False, True))

    with pytest.raises(TaskCancelled):
        generator.generate(
            "새로운 표현 새로운 표현",
            cancel_check=lambda: next(checks),
        )

    assert generator.get_wordcloud() is previous
