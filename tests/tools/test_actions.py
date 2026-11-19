import json
from types import SimpleNamespace

import pytest

from apollo.retrieval.tables import CategoryChange, DivisionStats, FineRecord
from apollo.tools import _runtime, actions


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch, tmp_path):
    records = SimpleNamespace(
        fines=[
            FineRecord(
                15, "Disobeying Traffic Light Or Stop Sign", 10000, 6, "Section 52(2)(a)", 1
            ),
        ],
        divisions=[
            DivisionStats("Kingston Central", {"murder": CategoryChange(16, 8)}, ()),
            DivisionStats("St. Andrew South", {"murder": CategoryChange(68, 47)}, ()),
            DivisionStats("Grand Total", {}, ()),
        ],
    )
    monkeypatch.setattr(_runtime, "get_records", lambda: records)
    monkeypatch.setattr(_runtime, "get_settings", lambda: SimpleNamespace(actions_dir=tmp_path))
    return tmp_path


def _log(folder, kind):
    return [json.loads(line) for line in (folder / f"{kind}.jsonl").read_text().splitlines()]


def test_fine_notice_uses_the_official_amount(fake_runtime) -> None:
    result = actions.issue_fine_notice.invoke(
        {"section": "52(2)(a)", "offence": "disobeyed a stop sign", "location": "Half Way Tree"}
    )
    assert "$10,000" in result and "6 demerit points" in result
    entry = _log(fake_runtime, "fine_notices")[0]
    assert entry["fine"] == 10000 and entry["reference"].startswith("FN-")


def test_notice_without_location_records_none(fake_runtime) -> None:
    result = actions.issue_fine_notice.invoke({"section": "52(2)(a)", "offence": "stop sign"})
    assert result.endswith("6 demerit points.")
    assert _log(fake_runtime, "fine_notices")[0]["location"] is None


def test_unknown_section_issues_nothing(fake_runtime) -> None:
    with pytest.raises(ValueError):
        actions.issue_fine_notice.invoke({"section": "999(9)", "offence": "x", "location": "y"})
    assert not (fake_runtime / "fine_notices.jsonl").exists()


def test_email_is_validated_and_logged(fake_runtime) -> None:
    with pytest.raises(ValueError):
        actions.notify_email.invoke({"to": "not-an-email", "subject": "s", "body": "b"})
    actions.notify_email.invoke(
        {"to": "traffic@jcf.gov.jm", "subject": "Notice FN-1", "body": "Stop sign offence."}
    )
    assert _log(fake_runtime, "outbox")[0]["to"] == "traffic@jcf.gov.jm"


def test_sighting_location_must_be_a_division(fake_runtime) -> None:
    result = actions.log_sighting_report.invoke(
        {"suspect_name": "Dave Edwards", "location": "st andrew south"}
    )
    assert "St. Andrew South" in result
    with pytest.raises(ValueError):
        actions.log_sighting_report.invoke({"suspect_name": "Dave Edwards", "location": "Mars"})


def test_high_risk_names_cover_every_action() -> None:
    assert actions.HIGH_RISK_TOOL_NAMES == {
        "issue_fine_notice",
        "notify_email",
        "log_sighting_report",
    }
