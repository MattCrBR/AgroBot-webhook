import time
import json

from config import (
    ALLOWED_NUMBERS,
    MAX_AGE_SECONDS,
    FEEDBACK_FILE,
    TIPOS_SEM_SUPORTE
)

from fastapi import FastAPI, Request, BackgroundTasks
from pipeline import analisar_foto
from evolution import get_image_base64, send_text, sent_message_ids

# IDs de mensagens já aceitas (evita processar o mesmo evento duas vezes)
processed_ids: set[str] = set()

# Último diagnóstico enviado a cada número (liga o 👍/👎 à resposta certa)
last_diagnosis: dict[str, dict] = {}

app = FastAPI()

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

def registrar_feedback(number: str, valor: str) -> None:
    diagnostico = last_diagnosis.pop(number, {})
    registro = {"ts": int(time.time()), "feedback": valor, **diagnostico}
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")

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

    if message_type in ("conversation", "extendedTextMessage"):
        if message_type == "conversation":
            texto = message.get("conversation") or ""
        else:
            texto = message.get("extendedTextMessage", {}).get("text") or ""
        texto = texto.strip()
        print(f"Texto: {texto}")

        # Feedback (👍/👎) sobre o último diagnóstico enviado a esse número
        if number in last_diagnosis and texto.startswith(("👍", "👎")):
            registrar_feedback(number, "positivo" if texto.startswith("👍") else "negativo")
            send_text(number, "Obrigado pelo retorno! 🌽")
        else:
            send_text(number, "Oi! Me manda uma foto da praga na planta de milho que eu te ajudo. 🌽")

    elif message_type == "imageMessage":
        image_data = message.get("imageMessage", {})
        print(f"Mimetype: {image_data.get('mimetype')}")
        print(f"Caption: {image_data.get('caption')}")

        base64_image = get_image_base64(message_id)
        if base64_image:
            print(f"Imagem decodificada com sucesso ({len(base64_image)} caracteres em base64)")
            try:
                resultado = analisar_foto(base64_image)
                resposta = resultado["texto"]
                if resultado["diagnostico"]:
                    last_diagnosis[number] = resultado["diagnostico"]
            except Exception as e:
                print(f"Erro no pipeline: {type(e).__name__}")
                resposta = "Tive um problema para analisar a foto. Pode tentar de novo daqui a pouco?"
            send_text(number, resposta)
        else:
            print("Falha ao obter a imagem")
            send_text(number, "Não consegui abrir a foto. Pode mandar de novo?")

    elif message_type in TIPOS_SEM_SUPORTE:
        send_text(number, "Ainda não consigo entender esse tipo de mensagem. Me manda uma foto da praga na planta de milho que eu te ajudo. 🌽")

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