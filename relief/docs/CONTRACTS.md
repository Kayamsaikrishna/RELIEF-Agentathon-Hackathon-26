# Contracts

All types are in `src/relief/contracts/schemas.py` (Pydantic, unknown fields rejected). Entry points:

* `Agent.run_case(CaseInput) -> CaseResult` — runs until the human gate, a hand-over, or an emergency stop.
* `Agent.resume_case(case_id, Decision) -> CaseResult` — `approve`, `edit` (needs `edited_plan`, re-verified) or `reject`.
* `Agent.get_result(case_id) -> CaseResult`.

HTTP (all under `/api`, JSON, `Authorization: Bearer <token>` except health and login): `GET /health` · `POST /auth/login` · `GET /auth/me` · `POST /auth/password` · `GET /registry/hospitals|packages|info` · `POST /uploads` · `POST /cases` (202; analysis runs in the background, poll `GET /cases/{id}`) · `GET /cases` (filters: status, blocker, q) · `GET /cases/{id}` · `POST /cases/{id}/decision` (the server records the signed-in user as decider) · `GET /cases/{id}/log` · `GET /stats` · `GET /reminders` · `POST /reminders/{id}/done` · admin only: `GET|POST /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/rules|audit|system`. Interactive docs at `/api/docs`. Facilitators see only their own cases; administrators see all. Documents by path must come from `/uploads` (png/jpg/tif/bmp, content-checked, size-limited).

Rules: "unknown" is a valid answer for any check; no tool guesses. `CaseResult.findings[0]` is the main blocker; `status` is one of running, awaiting_approval, handover, approved, rejected, completed, error. Changes after the first release should be additive.
