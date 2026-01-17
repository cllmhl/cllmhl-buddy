import sqlite3
import chromadb

DB_NAME = "buddy_system.db"
CHROMA_PATH = "./buddy_memory"

print(f"--- Controllo Database SQLite: {DB_NAME} ---")
try:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    print("\n--- STORIA (Ultime 5 conversazioni) ---")
    for row in cursor.execute("SELECT id, role, content, ts FROM history ORDER BY id DESC LIMIT 5"):
        print(row)
    conn.close()
except Exception as e:
    print(f"Errore: {e}")

print(f"\n--- Controllo Database Vettoriale: {CHROMA_PATH} ---")
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="memoria_buddy")
print(f"Trovati {collection.count()} ricordi nella collezione 'memoria_buddy'.")