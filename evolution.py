import random
import requests

from config import EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE

TIMEOUT_SECONDS = 30

# IDs das mensagens enviadas pelo próprio bot (para não responder a si mesmo)
sent_message_ids: set[str] = set()


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY,
    }


def get_image_base64(message_id: str) -> str | None:
    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE}"
    body = {"message": {"key": {"id": message_id}}}

    try:
        response = requests.post(url, headers=_headers(), json=body, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        print(f"Erro de rede ao buscar mídia: {type(e).__name__}")
        return None

    if response.ok:
        return response.json().get("base64")

    print(f"Erro ao buscar mídia: {response.status_code}")
    return None


def send_text(number: str, text: str) -> None:
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    body = {
        "number": number,
        "text": text,
        "delay": random.randint(2000, 4000),  # 2 a 4 segundos
    }

    try:
        response = requests.post(url, headers=_headers(), json=body, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        print(f"Erro de rede ao enviar mensagem: {type(e).__name__}")
        return

    if response.ok:
        sent_id = response.json().get("key", {}).get("id")
        if sent_id:
            sent_message_ids.add(sent_id)
    else:
        print(f"Erro ao enviar mensagem: {response.status_code}")