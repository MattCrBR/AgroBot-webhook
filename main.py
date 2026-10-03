from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "AgroBot webhook online"}

@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    print("=== Payload recebido ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return {"status": "received"}