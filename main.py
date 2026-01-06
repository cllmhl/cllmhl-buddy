import os
import logging
from dotenv import load_dotenv
from brain import BuddyBrain
from database_buddy import BuddyDatabase

# Setup logging professionale ma semplice
logging.basicConfig(filename='buddy_system.log', level=logging.INFO)

def main():
    load_dotenv()
    db = BuddyDatabase()
    buddy = BuddyBrain(os.getenv("GOOGLE_API_KEY"))

    print("--- Buddy OS Online (Raspberry Pi 5) ---")

    while True:
        try:
            user_input = input("Tu: ")
            if user_input.lower() in ["esci", "quit"]: break

            # 1. Salva input nel DB (Ruolo: user)
            db.add_history("user", user_input)

            # 2. Genera risposta con la personalità ironica
            risposta = buddy.respond(user_input)
            
            # 3. Salva risposta nel DB (Ruolo: model)
            db.add_history("model", risposta)

            print(f"Buddy: {risposta}")

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()