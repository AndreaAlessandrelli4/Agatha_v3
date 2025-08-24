import asyncio
import io
import os
import numpy as np
import soundfile as sf
import streamlit as st
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SAMPLERATE = 24000
CHANNELS = 1


async def speak_stream_text(text):
    """Genera audio TTS e riproduce su Streamlit"""
    leftover = b""

    async with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        input=text,
        response_format="pcm"
    ) as response:

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
    """Chat con streaming testuale e output TTS"""
    full_text = ""

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}],
        stream=True
    )

    placeholder = st.empty()
    async for event in stream:
        delta = event.choices[0].delta
        if delta.content:
            token = delta.content
            full_text += token
            placeholder.markdown(full_text)  # aggiorna live il testo

    # parla alla fine
    await speak_stream_text(full_text.strip())
