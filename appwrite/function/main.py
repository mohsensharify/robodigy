import os
import json
import requests
from datetime import datetime
from appwrite.client import Client
from appwrite.services.databases import Databases

def main(context):

    # 🔐 Auth
    if not hasattr(context, "user") or not context.user:
        context.log("no user")
        return context.res.text(
            json.dumps({"error": "Unauthorized"}),
            401,
            {"content-type": "application/json"}
        )

    user_id = context.user["$id"]
    context.log("user_id")
    # 📥 Body
    body = context.req.body_json
    user_message = body.get("message", "").strip()
    
    if not user_message:
        return context.res.text(
            json.dumps({"error": "Empty message"}),
            400,
            {"content-type": "application/json"}
        )
    context.log("msg")
    # 🔌 Appwrite DB
    client = Client()
    client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
    client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    client.set_key(os.environ["APPWRITE_API_KEY"])

    db = Databases(client)
    context.log("db")
    # 💾 ذخیره پیام کاربر
    db.create_document(
        database_id=os.environ["DATABASE_ID"],
        collection_id=os.environ["COLLECTION_ID"],
        document_id="unique()",
        data={
            "userId": user_id,
            "role": "user",
            "content": user_message,
            "createdAt": datetime.utcnow().isoformat()
        }
    )
    context.log("doc")
    # 🤖 OpenRouter
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful AI support assistant."},
                {"role": "user", "content": user_message}
            ]
        },
        timeout=30
    )
    context.log("openrouter")
    ai_reply = response.json()["choices"][0]["message"]["content"]
    context.log(ai_reply)
    # 💾 ذخیره پاسخ AI
    db.create_document(
        database_id=os.environ["DATABASE_ID"],
        collection_id=os.environ["COLLECTION_ID"],
        document_id="unique()",
        data={
            "userId": user_id,
            "role": "assistant",
            "content": ai_reply,
            "createdAt": datetime.utcnow().isoformat()
        }
    )

    # 📤 Response نهایی
    return context.res.text(
        json.dumps({
            "reply": ai_reply
        }),
        200,
        {"content-type": "application/json"}
    )
