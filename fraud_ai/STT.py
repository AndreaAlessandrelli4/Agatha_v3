import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, ClientSettings
import numpy as np
import tempfile
import soundfile as sf
import openai
from elevenlabs import ElevenLabs
from fraud_ai.config import ELEVEN_KEY, OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
eleven_client = ElevenLabs(api_key=ELEVEN_KEY)

# Funzione per trascrivere file audio con ElevenLabs
def transcribe_with_elevenlabs(temp_path):
    with open(temp_path, "rb") as f:
        result_stream = eleven_client.speech_to_text.convert(
            model_id="scribe_v1",
            file=f
        )
        texts = []
        lang_code = None
        lang_prob = None
        for key, value in result_stream:
            if key == "language_code":
                lang_code = value
            elif key == "language_probability":
                lang_prob = value
            elif key == "text":
                texts.append(value)
    final_text = " ".join(t.strip() for t in texts if t.strip())
    return final_text.strip(), lang_code, lang_prob

# Funzione principale STT live
def listen_and_transcribe_live(stt_provider="openai", language=None):
    st.info("🎙️ Premere **Start** e parlare nel microfono")

    # Config WebRTC
    client_settings = ClientSettings(
        media_stream_constraints={"audio": True, "video": False}
    )

    ctx = webrtc_streamer(
        key="stt",
        mode=WebRtcMode.SENDONLY,
        client_settings=client_settings,
        async_processing=False
    )

    if ctx.audio_receiver:
        frames = ctx.audio_receiver.get_frames(timeout=10)
        if not frames:
            return "silence"

        # Converti i frame in un array numpy
        audio_data = np.concatenate([f.to_ndarray() for f in frames], axis=0)

        # Salva temporaneamente il file audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio_data, 16000)
            temp_path = f.name

        # Trascrizione
        if stt_provider.lower() == "openai":
            with open(temp_path, "rb") as f_audio:
                resp = openai.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=f_audio,
                    language=language
                )
            transcription_text = resp.text.strip()
            return transcription_text if transcription_text else "silence"

        elif stt_provider.lower() == "elevenlabs":
            transcription_text, _, _ = transcribe_with_elevenlabs(temp_path)
            return transcription_text if transcription_text else "silence"

        else:
            raise ValueError("stt_provider must be 'openai' or 'elevenlabs'.")
    else:
        return "silence"
