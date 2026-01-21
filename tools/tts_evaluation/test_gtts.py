from gtts import gTTS
import os

def synthesize_with_gtts(text, output_filename="gtts_output.mp3"):
    """Synthesizes speech from the input string of text using gTTS."""
    try:
        tts = gTTS(text=text, lang='it')
        tts.save(output_filename)
        print(f"Audio content written to file '{output_filename}'")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    text_to_synthesize = "Ciao Buddy, bentornato a casa. Credo sia stata una bella giornata visto che il clima a strasburgo era gradevole."
    synthesize_with_gtts(text_to_synthesize)
