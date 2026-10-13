import os
from dotenv import load_dotenv

load_dotenv()

# Evolution API
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")

# Modo desenvolvimento: só processa mensagens dessas conversas
ALLOWED_NUMBERS = {
    n.strip() for n in os.getenv("ALLOWED_NUMBERS", "").split(",") if n.strip()
}

# Ignora eventos mais antigos que isso (evita responder backlog após ficar offline)
MAX_AGE_SECONDS = 120

# Registro do feedback 👍/👎
FEEDBACK_FILE = "feedback.jsonl"

# Tipos de mensagem que merecem uma resposta pedindo a foto
TIPOS_SEM_SUPORTE = {
    "audioMessage", "stickerMessage", "videoMessage",
    "documentMessage", "contactMessage", "locationMessage",
}

# Nível de log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()