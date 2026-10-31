"""Local language-model client (Ollama). The model is used only for language tasks:
choosing among fixed options, ranking fixed candidates, and writing one short summary sentence.
All replies are forced into a JSON schema and validated; failures raise typed errors that the
agent turns into visible fallbacks.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from relief.config import Settings, get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """The model server cannot be reached or the model is not installed."""


class LLMOutputError(RuntimeError):
    """The model replied, but not with valid JSON for the schema."""


class LLM(Protocol):
    model: str

    def chat_json(self, system: str, user: str, schema: type[T]) -> T: ...


_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)


def _clean(content: str) -> str:
    content = _THINK.sub("", content).strip()
    return _FENCE.sub("", content).strip()


class OllamaClient:
    def __init__(self, settings: Optional[Settings] = None, host: Optional[str] = None, model: Optional[str] = None,
                 timeout: Optional[float] = None, retries: int = 1):
        s = settings or get_settings()
        self.host = host or s.llm_host
        self.model = model or s.llm_model
        self.timeout = timeout or s.llm_timeout_s
        self.retries = retries
        import ollama

        self._ollama = ollama
        self._client = ollama.Client(host=self.host, timeout=self.timeout)
        self._think_supported: Optional[bool] = None

    # ------------------------------------------------------------------ health
    def health(self) -> tuple[bool, str]:
        """(ok, message). Used by the API and the setup check; never raises."""
        try:
            listing = self._client.list()
        except Exception as exc:  # connection refused, DNS, timeout
            return False, f"Cannot reach the model server at {self.host}: {exc}"
        names = {getattr(m, "model", None) or (m.get("model") if isinstance(m, dict) else None) for m in listing.get("models", listing.models if hasattr(listing, "models") else [])}
        if self.model not in names and f"{self.model}:latest" not in names:
            fallback = next((m for m in ("qwen2.5:7b", "qwen3:8b", "llama3.1:8b", "gemma3:4b") if m in names or f"{m}:latest" in names), None)
            if fallback:
                self.model = fallback
                return True, f"Model {self.model} is available at {self.host} (auto-detected from installed models)"
            return False, f"Model {self.model} is not installed. Run: ollama pull {self.model}"
        return True, f"Model {self.model} is available at {self.host}"

    # ------------------------------------------------------------------ chat
    def _call(self, messages: list[dict], schema: type[BaseModel]) -> str:
        kwargs = dict(model=self.model, messages=messages, format=schema.model_json_schema(),
                      options={"temperature": 0, "seed": 7, "num_ctx": 4096})
        try:
            if self._think_supported is not False:
                try:
                    resp = self._client.chat(think=False, **kwargs)
                    self._think_supported = True
                except self._ollama.ResponseError as exc:
                    if "think" in str(exc).lower():
                        self._think_supported = False
                        resp = self._client.chat(**kwargs)
                    else:
                        raise
            else:
                resp = self._client.chat(**kwargs)
        except self._ollama.ResponseError as exc:
            if getattr(exc, "status_code", None) == 404:
                raise LLMUnavailable(f"Model {self.model} is not installed. Run: ollama pull {self.model}") from exc
            raise LLMUnavailable(f"Model server error: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise LLMUnavailable(f"Cannot reach the model server at {self.host}: {exc}") from exc
        except Exception as exc:  # httpx errors surface in several forms
            name = type(exc).__name__
            if "Connect" in name or "Timeout" in name or "Network" in name:
                raise LLMUnavailable(f"Cannot reach the model server at {self.host}: {exc}") from exc
            raise
        msg = resp["message"] if isinstance(resp, dict) else resp.message
        return msg["content"] if isinstance(msg, dict) else msg.content

    def chat_json(self, system: str, user: str, schema: type[T]) -> T:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        last_err = ""
        for attempt in range(self.retries + 1):
            raw = self._call(messages, schema)
            try:
                return schema.model_validate_json(_clean(raw))
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_err = str(exc)[:300]
                log.warning("model reply failed validation (attempt %d): %s", attempt + 1, last_err)
                messages = messages + [
                    {"role": "assistant", "content": raw[:2000]},
                    {"role": "user", "content": f"That reply was invalid: {last_err}. Reply again with only valid JSON for the schema."},
                ]
        raise LLMOutputError(f"Model did not return valid JSON: {last_err}")
