from typing import Any, cast

import pytest

from apollo import llm


def test_base_url_accepts_both_endpoint_forms() -> None:
    expected = "https://jcf.openai.azure.com/openai/v1"
    assert llm.foundry_base_url("https://jcf.openai.azure.com/") == expected
    assert llm.foundry_base_url("https://jcf.openai.azure.com/openai/v1") == expected


def test_missing_settings_give_a_clear_error(monkeypatch) -> None:
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    for name in llm.REQUIRED:
        monkeypatch.delenv(name, raising=False)
    llm.get_chat_model.cache_clear()
    with pytest.raises(RuntimeError, match="AZURE_OPENAI_ENDPOINT"):
        llm.get_chat_model()


def test_model_is_built_from_environment(monkeypatch) -> None:
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://jcf.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("APOLLO_CHAT_DEPLOYMENT", "apollo-gpt")
    llm.get_chat_model.cache_clear()
    model = cast(Any, llm.get_chat_model())
    assert model.model_name == "apollo-gpt"
    assert str(model.openai_api_base) == "https://jcf.openai.azure.com/openai/v1"
    assert model.temperature == 0.0