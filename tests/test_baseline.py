from apollo.pipelines.baseline import BaselinePipeline


def test_ocr_is_only_preferred_when_it_adds_content() -> None:
    assert BaselinePipeline._select_text("long enough", "short") == "long enough"
    assert BaselinePipeline._select_text("short", "substantially longer OCR text") == (
        "substantially longer OCR text"
    )
