import time
from google import genai
from google.genai import types

# --- CONFIGURAZIONE ---
API_KEY = "INSERISCI_LA_TUA_API_KEY_QUI"

def test_gemini_merge_v2(old_text, new_text):
    print(f"\n--- AVVIO TEST MERGE CON GEMINI FLASH (Nuova SDK) ---")
    
    if API_KEY.startswith("INSERISCI"):
        print("❌ ERRORE: Manca la API Key.")
        return

    # 1. Inizializzazione del Client
    client = genai.Client(api_key=API_KEY)

    # 2. Configurazione (Temperature, System Instruction)
    # Nella nuova SDK, la system instruction va nella config
    merge_config = types.GenerateContentConfig(
        system_instruction="Sei un editor di database preciso. Unisci le due informazioni fornite in una singola frase in Italiano corretto, mantenendo i dettagli e usando la terza persona.",
        temperature=0.1
    )

    # 3. Costruzione del Prompt
    prompt = f"""
    Informazione A (Esistente): {old_text}
    Informazione B (Nuova): {new_text}

    Uniscile in una sola frase coerente senza preamboli:
    """

    start_time = time.time()
    
    try:
        print("☁️  Invio richiesta a Gemini Flash...")
        
        # 4. Chiamata al Modello
        response = client.models.generate_content(
            model='gemini-flash-lite-latest',
            config=merge_config,
            contents=prompt
        )
        
        duration = time.time() - start_time
        
        # Estrazione testo (molto più pulita nella nuova SDK)
        merged_text = response.text.strip()
        
        print(f"✅ Successo in {duration:.2f} secondi!")
        print(f"🔹 INPUT A: {old_text}")
        print(f"🔹 INPUT B: {new_text}")
        print(f"🔶 OUTPUT:  {merged_text}")
        
        return merged_text

    except Exception as e:
        print(f"❌ Errore API: {e}")
        return None

# --- ESECUZIONE ---
if __name__ == "__main__":
    caso_a = "All'utente piace molto il tennis e il suo tennista preferito è Musetti."
    caso_b = "L'utente a volte gioca a tennis nel weekend e segue con passione il tennista Sinner."
    
    test_gemini_merge_v2(caso_a, caso_b)