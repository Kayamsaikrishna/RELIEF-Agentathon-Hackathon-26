"""Application log: cases, decisions, simulator submissions, reminders. One SQLite file under RELIEF_VAR_DIR."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases(case_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, main_blocker TEXT,
  synthetic INTEGER NOT NULL DEFAULT 0, case_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, ts TEXT NOT NULL, action TEXT NOT NULL,
  decided_by TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, ts TEXT NOT NULL, kind TEXT NOT NULL,
  reference TEXT NOT NULL, payload_json TEXT NOT NULL, simulated INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','facilitator')), password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, last_login TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  case_id TEXT, detail TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, due_at TEXT NOT NULL, message TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending', fired_at TEXT);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._c = sqlite3.connect(self.path, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        with self._lock:
            self._c.executescript(SCHEMA)
            cols = {r["name"] for r in self._c.execute("PRAGMA table_info(cases)").fetchall()}
            for col, ddl in (("created_by", "TEXT"), ("error", "TEXT")):
                if col not in cols:
                    self._c.execute(f"ALTER TABLE cases ADD COLUMN {col} {ddl}")
            self._c.commit()
            if self.count_users() == 0 and not os.environ.get("PYTEST_CURRENT_TEST"):
                from relief.app.auth import hash_password
                pw_hash = hash_password("Relief2026!")
                now_str = _now()
                self._c.execute(
                    "INSERT INTO users(email, name, role, password_hash, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                    ("admin@relief.org", "RELIEF Administrator", "admin", pw_hash, now_str)
                )
                self._c.execute(
                    "INSERT INTO users(email, name, role, password_hash, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                    ("facilitator@relief.org", "Arogya Mitra Facilitator", "facilitator", pw_hash, now_str)
                )
                self._c.commit()

    def _q(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._c.execute(sql, args).fetchall()]

    def _x(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            cur = self._c.execute(sql, args)
            self._c.commit()
            return cur.lastrowid or 0

    # cases
    def save_case(self, case_id: str, status: str, main_blocker: Optional[str], synthetic: bool, case_json: str,
                  created_by: Optional[str] = None) -> None:
        self._x("INSERT INTO cases(case_id,created_at,status,main_blocker,synthetic,case_json,created_by) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(case_id) DO UPDATE SET status=excluded.status, main_blocker=excluded.main_blocker",
                (case_id, _now(), status, main_blocker, int(synthetic), case_json, created_by))

    def update_case(self, case_id: str, status: str, main_blocker: Optional[str] = None, error: Optional[str] = None) -> None:
        self._x("UPDATE cases SET status=?, main_blocker=COALESCE(?, main_blocker), error=? WHERE case_id=?",
                (status, main_blocker, error, case_id))

    def get_case_row(self, case_id: str) -> Optional[dict]:
        rows = self._q("SELECT * FROM cases WHERE case_id=?", (case_id,))
        return rows[0] if rows else None

    def list_cases(self, limit: int = 100, owner: Optional[str] = None, status: Optional[str] = None,
                   blocker: Optional[str] = None, q: Optional[str] = None) -> list[dict]:
        sql, args = "SELECT case_id,created_at,status,main_blocker,synthetic,created_by,error FROM cases WHERE 1=1", []
        if owner:
            sql += " AND created_by=?"; args.append(owner)
        if status:
            sql += " AND status=?"; args.append(status)
        if blocker:
            sql += " AND main_blocker=?"; args.append(blocker)
        if q:
            sql += " AND case_id LIKE ?"; args.append(f"%{q}%")
        return self._q(sql + " ORDER BY created_at DESC LIMIT ?", tuple(args) + (limit,))

    # users
    def add_user(self, email: str, name: str, role: str, password_hash: str) -> int:
        return self._x("INSERT INTO users(email,name,role,password_hash,created_at) VALUES(?,?,?,?,?)", (email.lower(), name, role, password_hash, _now()))

    def get_user(self, email: str) -> Optional[dict]:
        rows = self._q("SELECT * FROM users WHERE email=?", (email.lower(),))
        return rows[0] if rows else None

    def get_user_id(self, uid: int) -> Optional[dict]:
        rows = self._q("SELECT * FROM users WHERE id=?", (uid,))
        return rows[0] if rows else None

    def users(self) -> list[dict]:
        return self._q("SELECT id,email,name,role,active,created_at,last_login FROM users ORDER BY id")

    def count_users(self) -> int:
        return self._q("SELECT COUNT(*) AS n FROM users")[0]["n"]

    def update_user(self, uid: int, **fields) -> None:
        allowed = {"name", "role", "active", "password_hash", "last_login"}
        sets = [(k, v) for k, v in fields.items() if k in allowed]
        if sets:
            self._x(f"UPDATE users SET {', '.join(k + '=?' for k, _ in sets)} WHERE id=?", tuple(v for _, v in sets) + (uid,))

    def count_active_admins(self) -> int:
        return self._q("SELECT COUNT(*) AS n FROM users WHERE role='admin' AND active=1")[0]["n"]

    # audit
    def audit(self, actor: str, action: str, case_id: Optional[str] = None, detail: str = "") -> None:
        self._x("INSERT INTO audit(ts,actor,action,case_id,detail) VALUES(?,?,?,?,?)", (_now(), actor, action, case_id, detail[:500]))

    def audit_log(self, limit: int = 200, case_id: Optional[str] = None) -> list[dict]:
        if case_id:
            return self._q("SELECT * FROM audit WHERE case_id=? ORDER BY id DESC LIMIT ?", (case_id, limit))
        return self._q("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))

    # statistics
    def stats(self, owner: Optional[str] = None) -> dict:
        w, a = (" WHERE created_by=?", (owner,)) if owner else ("", ())
        by_status = {r["status"]: r["n"] for r in self._q(f"SELECT status, COUNT(*) AS n FROM cases{w} GROUP BY status", a)}
        by_blocker = {r["main_blocker"]: r["n"] for r in self._q(
            f"SELECT main_blocker, COUNT(*) AS n FROM cases{w}{' AND' if w else ' WHERE'} main_blocker IS NOT NULL GROUP BY main_blocker", a)}
        daily_rows = {r["day"]: r["n"] for r in self._q(f"SELECT substr(created_at,1,10) AS day, COUNT(*) AS n FROM cases{w} GROUP BY day ORDER BY day DESC LIMIT 14", a)}
        if daily_rows:
            try:
                latest_date = datetime.fromisoformat(max(daily_rows.keys())).date()
            except ValueError:
                latest_date = datetime.now(timezone.utc).date()
        else:
            latest_date = datetime.now(timezone.utc).date()
        days_window = [(latest_date - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        daily = [{"day": d, "n": daily_rows.get(d, 0)} for d in days_window]
        return {"total": sum(by_status.values()), "by_status": by_status, "by_blocker": by_blocker, "daily": daily}

    def case_exists(self, case_id: str) -> bool:
        return bool(self._q("SELECT 1 FROM cases WHERE case_id=?", (case_id,)))

    # decisions
    def add_decision(self, case_id: str, action: str, decided_by: str, note: str) -> None:
        self._x("INSERT INTO decisions(case_id,ts,action,decided_by,note) VALUES(?,?,?,?,?)", (case_id, _now(), action, decided_by, note))

    def decisions(self, case_id: str) -> list[dict]:
        return self._q("SELECT * FROM decisions WHERE case_id=? ORDER BY id", (case_id,))

    # submissions
    def add_submission(self, case_id: str, kind: str, reference: str, payload: dict, simulated: bool = True) -> int:
        return self._x("INSERT INTO submissions(case_id,ts,kind,reference,payload_json,simulated) VALUES(?,?,?,?,?,?)",
                       (case_id, _now(), kind, reference, json.dumps(payload, default=str), int(simulated)))

    def submissions(self, case_id: Optional[str] = None) -> list[dict]:
        if case_id:
            return self._q("SELECT * FROM submissions WHERE case_id=? ORDER BY id", (case_id,))
        return self._q("SELECT * FROM submissions ORDER BY id DESC LIMIT 200")

    # reminders
    def add_reminder(self, case_id: str, hours: float, message: str) -> int:
        due = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        return self._x("INSERT INTO reminders(case_id,due_at,message) VALUES(?,?,?)", (case_id, due, message))

    def reminders(self, state: Optional[str] = None) -> list[dict]:
        if state:
            return self._q("SELECT * FROM reminders WHERE state=? ORDER BY due_at", (state,))
        return self._q("SELECT * FROM reminders ORDER BY due_at")

    def fire_due_reminders(self, now: Optional[datetime] = None) -> list[dict]:
        now_s = (now or datetime.now(timezone.utc)).isoformat()
        due = self._q("SELECT * FROM reminders WHERE state='pending' AND due_at<=?", (now_s,))
        for r in due:
            self._x("UPDATE reminders SET state='due', fired_at=? WHERE id=?", (now_s, r["id"]))
        return due

    def dismiss_reminder(self, rid: int) -> None:
        self._x("UPDATE reminders SET state='done' WHERE id=?", (rid,))
