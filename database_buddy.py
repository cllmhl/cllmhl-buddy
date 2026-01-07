import sqlite3

class BuddyDatabase:
    def __init__(self, db_path="buddy_memory.db"):
        self.db_path = db_path
        self._setup()

    def _setup(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;") # Permette letture/scritture contemporanee
            # Aggiungiamo 'processed' per segnare cosa ha letto l'Archivista
            conn.execute('''CREATE TABLE IF NOT EXISTS history 
                            (id INTEGER PRIMARY KEY, role TEXT, text TEXT, 
                             processed INTEGER DEFAULT 0, ts DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS memories 
                            (id INTEGER PRIMARY KEY, content TEXT, category TEXT, metadata TEXT, importance INTEGER)''')

    def add_history(self, role, text):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (role, text) VALUES (?, ?)", (role, text))

    def get_unprocessed_history(self):
        """Recupera tutti i log non ancora analizzati dall'Archivista."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, role, text FROM history WHERE processed = 0")
            return cursor.fetchall()

    def mark_as_processed(self, ids):
        """Segna i log come analizzati usando una lista di ID."""
        if not ids: return
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join(['?'] * len(ids))
            conn.execute(f"UPDATE history SET processed = 1 WHERE id IN ({placeholders})", ids)

    def add_permanent_memory(self, content, category, metadata, importance):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO memories (content, category, metadata, importance) VALUES (?, ?, ?, ?)", 
                         (content, category, metadata, importance))