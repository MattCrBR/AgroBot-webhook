import json
import time
import logging

from config import (
    ALLOWED_NUMBERS,
    MAX_AGE_SECONDS,
    FEEDBACK_FILE,
    TIPOS_SEM_SUPORTE,
)
from evolution import get_image_base64, send_text, sent_message_ids
from pipeline import analisar_foto

logger = logging.getLogger(__name__)

# IDs de mensagens já aceitas (evita processar o mesmo evento duas vezes)
processed_ids: set[str] = set()

# Último diagnóstico enviado a cada número (liga o 👍/👎 à resposta certa)
last_diagnosis: dict[str, dict] = {}


def extract_number(jid: str) -> str:
    return jid.split("@")[0]

def mask_number(number: str) -> str:
    return f"***{number[-4:]}" if len(number) > 4 else "***"

def event_age_seconds(data: dict) -> int:
    ts = data.get("messageTimestamp")
    if isinstance(ts, dict):
        ts = ts.get("low")
    return int(time.time()) - int(ts) if ts else 0


def should_process(key: dict) -> bool:
    remote_jid = key.get("remoteJid", "")

    # Nunca processa grupos
    if remote_jid.endswith("@g.us"):
        return False

    # Só processa conversas com números da lista de permitidos
    number = extract_number(key.get("remoteJidAlt") or remote_jid)
    return number in ALLOWED_NUMBERS


def check_event(data: dict) -> str:
    """Decide o que fazer com um evento. Devolve 'received' se deve ser processado;
    caso contrário, o motivo do descarte."""
    key = data.get("key", {})
    message_id = key.get("id", "")

    if event_age_seconds(data) > MAX_AGE_SECONDS:
        return "stale"

    if message_id in sent_message_ids:
        return "own_reply"

    if not should_process(key):
        return "ignored"

    if message_id in processed_ids:
        return "duplicate"
    processed_ids.add(message_id)

    return "received"


def registrar_feedback(number: str, valor: str) -> None:
    diagnostico = last_diagnosis.pop(number, {})
    registro = {"ts": int(time.time()), "feedback": valor, **diagnostico}
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        logger.info("Feedback registrado: %s", valor)


def process_message(key: dict, message: dict, message_type: str) -> None:
    message_id = key.get("id", "")
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)
    number = extract_number(key.get("remoteJidAlt") or remote_jid)

    logger.info(
        "mensagem recebida | tipo=%s | de=%s | fromMe=%s | id=...%s",
        message_type, mask_number(number), from_me, message_id[-6:],
    )

    if message_type in ("conversation", "extendedTextMessage"):
        if message_type == "conversation":
            texto = message.get("conversation") or ""
        else:
            texto = message.get("extendedTextMessage", {}).get("text") or ""
        texto = texto.strip()

        # Feedback (👍/👎) sobre o último diagnóstico enviado a esse número
        if number in last_diagnosis and texto.startswith(("👍", "👎")):
            registrar_feedback(number, "positivo" if texto.startswith("👍") else "negativo")
            send_text(number, "Obrigado pelo retorno! 🌽")
        else:
            send_text(number, "Oi! Me manda uma foto da praga na planta de milho que eu te ajudo. 🌽")

    elif message_type == "imageMessage":
        image_data = message.get("imageMessage", {})
        logger.info("imagem | mimetype=%s", image_data.get("mimetype"))

        base64_image = get_image_base64(message_id)
        if base64_image:
            logger.info("imagem decodificada (%d caracteres em base64)", len(base64_image))
            try:
                resultado = analisar_foto(base64_image)
                resposta = resultado["texto"]
                if resultado["diagnostico"]:
                    last_diagnosis[number] = resultado["diagnostico"]
            except Exception:
                logger.exception("erro no pipeline")
                resposta = "Tive um problema para analisar a foto. Pode tentar de novo daqui a pouco?"
            send_text(number, resposta)
        else:
            logger.warning("falha ao obter a imagem")
            send_text(number, "Não consegui abrir a foto. Pode mandar de novo?")

    elif message_type in TIPOS_SEM_SUPORTE:
        send_text(number, "Ainda não consigo entender esse tipo de mensagem. Me manda uma foto da praga na planta de milho que eu te ajudo. 🌽")