import re
from typing import Iterable

_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


class KeywordMatcher:
    def __init__(self, keywords: Iterable[str] = ()):
        self.set_keywords(keywords)

    def set_keywords(self, keywords: Iterable[str]) -> None:
        self.keywords: list[str] = [k.strip().lower() for k in keywords if k and k.strip()]

    def find_matches(self, text: str) -> list[str]:
        if not text or not self.keywords:
            return []
        haystack = " ".join(_WORD_RE.findall(text.lower()))
        out = []
        for kw in self.keywords:
            if kw in haystack and kw not in out:
                out.append(kw)
        return out
