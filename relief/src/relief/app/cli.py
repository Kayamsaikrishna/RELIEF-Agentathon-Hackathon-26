"""Account administration. First admin:  python -m relief.app.cli create-user --email you@example.org --name "Your Name" --role admin"""
from __future__ import annotations

import argparse
import getpass
import sys

from relief.app import auth
from relief.app.db import Database
from relief.config import get_settings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="relief.app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-user")
    c.add_argument("--email", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--role", choices=["admin", "facilitator"], default="facilitator")
    c.add_argument("--password", help="omit to be asked (recommended)")
    sub.add_parser("list-users")
    r = sub.add_parser("reset-password")
    r.add_argument("--email", required=True)
    a = ap.parse_args(argv)
    db = Database(get_settings().db_path)
    if a.cmd == "list-users":
        for u in db.users():
            print(f"{u['id']:>3}  {u['email']:<36} {u['role']:<12} {'active' if u['active'] else 'disabled'}  {u['name']}")
        return 0
    pw = getattr(a, "password", None) or getpass.getpass("Password: ")
    if a.cmd == "create-user":
        if not auth.valid_email(a.email):
            print("That does not look like an email address."); return 1
        if db.get_user(a.email):
            print("A user with that email already exists."); return 1
    if (p := auth.password_problem(pw)):
        print(p); return 1
    if a.cmd == "create-user":
        db.add_user(a.email, a.name, a.role, auth.hash_password(pw))
        db.audit("cli", "user.create", detail=f"{a.email} ({a.role})")
        print(f"Created {a.role} {a.email}")
    else:
        u = db.get_user(a.email)
        if not u:
            print("No such user."); return 1
        db.update_user(u["id"], password_hash=auth.hash_password(pw))
        db.audit("cli", "user.reset_password", detail=a.email)
        print("Password updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
