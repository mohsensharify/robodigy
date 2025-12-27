import os
import json
import requests
from datetime import datetime

from appwrite.client import Client
from appwrite.services.tables import TablesDB


def main(context):

    # 🔐 Auth check (مهم)
    if not hasattr(context, "user") or context.user is None:
        context.log("Unauthorized: context.user is null")
        return context.res.text(
            json.dumps({"error": "Unauthorized"}),
            401,
            {"content-type": "application/json"}
        )

    user_id = context.user.get("$id")
    if not user_id:
        context.log("Unauthorized: user_id missing")
        return context.res.text(
            json.dumps({"error": "Unauthorized"}),
            401,
            {"content-type": "application/json"}
        )

    # 📥 Request body
    body = context.req.body_json or {}
    user_message = body.get("message", "").strip()

    if not user_message:
        return context.res.text(
            json.dumps({"error": "Empty message"}),
            400,
            {"content-type": "application/json"}
        )

    # 🔌 Appwrite Client
    client = Client()
    client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
    client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    client.set_key(os.environ["APPWRITE_API_KEY"])

    tables = TablesDB(client)

    # 💾 ذخیره پیام کاربر
    tables.create_row(
        database_id=os.environ["DATABASE_ID"],
        table_id=os.environ["COLLECTION_ID"],
        row_id="unique()",
        data={
            "userId": user_id,
            "role": "user",
            "content": user_message
        }
    )

    # 🤖 OpenRouter call
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

    if response.status_code != 200:
        context.log(response.text)
        return context.res.text(
            json.dumps({"error": "AI service failed"}),
            500,
            {"content-type": "application/json"}
        )

    ai_reply = response.json()["choices"][0]["message"]["content"]

    # 💾 ذخیره پاسخ AI
    tables.create_row(
        database_id=os.environ["DATABASE_ID"],
        table_id=os.environ["TABLE_ID"],
        row_id="unique()",
        data={
            "userId": user_id,
            "role": "assistant",
            "content": ai_reply
        }
    )

    # 📤 Response
    return context.res.text(
        json.dumps({"reply": ai_reply}),
        200,
        {"content-type": "application/json"}
    )
