import asyncio
from edge_tts import Communicate

TEXT = "Ciao Buddy, bentornato a casa. Credo sia stata una bella giornata visto che il clima a strasburgo era gradevole."
VOICES = ["it-IT-DiegoNeural", "it-IT-GiuseppeMultilingualNeural"]

async def main():
    """Main function"""
    for voice in VOICES:
        output_file = f"edge_tts_{voice}.mp3"
        communicate = Communicate(TEXT, voice)
        await communicate.save(output_file)
        print(f"Audio content written to file '{output_file}'")

if __name__ == "__main__":
    asyncio.run(main())
