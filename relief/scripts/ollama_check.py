"""Run on the laptop that has Ollama: python scripts/ollama_check.py
Checks that the model server is up, the model is installed, and a structured call returns valid JSON with the agent's own schema."""
import sys
import time

from relief.agent import prompts
from relief.config import get_settings
from relief.llm.client import OllamaClient


def main() -> int:
    s = get_settings()
    c = OllamaClient(s)
    ok, msg = c.health()
    print(("OK   " if ok else "FAIL ") + msg)
    if not ok:
        print(f"Start Ollama, then: ollama pull {s.llm_model}")
        return 1
    t = time.time()
    try:
        r = c.chat_json(prompts.SUMMARY_SYSTEM, '{"main_finding": "Possible missing referral for a tier 3A procedure.", "next_steps": ["Ask the hospital for the referral letter."]}', prompts.SummaryOut)
    except Exception as exc:
        print("FAIL structured call:", exc)
        return 1
    print(f"OK   structured call in {time.time() - t:.1f}s -> {r.summary}")
    try:
        from relief.tools.rules_kb import make_embedder
        make_embedder(s.embedder).embed_query("referral")
        print(f"OK   embedder '{s.embedder}' loads")
    except Exception as exc:
        print(f"FAIL embedder '{s.embedder}': {exc}\n     (use RELIEF_EMBEDDER=hashing for a lower-quality offline fallback)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
