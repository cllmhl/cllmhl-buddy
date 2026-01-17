"""
Memory Store - Gestione persistenza SQLite + ChromaDB
"""

import sqlite3
import chromadb
from chromadb.config import Settings
import time


class MemoryStore:
    def __init__(self, db_name="buddy_system.db", chroma_path="./buddy_memory"):
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
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    # --- METODI SQLITE (HISTORY) ---
    def add_history(self, role, content):
        self.cursor.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
        self.conn.commit()

    def get_unprocessed_history(self):
        self.cursor.execute("SELECT id, role, content FROM history WHERE processed = 0")
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

    def close(self):
        self.conn.close()