import subprocess
from dataclasses import dataclass
from typing import Optional
import sys

@dataclass
class User:
    name: str
    email: str

    @classmethod
    def from_semicolon_separated_str(cls, text: str):
        tokens = text.split(";")
        if len(tokens) != 2:
            raise ValueError(f"expect two fields; one for user.name and one for user.email. Found {len(tokens)} fields: {str(tokens)}")
        return cls(name=tokens[0], email=tokens[1])

# TODO(kc): Move away from hard coded db.
known_users = {
    "kc": User(name="Krerkkiat Chusap", email="kc@example.com"),
}

def commit_as(user: User, args: list[str]=list()) -> None:
    """
    Commit as the `user`.

    This will perform a single commit with the `user`.
    """
    if len(args) == 0:
        cmd = ["git", "-c", f"user.name={user.name}", "-c", f"user.email={user.email}", "commit"]
    else:
        cmd = ["git", "-c", f"user.name={user.name}", "-c", f"user.email={user.email}", "commit"]
        cmd.extend(args)
    # Pass control to git.
    proc = subprocess.run(cmd)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--raw-user", action="store_true")
    parser.add_argument("user")

    args, unknown_args = parser.parse_known_args()

    if args.raw_user:
        try:
            user = User.from_semicolon_separated_str(args.user)
        except ValueError as ex:
            print(ex)
            sys.exit()
    else:
        if args.user not in known_users.keys():
            print(f"Cannot find user '{args.user}' in the known users database.")
            sys.exit()
        user = known_users[args.user]

    commit_as(user, args=unknown_args)