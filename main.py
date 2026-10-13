from fastapi import FastAPI, Request, BackgroundTasks

from handlers import check_event, process_message

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

    return {"status": status}