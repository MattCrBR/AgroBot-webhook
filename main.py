import logging

from fastapi import FastAPI, Request, BackgroundTasks

from config import LOG_LEVEL
from handlers import check_event, process_message

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()


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

    status = check_event(data)

    if status == "received":
        background_tasks.add_task(process_message, key, message, message_type)
    else:
        logger.debug("evento descartado: %s", status)

    return {"status": status}