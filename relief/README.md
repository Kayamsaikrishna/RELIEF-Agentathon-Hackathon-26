# RELIEF

An agent that helps a facilitator (for example an Arogya Mitra) find **why cashless treatment under Ayushman Bharat PM-JAY and state schemes (Dr. YSR Aarogyasri, Aarogyasri, AB-ArK, MJPJAY, CMCHIS) was blocked**, checks the records and rules, cites the rule, prepares the fix, and **waits for a person to approve every action**.

It gives no medical advice, makes no eligibility decisions and never promises treatment. Every finding is worded "Possible …, requires verification". If a message suggests an emergency, it stops and shows a fixed notice (call 112 / go to the nearest hospital).

## How it works

```
intake → choose_tool ⇄ run_tool → retrieve → diagnose → plan → verify → human gate → act → done
            (emergency wording → stop)         (not enough evidence / low confidence → hand over)
```

* **Code decides facts**: name/date/id comparison, hospital empanelment, referral tier and 30-day validity, document completeness, the pre-authorisation clock (reported against both the 6-hour HBP 2.2 and 12-hour CAG limits, because the sources differ), and every citation.
* **The local model (Qwen2.5 / Qwen3 on Ollama) only does language**: orders the checks (all applicable checks always run), ranks candidate blockers when two or more are strong, writes one summary sentence. Replies are forced into a JSON schema and validated. If the model is down or wrong, a rule-based fallback is used and shown in the trace.
* **Verifier (code)**: every cited rule/evidence id exists, required checklist items are present, letters contain the case facts, no eligibility verdicts, guarantees or medical advice. Failing plans are revised twice, then handed to a person.
* **Human gate**: LangGraph `interrupt()`; approve, edit or reject. Nothing is executed before approval; state survives restarts (SQLite checkpoints).

Six blockers: Referral · Entitlement · Linkage · Improper charge · Empanelment · Forms, plus Escalation-only and Insufficient evidence (hand over, with a list of what is missing).

## Run it (Windows, macOS, Linux)

You need Python 3.11+, Node 18+ (only to build the web app once), Ollama, and Tesseract (for photo OCR).

```bash
pip install -e ".[dev]"                 # backend
cp .env.example .env                    # Windows: copy .env.example .env  -> set RELIEF_LLM_MODEL to qwen2.5:7b
ollama pull nomic-embed-text            # rule-search embeddings (skip if you already have it)
python scripts/ollama_check.py          # model, structured call, embedder: all OK?
python -m relief.app.cli create-user --email you@example.org --name "Your Name" --role admin   # asks for a password
cd frontend && npm install && npm run build && cd ..     # web app (built into frontend/dist)
python -m uvicorn relief.app.api:create_app --factory --port 8000
```

Open **http://127.0.0.1:8000**. On Windows, `start.bat` does the build-if-needed and start in one step.
Create facilitator accounts from the Admin → Users page.

Development with hot reload: run the backend as above and `cd frontend && npm run dev`, then open http://localhost:5173.

Other commands: `python -m pytest` (48 tests) · `python -m relief.eval.run_eval` · `python -m relief.agent.run fixtures/case_referral_input.json --no-llm --approve`.

No model running? The agent still works on its rule-based path (the trace says so). With `RELIEF_EMBEDDER=hashing` no embedding model is needed either.

## Web app

React + TypeScript (Vite) in `frontend/`: landing page, safety page, sign-in, facilitator workspace (dashboard, 4-step new case wizard, case page with live progress, evidence, cited rules, editable plan, approve / edit / reject, print to PDF, reminders, account) and admin console (overview, users, rules, registry, audit log, system health). Accounts: scrypt password hashes, signed tokens, login throttling, per-user case privacy, audit log.

## What is real and what is not

| Part | Status |
|---|---|
| Rule base (31 rules, 6 official documents) | Paraphrased with source, section, page. `quote_checked=false` until you run `python scripts/verify_sources.py` on a networked machine. Unchecked rules are flagged on screen. |
| Hospital registry and packages | **Synthetic** (`data/registry/registry.json`, names start "SYN"). Replace with a real export in the same format (docs/REGISTRY_FORMAT.md). |
| Pre-authorisation submission | **Simulator** (`app/portal.py`), labelled on every response. Not connected to the Transaction Management System. |
| Cases | Synthetic only. Use no real patient data. |
| Beneficiary lookup | Entered by the facilitator; the agent never queries BIS. |

## Layout

`src/relief/` — `contracts/` types · `tools/` checks, rule search, letters · `agent/` graph, diagnosis, planner, verifier, safety · `llm/` Ollama client · `app/` API, SQLite log, simulator, reminders · `frontend/` React web app · `eval/` cases and runner. `data/` rules and registry · `fixtures/` sample cases · `scripts/` laptop checks · `docs/`.

See docs/CONTRACTS.md, docs/EVALUATION.md, docs/LIMITS.md.

## Team and workflow

See CONTRIBUTING.md and docs/PREPARED_BEFORE_EVENT.md. Lanes: A agent · B tools and knowledge · C app and UI · D evidence, evaluation and story.
