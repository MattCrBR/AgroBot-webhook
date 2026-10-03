import os
import json
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")
print(f"URL: {EVOLUTION_API_URL}, KEY: {EVOLUTION_API_KEY}, INSTANCE: {EVOLUTION_INSTANCE}")

app = FastAPI()


def get_image_base64(message_id: str) -> str | None:
    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY,
    }
    body = {"message": {"key": {"id": message_id}}}

    response = requests.post(url, headers=headers, json=body)

    if response.ok:  # aceita qualquer status 200-299, não só 200 exato
        return response.json().get("base64")

    print(f"Erro ao buscar mídia: {response.status_code}")
    return None


@app.get("/")
def health_check():
    return {"status": "AgroBot webhook online"}


@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()

    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})
    message_type = data.get("messageType", "")

    message_id = key.get("id", "")
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)

    print("=== Mensagem recebida ===")
    print(f"ID: {message_id}")
    print(f"De: {remote_jid}")
    print(f"fromMe: {from_me}")
    print(f"Tipo: {message_type}")

    if message_type == "conversation":
        print(f"Texto: {message.get('conversation')}")

    elif message_type == "imageMessage":
        image_data = message.get("imageMessage", {})
        print(f"Mimetype: {image_data.get('mimetype')}")
        print(f"Caption: {image_data.get('caption')}")

        base64_image = get_image_base64(message_id)
        if base64_image:
            print(f"Imagem decodificada com sucesso ({len(base64_image)} caracteres em base64)")
        else:
            print("Falha ao obter a imagem")

    return {"status": "received"}