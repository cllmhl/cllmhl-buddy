"""
Memory Store - Gestione persistenza SQLite + ChromaDB
"""

import sqlite3
import chromadb
from chromadb.config import Settings
import time


class MemoryStore:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
             raise RuntimeError("MemoryStore not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def initialize(cls, db_name, chroma_path):
        if cls._instance is not None:
             # Idempotente: se già inizializzato, ignoriamo (o potremmo loggare warning)
             return cls._instance
        cls._instance = cls(db_name, chroma_path)
        return cls._instance

    def __init__(self, db_name, chroma_path):
        if MemoryStore._instance is not None and MemoryStore._instance != self:
             raise RuntimeError("Use MemoryStore.get_instance()")
        
        # 1. Setup SQLite per History (fatti)
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.cursor = self.conn.cursor()
        
        # 2. Setup ChromaDB per Memoria Permanente
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        # Creiamo o recuperiamo la collezione per i fatti
        self.collection = self.chroma_client.get_or_create_collection(name="memoria_buddy")
        
        self.create_tables()

    def create_tables(self):
        # Tabella history per i fatti
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                session_id TEXT, -- New column for session tracking
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    # --- METODI SQLITE (HISTORY) ---
    def add_history(self, role, content, session_id=None):
        self.cursor.execute("INSERT INTO history (role, content, session_id) VALUES (?, ?, ?)", (role, content, session_id))
        self.conn.commit()

    def get_unprocessed_history(self):
        self.cursor.execute("SELECT id, role, content FROM history WHERE processed = 0")
        return self.cursor.fetchall()

    def get_unarchived_sessions(self):
        """Restituisce le sessioni che hanno almeno un record non processato."""
        self.cursor.execute("SELECT DISTINCT session_id FROM history WHERE processed = 0 AND session_id IS NOT NULL ORDER BY session_id")
        return [row[0] for row in self.cursor.fetchall()]

    def get_unprocessed_history_by_session(self, session_id):
        """Restituisce i record non processati di una specifica sessione."""
        self.cursor.execute("SELECT id, role, content FROM history WHERE processed = 0 AND session_id = ?", (session_id,))
        return self.cursor.fetchall()

    def mark_as_processed(self, ids):
        if not ids: return
        placeholders = ', '.join(['?'] * len(ids))
        self.cursor.execute(f"UPDATE history SET processed = 1 WHERE id IN ({placeholders})", ids)
        self.conn.commit()

    # --- METODI CHROMADB (PERMANENT MEMORY) ---
    def add_permanent_memory(self, fact, category, notes, importance):
        """Salva un fatto in modo vettoriale su ChromaDB."""
        self.collection.add(
            documents=[fact],
            metadatas=[{
                "category": category, 
                "notes": notes, 
                "importance": int(importance),
                "ts": time.time(),
                "access_count": 0
            }],
            ids=[f"mem_{time.time()}"]
        )

    def get_semantic_memories(self, query_text, limit=5):
        """Cerca i ricordi più simili a quello che dice l'utente."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=limit
        )
        # Restituiamo solo i testi (documents) trovati
        return results['documents'][0] if results['documents'] else []

    def get_high_priority_memories(self, threshold=4):
        """Recupera le memorie ad alta priorità (es. importanza >= 4)."""
        results = self.collection.get(
            where={"importance": {"$gte": threshold}}
        )
        return results['documents']

    # --- DATA MANAGEMENT METHODS ---
    def reset_all_processed_flags(self):
        """Reset all processed flags to 0 in SQLite history table."""
        self.cursor.execute("UPDATE history SET processed = 0")
        self.conn.commit()
        affected_rows = self.cursor.rowcount
        return affected_rows

    def clear_all_permanent_memories(self):
        """Remove all data from ChromaDB collection."""
        # Get all IDs first
        results = self.collection.get()
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            return len(results['ids'])
        return 0

    def get_all_history(self, limit=None):
        """Get all history records ordered by most recent first."""
        if limit:
            self.cursor.execute("SELECT id, role, content, session_id, ts, processed FROM history ORDER BY id DESC LIMIT ?", (limit,))
        else:
            self.cursor.execute("SELECT id, role, content, session_id, ts, processed FROM history ORDER BY id DESC")
        return self.cursor.fetchall()

    def get_all_permanent_memories(self):
        """Get all permanent memories from ChromaDB."""
        results = self.collection.get()
        return {
            'ids': results['ids'] or [],
            'documents': results['documents'] or [],
            'metadatas': results['metadatas'] or []
        }

    def get_memory_stats(self):
        """Get statistics about stored data."""
        # SQLite stats
        self.cursor.execute("SELECT COUNT(*) FROM history")
        total_history = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM history WHERE processed = 0")
        unprocessed_history = self.cursor.fetchone()[0]
        
        # ChromaDB stats
        permanent_count = self.collection.count()
        
        return {
            'total_history': total_history,
            'unprocessed_history': unprocessed_history,
            'processed_history': total_history - unprocessed_history,
            'permanent_memories': permanent_count
        }

    def close(self):
        self.conn.close()