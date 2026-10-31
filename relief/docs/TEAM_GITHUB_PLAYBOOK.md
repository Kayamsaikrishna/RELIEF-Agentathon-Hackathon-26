# GitHub playbook for the four of us

## Before the event (Oct 30, 30 minutes, everyone)
1. Sai creates a **public** repo named `relief` under https://github.com/Kayamsaikrishna, no README, no .gitignore, no licence. Adds `MRamyasreelakshmi`, `rishithareddyaggannagari-cmd` and `mahithap09` (Settings → Collaborators → Add people, role Write). Each of them accepts the invitation from their email.
2. Everyone: `git config --global user.name "Your Name"` and `user.email` = the email on your GitHub account (so commits show your face). Test with one throwaway push to a branch, then delete it.
3. Sai sets, on `main` (Settings → Branches → Add rule): require a pull request, require 1 approval, require the `test` check, no force-push.
4. `.github/CODEOWNERS` already has the four real usernames; CODEOWNERS only works once all four have accepted access.
5. Create labels: `lane-a`, `lane-b`, `lane-c`, `lane-d`, `bug`, `task`. Create a Project board (To do, Doing, Review, Done).
6. **Do not push the project yet.** Push it at 4:00 PM on Oct 31 (start of the hackathon) as the first commit, in front of the team.

## First commit (Sai, 4:00 PM Oct 31)
```bash
unzip RELIEF_project.zip && cd relief
git init -b main && git add . && git commit -m "Initial import: scaffold prepared before the event (see docs/PREPARED_BEFORE_EVENT.md)"
git remote add origin https://github.com/Kayamsaikrishna/relief.git && git push -u origin main
```
Then the other three clone it. Make sure the real timestamp is kept; never alter it.

## Daily loop (everyone, every 1-3 hours)
```bash
git switch main && git pull
git switch -c lane-b/verify-rule-quotes
# work, run: make test
git add -p && git commit -m "rules: fix quote for WHO-REFERRAL-VALID-30D"   # several small commits
git push -u origin lane-b/verify-rule-quotes
# open a pull request on GitHub, tag a reviewer from another lane, link the issue
```
Reviewer: read the diff, run it if it touches your lane, comment, approve. Merge with "Create a merge commit" (keeps the history). Delete the branch. Everyone pulls `main` after each merge.

## Real work for each lane that makes real commits and pull requests
| Lane | Issues to open at 4:30 PM (each becomes one or more PRs) |
|---|---|
| A (Sai Krishna) | Run the agent on real Qwen3 and fix JSON failures; set timeouts and warm-up; measure seconds per call on qwen3:8b vs 4b; add logging of model failures; run `--llm` evaluation and commit results |
| B (Ramya) | Run `scripts/verify_sources.py` and fix failing quotes; test OCR on 10 real phone photos of printed cards and tune the parser; test rule search recall on 20 queries; add missing rules found while reading |
| C (Rishitha) | Run the UI with a facilitator walkthrough and fix wording and error states; add file upload preview; polish the approval and edit flow; make the reminders tab useful; screenshots for the README |
| D (Mahitha) | Review the 30 cases and add 10 new ones with sources; second-review the answer keys; write the demo script and 3-minute story; fill docs/LIMITS.md with what you actually saw; collect failure cases |
| All | Bug bash (issues), freeze tag `freeze-1`, final README, rehearsal |

## Evenings and nights
* Every 3 hours: 10-minute sync. Post `[DONE] ...` in the chat; merge what is green.
* Sleep in shifts; the person awake merges only reviewed pull requests.
* Never force-push, never rewrite history, never edit timestamps. Reverts are normal and look good.

## Final hour
Tag `final`, check the repo is public, the README has the setup steps, `docs/PREPARED_BEFORE_EVENT.md` is accurate, and the last commit is before the deadline (3:30 PM Nov 1).
