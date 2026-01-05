import sqlite3
from typing import List, Tuple


class DatabaseBuddy:
    """Lightweight SQLite wrapper for storing conversation messages."""

    def __init__(self, db_path: str = "buddy.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.init_db()

    def init_db(self) -> None:
        c = self._conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def save_message(self, role: str, content: str) -> None:
        c = self._conn.cursor()
        c.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        self._conn.commit()

    def get_conversation(self, limit: int = 100) -> List[Tuple[str, str]]:
        c = self._conn.cursor()
        c.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return list(reversed(rows))

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
