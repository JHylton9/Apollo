"""A scripted chat model so agent graphs can be tested without calling Foundry."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel


class ScriptedModel(GenericFakeChatModel):
    """Returns the given messages in order and accepts bind_tools like a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def scripted(*messages):
    return ScriptedModel(messages=iter(messages))
