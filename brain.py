from typing import Optional
import database_buddy


class Brain:
    """Very small reasoning layer that uses DatabaseBuddy for context."""

    def __init__(self, db: Optional[database_buddy.DatabaseBuddy] = None):
        self.db = db

    def _simple_policy(self, prompt: str) -> str:
        p = prompt.strip()
        if not p:
            return "I didn't receive any input."
        if "hello" in p.lower() or "hi" in p.lower():
            return "Hello — I'm Buddy. How can I help?"
        if p.endswith("?"):
            return "That's an interesting question. Can you share more context?"
        return f"I heard: {p}"

    def process_and_respond(self, prompt: str) -> str:
        if self.db:
            self.db.save_message("user", prompt)
        resp = self._simple_policy(prompt)
        if self.db:
            self.db.save_message("assistant", resp)
        return resp
