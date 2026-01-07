from database_buddy import BuddyDatabase
from archivist import BuddyArchivist
from dotenv import load_dotenv
import os

# 1. Inizializza i componenti
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
db = BuddyDatabase()
archivist = BuddyArchivist(api_key)

# 2. Simula una conversazione aggiungendo log manualmente in SQL
db.add_history("user", "Ciao Buddy, io mi chiamo Michele e vivo a Ferrara.")
db.add_history("model", "Piacere di conoscerti Michele! Ferrara è una bellissima città.")

# 3. Lancia l'archivista
print("Lancio l'archivista...")
archivist.distill_and_save(db)

# 4. Verifica se ChromaDB ha salvato qualcosa
print("\nRicerca semantica per 'Chi sono?':")
ricordi = db.get_semantic_memories("Chi sono?")
print(ricordi)
print("\nRicerca semantica per 'Come mi chiamo?':")
ricordi = db.get_semantic_memories("Come mi chiamo?")
print(ricordi)
print("\nRicerca semantica per 'Dove vivo?':")
ricordi = db.get_semantic_memories("Dove vivo?")
print(ricordi)