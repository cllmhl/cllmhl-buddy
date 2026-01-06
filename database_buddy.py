import sqlite3
import logging

class BuddyDatabase:
    def __init__(self, db_path="buddy_memory.db"):
        self.db_path = db_path
        self._setup()

    def _setup(self):
        with sqlite3.connect(self.db_path) as conn:
            # Tabella per la cronologia recente (RUOLO fondamentale)
            conn.execute('''CREATE TABLE IF NOT EXISTS history 
                            (id INTEGER PRIMARY KEY, role TEXT, text TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            # Tabella per i ricordi a lungo termine (METADATA)
            conn.execute('''CREATE TABLE IF NOT EXISTS memories 
                            (id INTEGER PRIMARY KEY, content TEXT, category TEXT, importance INTEGER)''')

    def add_history(self, role: str, text: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (role, text) VALUES (?, ?)", (role, text))

    def add_permanent_memory(self, content: str, category="generale"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO memories (content, category) VALUES (?, ?)", (content, category))