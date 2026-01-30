import sqlite3
import chromadb

DB_NAME = "data/system.db"
CHROMA_PATH = "data/memory"

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

print("\n--- CONTENUTO MEMORIA ---")
results = collection.get()
ids = results['ids']
documents = results['documents'] if results['documents'] is not None else []
metadatas = results['metadatas'] if results['metadatas'] is not None else []

if not ids:
    print("Nessuna memoria trovata.")
else:
    for i in range(len(ids)):
        print(f"\nID: {ids[i]}")
        doc = documents[i] if i < len(documents) else "N/A"
        meta = metadatas[i] if i < len(metadatas) else "N/A"
        print(f"Documento: {doc}")
        print(f"Metadati: {meta}")