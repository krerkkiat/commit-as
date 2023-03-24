import subprocess
from dataclasses import dataclass
from typing import Optional
import sys
import sqlite3
from pathlib import Path
import os


@dataclass
class User:
    id_: int
    key: str
    name: str
    email_address: str

    @classmethod
    def from_semicolon_separated_str(cls, text: str):
        tokens = text.split(";")
        if len(tokens) == 2:
            return cls(id_=0, key=tokens[0], name=tokens[0], email_address=tokens[1])
        elif len(tokens) == 3:
            return cls(id_=0, key=tokens[0], name=tokens[1], email_address=tokens[2])
        else:
            raise ValueError(
                f"expect two fields; one for user.name and one for user.email. Found {len(tokens)} fields: {str(tokens)}"
            )

    @classmethod
    def from_db_record(cls, record):
        return cls(
            id_=record[0], key=record[1], name=record[2], email_address=record[3]
        )

    def __str__(self):
        return f"id: {self.id_}, key: '{self.key}', name: '{self.name}' email_address: '{self.email_address}'"


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

    def delete(self, id_: int) -> None:
        cur = self.con.cursor()
        res = cur.execute(
            "DELETE FROM users WHERE id=:id_",
            {"id_": id_},
        )
        self.con.commit()

    def delete_by_key(self, key: str) -> None:
        cur = self.con.cursor()
        res = cur.execute(
            "DELETE FROM users WHERE key=:key",
            {"key": key},
        )
        self.con.commit()

    def get(self, id_: int) -> None:
        cur = self.con.cursor()
        res = cur.execute(
            "SELECT id, key, name, email_address FROM users WHERE id=:id_",
            {"id_": id_},
        )
        user_row = res.fetchone()

        if user_row is None:
            return None

        return User.from_db_record(user_row)

    def get_user_by_key(self, key: str) -> Optional[User]:
        cur = self.con.cursor()
        res = cur.execute(
            "SELECT id, key, name, email_address FROM users WHERE key=:key",
            {"key": key},
        )
        user_row = res.fetchone()

        if user_row is None:
            return None

        return User.from_db_record(user_row)

    def get_all_users(self) -> list[User]:
        """Get all users."""
        cur = self.con.cursor()
        res = cur.execute("SELECT id, key, name, email_address FROM users")

        users = []
        for record in res.fetchall():
            users.append(User.from_db_record(record))
        return users


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

    cli = argparse.ArgumentParser()
    cli.add_argument(
        "-d", "--db", action="store", help="Path to database.", default=None
    )
    cli.add_argument(
        "-r",
        "--raw-user",
        action="store_true",
        help="Treat user argument as full name and email separated by semicolon instead of reading from the database.",
    )

    subparsers = cli.add_subparsers(dest="subcommand")

    commit_cmd_parser = subparsers.add_parser("commit", description="Commit as a user")
    commit_cmd_parser.add_argument("key", help="Key of a user stored in the database.")

    set_cmd_parser = subparsers.add_parser(
        "set",
        description="Set Git's configuration to this user instead of making a commit.",
    )
    set_cmd_parser.add_argument("key", help="Key of a user stored in the database.")

    add_cmd_parser = subparsers.add_parser(
        "add", description="Add user to the database"
    )
    add_cmd_parser.add_argument("key", help="Key of a user stored in the database.")
    add_cmd_parser.add_argument("name")
    add_cmd_parser.add_argument("email_address")

    remove_cmd_parser = subparsers.add_parser(
        "remove", description="Remove user from the database"
    )
    remove_cmd_parser.add_argument("key")

    list_cmd_parser = subparsers.add_parser(
        "list", description="List users in the database"
    )

    args, unknown_args = cli.parse_known_args()

    db = KnownUserDB(args.db)
    db.connect()
    db.create_tables()

    if args.subcommand == "commit" or args.subcommand == "set":
        if args.raw_user:
            try:
                user = User.from_semicolon_separated_str(args.key)
            except ValueError as ex:
                print(ex)
                sys.exit()
        else:
            user = db.get_user_by_key(args.key)
            if user is None:
                print(f"Cannot find user '{args.key}' in the known users database.")
                sys.exit()
        if args.subcommand == "commit":
            commit_as(user, args=unknown_args)
        elif args.subcommand == "set":
            set_user(user, args=unknown_args)
    elif args.subcommand == "add":
        db.add_user(args.key, args.name, args.email_address)
    elif args.subcommand == "remove":
        db.delete_by_key(args.key)
    elif args.subcommand == "list":
        users = db.get_all_users()
        if len(users) == 0:
            print(f"no user found in the database at {db.path}")
        else:
            for user in users:
                print(str(user))


if __name__ == "__main__":
    main()
