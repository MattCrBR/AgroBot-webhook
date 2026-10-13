import os
import time
import requests
import random
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv

load_dotenv()

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")

# Modo desenvolvimento: só processa mensagens dessas conversas
ALLOWED_NUMBERS = {
    n.strip() for n in os.getenv("ALLOWED_NUMBERS", "").split(",") if n.strip()
}

# Ignora eventos mais antigos que isso (evita responder backlog após ficar offline)
MAX_AGE_SECONDS = 120

# IDs das mensagens enviadas pelo próprio bot (para não responder a si mesmo)
sent_message_ids: set[str] = set()

# IDs de mensagens já aceitas (evita processar o mesmo evento duas vezes)
processed_ids: set[str] = set()

app = FastAPI()


def get_image_base64(message_id: str) -> str | None:
    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY,
    }
    body = {"message": {"key": {"id": message_id}}}

    response = requests.post(url, headers=headers, json=body)

    if response.ok:
        return response.json().get("base64")

    print(f"Erro ao buscar mídia: {response.status_code}")
    return None

def send_text(number: str, text: str) -> None:
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY,
    }
    body = {
        "number": number,
        "text": text,
        "delay": random.randint(2000, 4000),  # 2 a 4 segundos
    }

    response = requests.post(url, headers=headers, json=body)

    if response.ok:
        sent_id = response.json().get("key", {}).get("id")
        if sent_id:
            sent_message_ids.add(sent_id)
    else:
        print(f"Erro ao enviar mensagem: {response.status_code}")

def extract_number(jid: str) -> str:
    return jid.split("@")[0]


def should_process(key: dict) -> bool:
    remote_jid = key.get("remoteJid", "")

    # Nunca processa grupos
    if remote_jid.endswith("@g.us"):
        return False

    # Só processa conversas com números da lista de permitidos
    number = extract_number(key.get("remoteJidAlt") or remote_jid)
    return number in ALLOWED_NUMBERS

def process_message(key: dict, message: dict, message_type: str) -> None:
    message_id = key.get("id", "")
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)
    number = extract_number(key.get("remoteJidAlt") or remote_jid)

    print("=== Mensagem recebida ===")
    print(f"ID: {message_id}")
    print(f"De: {remote_jid}")
    print(f"fromMe: {from_me}")
    print(f"Tipo: {message_type}")

    if message_type == "conversation":
        print(f"Texto: {message.get('conversation')}")
        send_text(number, "Oi! Me manda uma foto da praga na planta de milho que eu te ajudo. 🌽")

    elif message_type == "imageMessage":
        image_data = message.get("imageMessage", {})
        print(f"Mimetype: {image_data.get('mimetype')}")
        print(f"Caption: {image_data.get('caption')}")

        base64_image = get_image_base64(message_id)
        if base64_image:
            print(f"Imagem decodificada com sucesso ({len(base64_image)} caracteres em base64)")
            send_text(number, "Recebi sua foto! Em breve vou analisar.")
        else:
            print("Falha ao obter a imagem")
            send_text(number, "Não consegui abrir a foto. Pode mandar de novo?")

def event_age_seconds(data: dict) -> int:
    ts = data.get("messageTimestamp")
    if isinstance(ts, dict):
        ts = ts.get("low")
    return int(time.time()) - int(ts) if ts else 0


@app.get("/")
def health_check():
    return {"status": "AgroBot webhook online"}


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})
    message_type = data.get("messageType", "")
    message_id = key.get("id", "")

    if event_age_seconds(data) > MAX_AGE_SECONDS:
        return {"status": "stale"}

    if message_id in sent_message_ids:
        return {"status": "own_reply"}

    if not should_process(key):
        return {"status": "ignored"}

    if message_id in processed_ids:
        return {"status": "duplicate"}
    processed_ids.add(message_id)

    background_tasks.add_task(process_message, key, message, message_type)
    return {"status": "received"}