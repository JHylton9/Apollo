import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from rich.console import Console
from typer.testing import CliRunner

from apollo import cli
from apollo.agents import terminal
from apollo.agents.coordinator import build_coordinator
from apollo.middleware import build_hitl_middleware
from apollo.retrieval.tables import CategoryChange, DivisionStats
from apollo.tools import _runtime

from .fakes import scripted

SIGHTING = {"suspect_name": "Dave Edwards", "location": "Kingston Central", "anonymous": True}


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch, tmp_path):
    divisions = [
        DivisionStats(name, {"murder": CategoryChange(1, 1)}, ())
        for name in ("Kingston Central", "St. Andrew South")
    ]
    records = SimpleNamespace(fines=[], divisions=divisions, murder_counts={})
    monkeypatch.setattr(_runtime, "get_records", lambda: records)
    monkeypatch.setattr(_runtime, "get_settings", lambda: SimpleNamespace(actions_dir=tmp_path))
    return tmp_path


def test_coerce_keeps_argument_types() -> None:
    assert terminal._coerce(True, "no") is False
    assert terminal._coerce(5, "7") == 7
    assert terminal._coerce(None, "") is None
    assert terminal._coerce("Kingston", "St. Andrew South") == "St. Andrew South"


def test_chat_command_edit_flow(monkeypatch, fake_runtime) -> None:
    # Spec test case, end to end through the terminal: edit the location, then resume.
    model = scripted(
        AIMessage(
            content="", tool_calls=[{"name": "log_sighting_report", "args": SIGHTING, "id": "a1"}]
        ),
        AIMessage(content="Sighting report [verified] logged for St. Andrew South."),
    )
    agent = build_coordinator(model, delegation_tools=[], middleware=[build_hitl_middleware()])
    real_session = terminal.ApolloSession
    monkeypatch.setattr(terminal, "ApolloSession", lambda: real_session(agent, "cli-test"))
    monkeypatch.setattr(cli, "console", Console(width=100))
    keystrokes = "\n".join(
        [
            "Log a sighting of Dave Edwards at Kingston Central",
            "e",  # edit
            "suspect_name",  # typing the argument's name is caught and re-asked
            "",  # suspect_name: keep
            "St. Andrew South",  # location: change
            "",  # anonymous: keep
            "exit",
        ]
    )
    result = CliRunner().invoke(cli.app, ["chat"], input=keystrokes + "\n")

    assert result.exit_code == 0, result.output
    assert "Paused: officer review required" in result.output
    output = " ".join(result.output.split())
    assert (
        "For each argument, press Enter to keep the value shown in [brackets], "
        "or type the new value (not the argument name)."
    ) in output
    assert "[verified]" in output
    logged = json.loads((fake_runtime / "sighting_reports.jsonl").read_text())
    assert "That is the argument's name" in result.output
    assert logged["suspect_name"] == "Dave Edwards"
    assert logged["division"] == "St. Andrew South"
    assert logged["anonymous"] is True
