import subprocess
from dataclasses import dataclass
from typing import Optional
import sys
import sqlite3
from pathlib import Path
import os


@dataclass
class User:
    name: str
    email_address: str

    @classmethod
    def from_semicolon_separated_str(cls, text: str):
        tokens = text.split(";")
        if len(tokens) != 2:
            raise ValueError(
                f"expect two fields; one for user.name and one for user.email. Found {len(tokens)} fields: {str(tokens)}"
            )
        return cls(name=tokens[0], email_address=tokens[1])

    @classmethod
    def from_db_record(cls, record):
        return cls(name=record[0], email_address=record[1])


class KnownUserDB:
    def __init__(self, path=None):
        if path is None:
            path = Path(os.environ.get("HOME")) / "commit-as.sqlite3"

        self.path = path
        self.con = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.disconnect()

    def connect(self):
        if self.con is None:
            self.con = sqlite3.connect(self.path)

    def disconnect(self):
        if not (self.con is None):
            self.con.close()

    def create_tables(self):
        cur = self.con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, key TEXT, name TEXT, email_address TEXT)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS user_key ON users(key)")
        self.con.commit()

    def add_user(self, key: str, name: str, email_address: str) -> None:
        cur = self.con.cursor()
        cur.execute(
            """
            INSERT INTO users(key, name, email_address) VALUES
                (:key, :name, :email_address)
        """,
            {"key": key, "name": name, "email_address": email_address},
        )
        self.con.commit()

    def get_user_by_key(self, key: str) -> Optional[User]:
        cur = self.con.cursor()
        res = cur.execute(
            "SELECT name, email_address FROM users WHERE key=:key", {"key": key}
        )
        user_row = res.fetchone()

        if user_row is None:
            return None

        return User.from_db_record(user_row)


def commit_as(user: User, args: list[str] = list()) -> None:
    """
    Commit as the `user`.

    This will perform a single commit with the `user`.
    """
    if len(args) == 0:
        cmd = [
            "git",
            "-c",
            f"user.name={user.name}",
            "-c",
            f"user.email={user.email_address}",
            "commit",
        ]
    else:
        cmd = [
            "git",
            "-c",
            f"user.name={user.name}",
            "-c",
            f"user.email={user.email_address}",
            "commit",
        ]
        cmd.extend(args)
    # Pass control to git.
    proc = subprocess.run(cmd)


def set_user(user: User, args: list[str] = list()) -> None:
    """Set user for Git."""
    cmd = f"git config --global user.name {user.name}; git config --global user.email {user.email_address}"
    proc = subprocess.run(cmd, shell=True)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--db", action="store", help="Path to database.", default=None
    )
    parser.add_argument(
        "-r",
        "--raw-user",
        action="store_true",
        help="Treat user argument as full name and email separated by semicolon instead of reading from the database.",
    )
    parser.add_argument(
        "--set",
        action="store_true",
        help="Set Git's configuration to this user instead of making a commit.",
    )
    parser.add_argument("user-key", help="")

    args, unknown_args = parser.parse_known_args()

    db = KnownUserDB(args.db)

    if args.raw_user:
        try:
            user = User.from_semicolon_separated_str(args.user)
        except ValueError as ex:
            print(ex)
            sys.exit()
    else:
        user = db.get_user_by_key(args.user_key)
        if user is None:
            print(f"Cannot find user '{args.user}' in the known users database.")
            sys.exit()

    if args.set:
        set_user(user, args=unknown_args)
    else:
        commit_as(user, args=unknown_args)


if __name__ == "__main__":
    main()
