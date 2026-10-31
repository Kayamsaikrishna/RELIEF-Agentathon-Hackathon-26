"""OllamaClient against a local fake server that speaks the Ollama HTTP protocol."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from pydantic import BaseModel

from relief.config import Settings
from relief.llm.client import LLMOutputError, LLMUnavailable, OllamaClient


class Out(BaseModel):
    summary: str


def serve(replies, tags=("qwen3:8b",)):
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            self._send(200, {"models": [{"model": t, "name": t} for t in tags]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            r = replies.pop(0)
            if isinstance(r, int):
                self._send(r, {"error": "boom"})
            else:
                self._send(200, {"model": body["model"], "message": {"role": "assistant", "content": r}, "done": True})

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}", seen


def client(url, **kw):
    return OllamaClient(Settings(), host=url, model="qwen3:8b", timeout=5, **kw)


def test_valid_reply_and_request_shape():
    srv, url, seen = serve(['{"summary": "ok"}'])
    assert client(url).chat_json("sys", "user", Out).summary == "ok"
    assert seen[0]["format"]["properties"]["summary"] and seen[0]["options"]["temperature"] == 0
    srv.shutdown()


def test_think_tags_and_fences_are_stripped():
    srv, url, _ = serve(['<think>hmm</think>```json\n{"summary": "ok"}\n```'])
    assert client(url).chat_json("s", "u", Out).summary == "ok"
    srv.shutdown()


def test_retry_once_then_succeed_and_then_fail():
    srv, url, seen = serve(["not json", '{"summary": "second"}'])
    assert client(url).chat_json("s", "u", Out).summary == "second"
    assert "invalid" in seen[1]["messages"][-1]["content"]
    srv.shutdown()
    srv, url, _ = serve(["bad", "worse"])
    with pytest.raises(LLMOutputError):
        client(url).chat_json("s", "u", Out)
    srv.shutdown()


def test_health_missing_model_and_unreachable():
    srv, url, _ = serve([], tags=("other:1b",))
    ok, msg = client(url).health()
    assert not ok and "ollama pull qwen3:8b" in msg
    srv.shutdown()
    ok, msg = client("http://127.0.0.1:1").health()
    assert not ok
    with pytest.raises(LLMUnavailable):
        client("http://127.0.0.1:1").chat_json("s", "u", Out)


def test_ollama_embedder_against_fake_server():
    """Checks the request shape sent for nomic-embed-text (prefixes) and that vectors come back as lists."""
    from relief.tools.rules_kb import OllamaEmbedder
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            out = json.dumps({"model": body["model"], "embeddings": [[0.1, 0.2, 0.3] for _ in body["input"]]}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    e = OllamaEmbedder("nomic-embed-text", f"http://127.0.0.1:{srv.server_port}")
    assert e.embed_documents(["a", "b"]) == [[0.1, 0.2, 0.3]] * 2 and seen[0]["input"] == ["search_document: a", "search_document: b"]
    assert e.embed_query("q") == [0.1, 0.2, 0.3] and seen[1]["input"] == ["search_query: q"]
    srv.shutdown()
    with pytest.raises(RuntimeError, match="ollama pull nomic-embed-text"):
        OllamaEmbedder("nomic-embed-text", "http://127.0.0.1:1").embed_query("x")
