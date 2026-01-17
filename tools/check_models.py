import os
from dotenv import load_dotenv
from google import genai

def check_buddy_models():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ Errore: GOOGLE_API_KEY non trovata nel file .env")
        return

    client = genai.Client(api_key=api_key)

    print("\n--- 🧠 Verifica Modelli Buddy OS (SDK 2026) ---")
    print(f"{'Nome Modello':<40} | {'Capacità Speciali':<25}")
    print("-" * 70)
    
    try:
        # Recupera i modelli
        models = client.models.list()
        
        for m in models:
            # Identifichiamo le capacità basandoci sul nome e sulle caratteristiche
            name_lower = m.name.lower()
            features = []

            # I modelli Flash e Pro della nuova generazione supportano tutto
            if "flash" in name_lower or "pro" in name_lower:
                if "2.5" in name_lower or "2.0" in name_lower:
                    features.append("👂 Audio Nativo")
                    features.append("👁️ Vision")
            
            if "lite" in name_lower:
                features.append("⚡ Fast")

            feat_str = ", ".join(features) if features else "📝 Testo"
            
            print(f"{m.name:<40} | {feat_str}")

        print("\n✅ Connessione riuscita. Buddy è pronto a evolversi.")
        
    except Exception as e:
        print(f"❌ Errore durante l'ispezione: {e}")
        print("\nSuggerimento: Verifica di aver installato 'google-genai' e non 'google-generativeai'.")

if __name__ == "__main__":
    check_buddy_models()