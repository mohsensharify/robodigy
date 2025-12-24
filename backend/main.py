from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI Support Service")

# مدل ورودی چت
class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {"status": "ok", "message": "API is running"}


@app.post("/chat")
def chat(req: ChatRequest):
    return {
        "reply": f"پیام شما دریافت شد: {req.message}"
    }