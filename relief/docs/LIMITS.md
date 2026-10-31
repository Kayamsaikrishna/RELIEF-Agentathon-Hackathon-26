# Limits and unverified items

1. **Not verified here:** Qwen3 and BGE were never run in the build environment. The Ollama client was tested against a fake server that speaks the Ollama protocol. Run `make check` and `python -m relief.eval.run_eval --llm` on a machine with Ollama before claiming any model-path result.
2. **Rule quotes** are unchecked until `scripts/verify_sources.py` is run with internet access. Sources disagree on the pre-authorisation time limit (HBP 2.2: 6 h; CAG report: 12 h), so both are shown.
3. **Referral tiers** come from a 2025 WHO paper on Karnataka's referral system; the real rules may have changed.
4. **OCR** (Tesseract) was tested on generated images only. Phone photos at an angle or in poor light will often come out "unreadable", which hands over rather than guesses.
5. **Synthetic registry and simulator**: no live hospital list, no live portal, no real beneficiary lookup.
6. **Evaluation** is circular on the rule-based path (see EVALUATION.md).
7. Built on Python 3.13; declared support is 3.11+ — run `make test` on your version.
8. English only. Not a legal or medical tool.
