"""Check every rule's quote or anchor terms against the official source text. Needs internet; run on a laptop.
    python scripts/verify_sources.py
Writes data/rules/verification.json {rule_id: bool}. Rules not verified keep quote_checked=false and a warning on screen."""
import io
import json
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1] / "data" / "rules"


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def fetch_text(url: str) -> str:
    r = httpx.get(url, follow_redirects=True, timeout=120, headers={"User-Agent": "RELIEF-source-check"})
    r.raise_for_status()
    if url.lower().endswith(".pdf") or r.headers.get("content-type", "").startswith("application/pdf"):
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
    return re.sub(r"<[^>]+>", " ", r.text)


def main() -> int:
    sources = {s["source_id"]: s for s in json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))}
    rules = json.loads((ROOT / "rules.json").read_text(encoding="utf-8"))
    texts: dict[str, str] = {}
    result: dict[str, bool] = {}
    for sid, s in sources.items():
        try:
            texts[sid] = norm(fetch_text(s["url"]))
            print(f"fetched {sid} ({len(texts[sid])} chars)")
        except Exception as exc:
            print(f"COULD NOT FETCH {sid}: {exc}")
    for r in rules:
        t = texts.get(r["source_id"])
        if not t:
            result[r["rule_id"]] = False
            continue
        if r.get("quote"):
            ok = norm(r["quote"]) in t
        else:
            anchors = [norm(a) for a in r.get("anchors", [])]
            ok = bool(anchors) and all(a in t for a in anchors)
        result[r["rule_id"]] = ok
        print(("ok    " if ok else "CHECK ") + r["rule_id"])
    (ROOT / "verification.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"{sum(result.values())}/{len(result)} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
