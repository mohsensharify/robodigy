import os
import json
import requests
from datetime import datetime

from appwrite.client import Client
from appwrite.services.tables_db import TablesDB


def main(context):

    # 📥 Body
    body = context.req.body_json or {}
    user_message = body.get("message", "").strip()
    user_id = body.get("userId", "guest").strip()
    context.log("user data:")

    if not user_message:
        return context.res.text(
            json.dumps({"error": "Empty message"}),
            400,
            {"content-type": "application/json"}
        )
        
    context.log(user_id)
    user_message = body.get("message", "").strip()

    # 🔌 Appwrite Client
    client = Client()
    client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
    client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    client.set_key(os.environ["APPWRITE_API_KEY"])

    tables = TablesDB(client)
    context.log("db")

    # 💾 ذخیره پیام کاربر
    tables.create_row(
        database_id=os.environ["DATABASE_ID"],
        table_id=os.environ["TABLE_ID"],
        #row_id = "unique()"
        data={
            "userId": user_id,
            "role": "user",
            "content": user_message,
            "createdAt": datetime.utcnow().isoformat()
        }
    )
    context.log("row")

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

    response.raise_for_status()
    ai_reply = response.json()["choices"][0]["message"]["content"]
    context.log(ai_reply)

    # 💾 ذخیره پاسخ AI
    tables.create_row(
        database_id=os.environ["DATABASE_ID"],
        table_id=os.environ["TABLE_ID"],
        data={
            "userId": user_id,
            "role": "assistant",
            "content": ai_reply,
            "createdAt": datetime.utcnow().isoformat()
        }
    )

    # 📤 Response
    return context.res.text(
        json.dumps({"reply": ai_reply}, ensure_ascii=False),
        200,
        {"content-type": "application/json"}
    )
