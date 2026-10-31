# How we work

Four lanes, one repo, short branches, reviewed pull requests.

* **Branches:** `lane-a/<what>`, `lane-b/<what>`, `lane-c/<what>`, `lane-d/<what>`, `fix/<what>`. Branch from `main`, keep them under about 3 hours.
* **Commits:** small, one idea each, in the imperative: `verifier: reject letter quotes not in rule text`. Commit from your own account.
* **Pull requests:** into `main`, reviewed by a person from another lane. Squash only for tiny fix-ups; otherwise keep the commits. Do not push to `main` directly.
* **Issues:** every task and bug has one. Commits and pull requests link them (`Closes #12`).
* **Contracts:** `src/relief/contracts/schemas.py` changes only through a pull request that the lead approves, and only additively.
* **Safety:** no real patient data, no secrets (`.env` is ignored), no medical advice or eligibility wording in outputs.
* **Tests:** `make test` before you push; CI runs it again.
