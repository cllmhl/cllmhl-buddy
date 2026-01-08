from logging.handlers import RotatingFileHandler
import os
import logging
from dotenv import load_dotenv
import threading
import queue
import time
from database_buddy import BuddyDatabase
from brain import BuddyBrain
from archivist import BuddyArchivist

# Setup logging
handler = RotatingFileHandler('buddy_system.log', maxBytes=10*1024*1024, backupCount=1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

input_queue = queue.Queue()

def keyboard_thread():
    """Ascolta l'input senza stampare prefissi fissi."""
    while True:
        try:
            # Usiamo un input vuoto per non avere il "Tu:" che fluttua
            text = input() 
            if text:
                input_queue.put(text)
        except EOFError:
            break

def main():
    load_dotenv()
    db = BuddyDatabase()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    buddy = BuddyBrain(api_key)
    archivist = BuddyArchivist(api_key=api_key)

    t = threading.Thread(target=keyboard_thread, daemon=True)
    t.start()

    print("\n--- Buddy OS Online ---")
    print("Scrivi un messaggio e premi Invio (digita 'esci' per chiudere)")
    print("\nTu > ", end="", flush=True) # Primo prompt manuale

    last_archive_time = time.time()

    try:
        while True:
            # 1. GESTIONE INPUT
            if not input_queue.empty():
                user_input = input_queue.get()
                
                if user_input.lower() in ["esci", "quit"]:
                    print("\nBuddy: Alla prossima, umano!")
                    break

                # Processamento
                db.add_history("user", user_input)
                risposta = buddy.respond(user_input)
                db.add_history("model", risposta)
                
                # Stampa pulita: andiamo a capo e mostriamo la risposta
                print(f"Buddy > {risposta}")
                print("\nTu > ", end="", flush=True)

            # 2. GESTIONE ARCHIVISTA
            current_time = time.time()
            if current_time - last_archive_time > 30:
                unprocessed = db.get_unprocessed_history()
                if len(unprocessed) > 0:
                    # Usiamo \r per "pulire" la riga del prompt durante l'analisi
                    logging.debug(f"L'Archivista sta analizzando {len(unprocessed)} messaggi...")
                    archivist.distill_and_save(db)
                    logging.debug("Completato.")
                
                last_archive_time = current_time

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nBuddy: Spegnimento in corso...")

if __name__ == "__main__":
    main()