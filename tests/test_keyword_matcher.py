from keyword_matcher.matcher import KeywordMatcher


def test_plain_substring_match():
    m = KeywordMatcher(["python"])
    assert m.find_matches("looking for a python dev") == ["python"]
    assert m.find_matches("nothing here") == []


def test_case_insensitive():
    m = KeywordMatcher(["Django"])
    assert m.find_matches("we use DJANGO in prod") == ["Django"]


def test_phrase_needs_all_words():
    m = KeywordMatcher(["web design"])
    assert m.find_matches("need web design for a shop") == ["web design"]
    assert m.find_matches("a nice web page") == []


def test_fuzzy_catches_a_typo():
    m = KeywordMatcher(["marketing"])
    assert m.find_matches("marketng budget", fuzz_ratio=80) == ["marketing"]


def test_result_is_deduped():
    m = KeywordMatcher(["python", "go"])
    assert m.find_matches("python python and go, go, go") == ["python", "go"]


def test_empty_inputs():
    assert KeywordMatcher([]).find_matches("anything") == []
    assert KeywordMatcher(["python"]).find_matches("") == []
