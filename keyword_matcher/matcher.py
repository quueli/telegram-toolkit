import re
from typing import Iterable

try:
    from rapidfuzz import fuzz
except Exception:
    import difflib

    class _FuzzFallback:
        @staticmethod
        def ratio(a, b):
            # difflib gives [0, 1], rapidfuzz gives [0, 100]
            return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)

    fuzz = _FuzzFallback()

try:
    import snowballstemmer
    _STEMMER = snowballstemmer.stemmer("russian")
except Exception:
    _STEMMER = None

_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


def _stem(token: str) -> str:
    if _STEMMER is None:
        return token.lower()
    try:
        return _STEMMER.stemWord(token.lower())
    except Exception:
        return token.lower()


class KeywordMatcher:
    def __init__(self, keywords: Iterable[str] = ()):
        self.set_keywords(keywords)

    def set_keywords(self, keywords: Iterable[str]) -> None:
        cleaned = [k.strip() for k in keywords if k and k.strip()]
        self.keywords: list[str] = cleaned
        self.kw_stems: list[list[str]] = []
        for kw in cleaned:
            tokens = _WORD_RE.findall(kw.lower())
            self.kw_stems.append([_stem(t) for t in tokens] if tokens else [_stem(kw)])

    def _text_tokens_stems(self, text: str):
        tokens = _WORD_RE.findall((text or "").lower())
        return tokens, [_stem(t) for t in tokens]

    def find_matches(self, text: str, fuzz_ratio: int = 90) -> list[str]:
        if not text or not self.keywords:
            return []
        tokens, stems = self._text_tokens_stems(text)
        token_set = set(tokens)
        stem_set = set(stems)

        matched = []
        for kw, kw_stems in zip(self.keywords, self.kw_stems):
            if len(kw_stems) == 1:
                keystem = kw_stems[0]
                if keystem in stem_set:
                    matched.append(kw)
                    continue
                if kw.lower() in " ".join(tokens):
                    matched.append(kw)
                    continue
                for t in token_set:
                    if fuzz.ratio(t, kw.lower()) >= fuzz_ratio:
                        matched.append(kw)
                        break
            # a phrase only counts when every word of it is in the text
            elif all(any(fuzz.ratio(st, s) >= fuzz_ratio or st == s for s in stem_set) for st in kw_stems):
                matched.append(kw)

        out, seen = [], set()
        for m in matched:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out
