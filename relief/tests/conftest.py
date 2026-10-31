import pytest

from relief.agent.service import Agent
from relief.config import Settings


@pytest.fixture(scope="session")
def _base(tmp_path_factory, monkeypatch_session=None):
    return tmp_path_factory.mktemp("var")


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("RELIEF_VAR_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("RELIEF_EMBEDDER", "hashing")
    return Settings()


@pytest.fixture()
def agent(settings, tmp_path):
    return Agent(settings, llm=None, checkpoint_path=tmp_path / "ck.sqlite")


class ScriptedLLM:
    """Stands in for the model. `replies` maps schema name to a dict or an exception to raise."""
    model = "scripted"

    def __init__(self, replies):
        self.replies, self.calls = replies, []

    def chat_json(self, system, user, schema):
        self.calls.append(schema.__name__)
        import json
        from relief.llm.client import LLMOutputError
        r = self.replies.get(schema.__name__)
        if isinstance(r, Exception):
            raise r
        if r is None and schema.__name__ == "ToolChoice":  # default: take the first allowed tool, like a sensible model
            r = {"tool": next(iter(json.loads(user)["allowed"])), "reason": "scripted"}
        if r is None:
            raise LLMOutputError("scripted: no reply for " + schema.__name__)
        return schema.model_validate(r)


def make_case(**kw):
    from relief.eval.cases import _base
    from relief.contracts.schemas import CaseInput
    base = _base(0)  # a clean, consistent file: only what a test changes can be a blocker
    base.update(kw)
    return CaseInput.model_validate(base)
