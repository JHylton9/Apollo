from apollo.text import clean_text, normalized, stable_id


def test_clean_text_normalizes_spacing() -> None:
    assert clean_text(" A   B\n\n\nC ") == "A B\n\nC"


def test_normalized_handles_currency_and_punctuation() -> None:
    assert normalized("Tip: $20,000 / 6 points") == "tip 20 000 6 points"


def test_stable_id_is_deterministic() -> None:
    assert stable_id("a", 1) == stable_id("a", 1)
    assert stable_id("a", 1) != stable_id("a", 2)
