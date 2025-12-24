import requests
import os

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def main(context):
    if not hasattr(context, "user") or not context.user:
        return context.res.json({"error": "Unauthorized"}, status_code=401)
    # 🔐 Auth check
    if not context.user:
        return context.res.json(
            {"error": "Unauthorized"},
            status_code=401
        )

    if context.req.method != "POST":
        return context.res.json(
            {"error": "Method not allowed"},
            status_code=405
        )

    body = context.req.body_json
    user_message = body.get("message", "").strip()

    if not user_message:
        return context.res.json(
            {"error": "Empty message"},
            status_code=400
        )

    # 🧠 Call OpenRouter
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI support assistant."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        },
        timeout=30
    )

    data = response.json()

    ai_reply = data["choices"][0]["message"]["content"]

    context.log("AI reply:")
    context.log(ai_reply)

    return context.res.json({
        "reply": ai_reply
    })
