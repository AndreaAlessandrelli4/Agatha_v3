import streamlit as st

# statica → resta invariata
DATABASE_URL = "sqlite:///fraud_ai.db"

class _DynamicKey:
    """Wrapper che legge una chiave dinamica da st.session_state"""
    def __init__(self, key_name: str):
        self.key_name = key_name

    def __str__(self) -> str:
        return self.__call__()

    def __repr__(self) -> str:
        return f"<DynamicKey {self.key_name}={self.__call__()!r}>"

    def __call__(self) -> str | None:
        return st.session_state.get(self.key_name, None)

    # così puoi usarlo come se fosse una stringa
    def __getattr__(self, item):
        return getattr(str(self), item)

# queste sembrano "variabili", ma in realtà leggono dalla sessione
OPENAI_API_KEY = _DynamicKey("openai_api_key")
ELEVEN_KEY = _DynamicKey("eleven_api_key")