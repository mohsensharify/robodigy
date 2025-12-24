import requests
import os

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def main(context):
    # بررسی امن Auth
    if not hasattr(context, "user") or not context.user:
        return context.res.status(401).json({"error": "Unauthorized"})

    user_id = context.user["$id"]

    if context.req.method != "POST":
        return context.res.status(405).json({"error": "Method not allowed"})

    body = context.req.body_json
    user_message = body.get("message", "").strip()

    if not user_message:
        return context.res.status(400).json({"error": "Empty message"})

    # درخواست به OpenRouter
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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

    data = response.json()
    ai_reply = data["choices"][0]["message"]["content"]

    # لاگ برای دیباگ
    context.log(ai_reply)

    return context.res.json({
        "userId": user_id,
        "reply": ai_reply
    })
