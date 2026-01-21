from pathlib import Path
from dotenv import load_dotenv
from google.cloud import texttospeech
import os

def list_voices():
    """Lists the available voices."""
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()

    # Performs the list voices request
    voices = client.list_voices()

    for voice in voices.voices:
        # Filter for Italian male voices
        if "it-IT" in voice.language_codes and voice.ssml_gender == texttospeech.SsmlVoiceGender.MALE:
            # Display the voice's name. Example: tpc-vocoded
            print(f"Name: {voice.name}")

            # Display the supported language codes for this voice. Example: "en-US"
            for language_code in voice.language_codes:
                print(f"Supported language: {language_code}")

            ssml_gender = texttospeech.SsmlVoiceGender(voice.ssml_gender)

            # Display the SSML Voice Gender
            print(f"SSML Voice Gender: {ssml_gender.name}")

            # Display the natural sample rate hertz for this voice. Example: 24000
            print(f"Natural Sample Rate Hertz: {voice.natural_sample_rate_hertz}\n")

def synthesize_text(text, voice_name, output_filename):
    """Synthesizes speech from the input string of text."""
    
    # Check if credentials are set
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        return

    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.VoiceSelectionParams(
        language_code="it-IT",
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )

    # The response's audio_content is binary.
    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file "{output_filename}"')

def synthesize_italian_male_voices(text):
    """Synthesizes speech from the input string of text for all Italian male voices."""
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices().voices

    for voice in voices:
        if "it-IT" in voice.language_codes and voice.ssml_gender == texttospeech.SsmlVoiceGender.MALE:
            print(f"Synthesizing with voice: {voice.name}")
            output_filename = f"{voice.name}.mp3"
            synthesize_text(text, voice.name, output_filename)

if __name__ == "__main__":
    # 1. Carica .env per API keys
    env_path = Path(os.getenv('BUDDY_HOME', '.')).resolve() / '.env'
    load_dotenv(env_path)
    text_to_synthesize = "Ciao Buddy, bentornato a casa. Credo sia stata una bella giornata visto che il clima a strasburgo era gradevole."
    synthesize_italian_male_voices(text_to_synthesize)
