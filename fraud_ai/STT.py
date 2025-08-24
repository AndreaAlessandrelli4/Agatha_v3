import streamlit as st
import tempfile
import openai
from elevenlabs import ElevenLabs
from fraud_ai.config import ELEVEN_KEY, OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
eleven_client = ElevenLabs(api_key=ELEVEN_KEY)


def transcribe_with_elevenlabs(temp_path):
    with open(temp_path, "rb") as f:
        result_stream = eleven_client.speech_to_text.convert(
            model_id="scribe_v1",  # o "scribe_v1_experimental"
            file=f
        )

        texts, lang_code, lang_prob = [], None, None
        for key, value in result_stream:
            if key == "language_code":
                lang_code = value
            elif key == "language_probability":
                lang_prob = value
            elif key == "text":
                texts.append(value)

    final_text = " ".join(t.strip() for t in texts if t.strip())
    return final_text.strip(), lang_code, lang_prob


def listen_and_transcribe(
    stt_enabled=True,
    stt_provider="openai",
    language=None
):
    # === fallback: testo manuale se STT disattivato ===
    if not stt_enabled:
        manual_text = st.text_input("Customer:")
        return manual_text if manual_text else "silence"

    # === caricamento file audio dal browser ===
    uploaded_audio = st.file_uploader("🎤 Carica una registrazione vocale", type=["wav", "mp3", "m4a"])
    if not uploaded_audio:
        return "silence"

    # salvataggio temporaneo
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(uploaded_audio.read())
        temp_path = tmp.name

    # === trascrizione ===
    if stt_provider.lower() == "openai":
        with open(temp_path, "rb") as f:
            resp = openai.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                language=language
            )
        transcription_text = resp.text.strip()
        return transcription_text if transcription_text else "silence"

    elif stt_provider.lower() == "elevenlabs":
        transcription_text, _, _ = transcribe_with_elevenlabs(temp_path)
        return transcription_text if transcription_text else "silence"

    else:
        raise ValueError("stt_provider must be 'openai' or 'elevenlabs'.")
