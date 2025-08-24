import asyncio
import io
import os
import numpy as np
import soundfile as sf
import streamlit as st
from openai import AsyncOpenAI
from fraud_ai.config import OPENAI_API_KEY

# se sounddevice è disponibile e c'è un device audio locale
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SAMPLERATE = 24000
CHANNELS = 1


async def speak_stream_text(text):
    """Stream TTS: locale usa sounddevice, su Streamlit Cloud usa st.audio."""
    leftover = b""

    async with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        input=text,
        response_format="pcm"
    ) as response:

        # === Caso 1: siamo in locale con sounddevice ===
        if HAS_SOUNDDEVICE and not os.getenv("STREAMLIT_RUNTIME"):
            with sd.OutputStream(samplerate=SAMPLERATE, channels=CHANNELS, dtype='int16') as stream:
                async for chunk in response.iter_bytes():
                    chunk = leftover + chunk
                    full_count = len(chunk) // 2
                    complete_bytes = chunk[: full_count * 2]
                    leftover = chunk[full_count * 2:]
                    if complete_bytes:
                        stream.write(np.frombuffer(complete_bytes, dtype=np.int16))

        # === Caso 2: siamo su Streamlit Cloud (usa st.audio) ===
        else:
            audio_buffer = io.BytesIO()
            with sf.SoundFile(
                audio_buffer, mode="w",
                samplerate=SAMPLERATE, channels=CHANNELS, subtype="PCM_16"
            ) as f:
                async for chunk in response.iter_bytes():
                    chunk = leftover + chunk
                    full_count = len(chunk) // 2
                    complete_bytes = chunk[: full_count * 2]
                    leftover = chunk[full_count * 2:]
                    if complete_bytes:
                        f.write(np.frombuffer(complete_bytes, dtype=np.int16))

            audio_buffer.seek(0)
            st.audio(audio_buffer, format="audio/wav")


async def chat_and_speak(user_input):
    """Stream LLM output live into TTS and play to completion."""
    full_text = ""

    # Stream chat completion tokens
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}],
        stream=True
    )

    async for event in stream:
        delta = event.choices[0].delta
        if delta.content:
            token = delta.content
            print(token, end="", flush=True)
            full_text += token

    print()  # newline

    # Now speak the *entire* generated response
    await speak_stream_text(full_text.strip())


async def main():
    print("💬 Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            print("👋 Goodbye!")
            break
        await chat_and_speak(user_input)


if __name__ == "__main__":
    asyncio.run(main())
