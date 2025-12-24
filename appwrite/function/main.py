import json

def main(context):
    """
    Appwrite Function entry point
    """

    if context.req.method == "GET":
        return context.res.json({
            "status": "ok",
            "message": "Appwrite Function is running"
        })

    if context.req.method == "POST":
        body = context.req.body_json
        message = body.get("message", "")

        return context.res.json({
            "reply": f"پیام شما دریافت شد: {message}"
        })

    return context.res.json(
        {"error": "Method not allowed"},
        status_code=405
    )
