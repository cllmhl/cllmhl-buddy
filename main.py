#!/usr/bin/env python3
import argparse
import sys
from database_buddy import DatabaseBuddy
from brain import Brain


def run_interactive(db_path: str = "buddy.db") -> None:
    db = DatabaseBuddy(db_path)
    brain = Brain(db)
    try:
        print("Buddy interactive — type 'exit' or Ctrl-C to quit.")
        while True:
            try:
                prompt = input("You: ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if prompt.strip().lower() in ("exit", "quit"):
                break
            resp = brain.process_and_respond(prompt)
            print("Buddy:", resp)
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Buddy CLI")
    parser.add_argument("-m", "--message", help="Send a single message and exit")
    parser.add_argument("--db", default="buddy.db", help="Path to SQLite DB file")
    args = parser.parse_args(argv)

    db = DatabaseBuddy(args.db)
    brain = Brain(db)
    try:
        if args.message:
            print(brain.process_and_respond(args.message))
        else:
            run_interactive(args.db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
