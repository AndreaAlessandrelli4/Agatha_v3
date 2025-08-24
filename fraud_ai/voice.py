import asyncio
import io
import os
import numpy as np
import soundfile as sf
import streamlit as st
from openai import AsyncOpenAI

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SAMPLERATE = 24000
CHANNELS = 1


async def speak_stream_text(text):
    """TTS: locale con sounddevice, su Streamlit con st.audio"""
    leftover = b""

    async with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        input=text,
        response_format="pcm"
    ) as response:

        # 🔹 Caso 1: locale (se hai una scheda audio)
        if HAS_SOUNDDEVICE and not os.getenv("STREAMLIT_SERVER_ENABLED"):
            with sd.OutputStream(
                samplerate=SAMPLERATE, channels=CHANNELS, dtype='int16'
            ) as stream:
                async for chunk in response.iter_bytes():
                    chunk = leftover + chunk
                    full_count = len(chunk) // 2
                    complete_bytes = chunk[: full_count * 2]
                    leftover = chunk[full_count * 2:]
                    if complete_bytes:
                        stream.write(np.frombuffer(complete_bytes, dtype=np.int16))

        # 🔹 Caso 2: su Streamlit Cloud
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
