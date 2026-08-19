import math
import re

from bs4 import BeautifulSoup


WORDS_PER_MINUTE = 225
_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)


def count_content_words(content: str) -> int:
    """Count visible words in article source while excluding HTML markup."""
    if not content:
        return 0
    text = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
    return len(_WORD_RE.findall(text))


def estimate_reading_minutes(content: str, words_per_minute: int = WORDS_PER_MINUTE) -> int:
    """Return a reusable, source-content-only reading-time estimate."""
    if words_per_minute <= 0:
        raise ValueError("words_per_minute must be greater than zero")
    return max(1, math.ceil(count_content_words(content) / words_per_minute))
