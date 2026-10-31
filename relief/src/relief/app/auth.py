"""Accounts and sessions: scrypt password hashes, signed JWT bearer tokens, simple login throttling."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt

from relief.config import Settings

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 10


def valid_email(e: str) -> bool:
    return bool(_EMAIL.match(e)) and len(e) <= 200


def password_problem(pw: str) -> Optional[str]:
    if len(pw) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if pw.lower() == pw or pw.upper() == pw or not any(c.isdigit() for c in pw):
        return "Use upper and lower case letters and at least one digit."
    return None


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc.hex(), dk)
    except Exception:
        return False


def load_secret(settings: Settings) -> str:
    """Use RELIEF_JWT_SECRET if set; otherwise create one once and keep it in the var directory (mode 600)."""
    if settings.jwt_secret:
        return settings.jwt_secret
    path: Path = settings.secret_path
    if path.exists():
        return path.read_text().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(48)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(secret)
    return secret


def make_token(secret: str, user: dict, hours: float) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user["id"]), "role": user["role"], "iat": now, "exp": now + timedelta(hours=hours)}, secret, algorithm="HS256")


def read_token(secret: str, token: str) -> Optional[int]:
    try:
        return int(jwt.decode(token, secret, algorithms=["HS256"])["sub"])
    except Exception:
        return None


class Throttle:
    """Blocks a key after `limit` failures within `window` seconds."""

    def __init__(self, limit: int = 5, window: int = 900):
        self.limit, self.window, self._fails = limit, window, {}

    def blocked(self, key: str) -> bool:
        now = time.time()
        self._fails[key] = [t for t in self._fails.get(key, []) if now - t < self.window]
        return len(self._fails[key]) >= self.limit

    def fail(self, key: str) -> None:
        self._fails.setdefault(key, []).append(time.time())

    def clear(self, key: str) -> None:
        self._fails.pop(key, None)
