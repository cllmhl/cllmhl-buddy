"""
Memory Store - Gestione persistenza SQLite + ChromaDB
"""

from http import client
import sqlite3
import chromadb
from chromadb.config import Settings
from google import genai
from google.genai import types
import logging
import time


class MemoryStore:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
             raise RuntimeError("MemoryStore not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def initialize(cls, api_key: str, memory_config):
        if cls._instance is not None:
             # Idempotente: se già inizializzato, ignoriamo (o potremmo loggare warning)
             return cls._instance
        cls._instance = cls(api_key, memory_config)
        return cls._instance

    def __init__(self, api_key: str, memory_config):
        if MemoryStore._instance is not None and MemoryStore._instance != self:
             raise RuntimeError("Use MemoryStore.get_instance()")
        
        self.logger = logging.getLogger(__name__)

        # 1. Setup SQLite per History (fatti)
        self.conn = sqlite3.connect(memory_config['sqlite_path'], check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.cursor = self.conn.cursor()
        self.create_tables()

        # 2. Setup ChromaDB per Memoria Permanente
        self.chroma_client = chromadb.PersistentClient(path=memory_config['chroma_path'])
        # Creiamo o recuperiamo la collezione per i fatti con spazio vettoriale cosine per similarità
        self.collection = self.chroma_client.get_or_create_collection(name="memoria_buddy",metadata={"hnsw:space": "cosine"})
        
        # 3. Inizializzazione del Client e della config per il merge
        self.reinforce_threshold = float(memory_config['reinforce_threshold'])
        self.model_id = memory_config['model_id']
        self.client = genai.Client(api_key=api_key)
        self.merge_config = types.GenerateContentConfig(
            system_instruction=memory_config['system_instruction'],
            temperature=memory_config['temperature']
        )
        
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
    def add_permanent_memory(self, fact, category, importance):
        """Salva un fatto in modo vettoriale su ChromaDB.
        
        Se esiste già una memoria simile (distanza <= reinforce_threshold) nella stessa categoria,
        rinforza quella esistente invece di crearne una nuova.
        """
        # Cerca memorie simili nella stessa categoria
        results = self.collection.query(
            query_texts=[fact],
            n_results=5,  # Prendiamo top 5 per controllare la categoria
            where={"category": category}
        )
        
        # Se troviamo risultati simili nella stessa categoria
        if (results.get('ids') and results['ids'] and results['ids'][0] and 
            results.get('distances') and results['distances'] and results['distances'][0] and
            results.get('documents') and results['documents'] and results['documents'][0] and
            results.get('metadatas') and results['metadatas'] and results['metadatas'][0]):
            
            for i, distance in enumerate(results['distances'][0]):
                # Se la distanza è sotto la soglia, rinforziamo
                if distance <= self.reinforce_threshold:
                    existing_id = results['ids'][0][i]
                    existing_doc = results['documents'][0][i]
                    existing_metadata = results['metadatas'][0][i]
                    
                    # Merge del fatto nuovo con quello esistente usando LLM 
                    prompt = f"""
                    Informazione A (Esistente): {existing_doc}
                    Informazione B (Nuova): {fact}

                    Uniscile in una sola frase coerente senza preamboli:
                    """
                    # Chiamiamo il modello per il merge
                    result = self.client.models.generate_content(
                        model=self.model_id,
                        config=self.merge_config,
                        contents=prompt
                    )
                    updated_doc = (result.text or '').strip()
                    
                    # Incrementa reinforcement_count (type-safe cast, fail-fast se campo mancante)
                    old_count = existing_metadata['reinforcement_count']
                    new_reinforcement_count = int(old_count) + 1 if isinstance(old_count, (int, float)) else 1
                    
                    # Access count (type-safe cast, fail-fast se campo mancante)
                    old_access = existing_metadata['access_count']
                    access_count = int(old_access) if isinstance(old_access, (int, float)) else 0
                    
                    # Timestamp (type-safe cast, fail-fast se campo mancante)
                    old_ts = existing_metadata['ts']
                    ts_value = float(old_ts) if isinstance(old_ts, (int, float)) else time.time()
                    
                    # Aggiorna la memoria esistente
                    self.collection.update(
                        ids=[existing_id],
                        documents=[updated_doc],
                        metadatas=[{
                            "category": category,
                            "importance": int(importance),
                            "ts": ts_value,
                            "reinforcement_count": new_reinforcement_count,
                            "access_count": access_count
                        }]
                    )
                    self.logger.info(
                        f"🔄 Memory reinforced [category={category}, importance={importance}, "
                        f"reinforcements={new_reinforcement_count}, distance={distance:.3f}]: {updated_doc[:100]}"
                    )
                    return  # Memoria rinforzata, non inseriamo
        
        # Nessuna memoria simile trovata, inseriamo nuova
        self.collection.add(
            documents=[fact],
            metadatas=[{
                "category": category, 
                "importance": int(importance),
                "ts": time.time(),
                "reinforcement_count": 0,
                "access_count": 0
            }],
            ids=[f"mem_{time.time()}"]
        )
        self.logger.info(
            f"✨ New memory stored [category={category}, importance={importance}]: {fact[:100]}"
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