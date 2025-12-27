import os
import json
import requests
from datetime import datetime, timedelta

from appwrite.client import Client
from appwrite.services.account import Account
from appwrite.services.databases import Databases  # در نسخه‌های جدید Databases جایگزین TablesDB شده است
from appwrite.query import Query  # برای فیلتر کردن کوئری‌ها اضافه شد

def main(context):
    # ۱. دریافت داده‌ها از بدنه درخواست (Payload)
    body = context.req.body_json or {}
    user_message = body.get("message", "").strip()
    user_jwt = body.get("user_jwt")  # توکنی که از کلاینت فرستادیم

    # ۲. بررسی وجود اطلاعات لازم
    if not user_jwt or not user_message:
        return context.res.json({
            "error": "Missing user_jwt or message"
        }, 400)

    # ۳. تنظیم کلاینت برای تایید هویت کاربر (استفاده از JWT)
    auth_client = Client()
    auth_client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
    auth_client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    auth_client.set_jwt(user_jwt) # هویت کاربر را با توکن ست می‌کنیم

    try:
        # استخراج اطلاعات کاربر از طریق JWT
        account_service = Account(auth_client)
        user_info = account_service.get()
        user_id = user_info["$id"]
        context.log(f"Authenticated User ID: {user_id}")
    except Exception as e:
        context.error(f"JWT Validation failed: {str(e)}")
        return context.res.json({"error": "Unauthorized: Invalid JWT"}, 401)

    # ۴. تنظیم کلاینت اصلی با API Key (برای دسترسی کامل به دیتابیس)
    admin_client = Client()
    admin_client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
    admin_client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    admin_client.set_key(os.environ["APPWRITE_API_KEY"])

    databases = Databases(admin_client)

    try:
        RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", 60))
        MAX_MESSAGES_PER_WINDOW = int(os.environ.get("MAX_MESSAGES_PER_WINDOW", 5))
        
        now = datetime.utcnow()
        since_time = (now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)).isoformat()
        
        # کوئری برای پیدا کردن پیام‌های اخیر این کاربر
        recent_messages = databases.list_documents(
            database_id=os.environ["DATABASE_ID"],
            collection_id=os.environ["COLLECTION_ID"],
            queries=[
                Query.equal("userId", user_id),
                Query.greater_than_equal("$createdAt", since_time) # بررسی بر اساس زمان ساخت
            ]
        )

        if recent_messages['total'] >= MAX_MESSAGES_PER_WINDOW:
            context.log(f"Rate limit exceeded for user: {user_id}")
            return context.res.json({
                "reply": "شما بیش از حد مجاز پیام فرستاده‌اید. لطفا کمی صبر کنید."
            }, 429) # کد ۴۲۹ برای Too Many Requests
        
        
        # ۵. ذخیره پیام کاربر در دیتابیس
        databases.create_document(
            database_id=os.environ["DATABASE_ID"],
            collection_id=os.environ["COLLECTION_ID"],
            document_id="unique()",
            data={
                "userId": user_id,
                "role": "user",
                "content": user_message
            }
        )
        
        
        #----------------------------------
        
        # ۱. واکشی تاریخچه پیام‌ها برای Context Window (مثلاً ۵ پیام آخر)
        history_docs = databases.list_documents(
            database_id=os.environ["DATABASE_ID"],
            collection_id=os.environ["COLLECTION_ID"],
            queries=[
                Query.equal("userId", user_id),
                Query.order_desc("$createdAt"), # دریافت از جدید به قدیم
                Query.limit(5)                   # فقط ۵ پیام اخیر
            ]
        )

        # ۲. ساخت لیست پیام‌ها برای ارسال به AI
        # پیام‌ها را معکوس می‌کنیم تا ترتیب زمانی (قدیم به جدید) درست شود
        formatted_history = []
        for doc in reversed(history_docs['documents']):
            formatted_history.append({
                "role": doc['role'], 
                "content": doc['content']
            })

        # ۳. اضافه کردن پیام فعلی کاربر به انتهای تاریخچه
        # (اگر هنوز پیام فعلی را در دیتابیس ذخیره نکرده‌اید، اینجا اضافه کنید)
        messages_for_ai = [
            {"role": "system", "content": "You are a helpful AI support assistant."}
        ]
        messages_for_ai.extend(formatted_history)
        
        # اگر پیام فعلی در تاریخچه نبود (چون هنوز ذخیره نشده)، آن را دستی اضافه می‌کنیم:
        #if not any(m['content'] == user_message for m in formatted_history):
        #    messages_for_ai.append({"role": "user", "content": user_message})
        
        #----------------------------------

        # ۶. فراخوانی OpenRouter
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            },
            #json={
            #    "model": "gpt-4o-mini",
            #    "messages": [
            #        {"role": "system", "content": "You are a helpful AI support assistant."},
            #        {"role": "user", "content": user_message}
            #    ]
            #},
            json={
                "model": "gpt-4o-mini",
                "messages": messages_for_ai # ارسال کل لیست به جای تک پیام
            },
            timeout=30
        )

        if response.status_code != 200:
            context.error(f"OpenRouter Error: {response.text}")
            return context.res.json({"error": "AI service failed"}, 500)

        ai_reply = response.json()["choices"][0]["message"]["content"]

        # ۷. ذخیره پاسخ AI
        databases.create_document(
            database_id=os.environ["DATABASE_ID"],
            collection_id=os.environ["COLLECTION_ID"],
            document_id="unique()",
            data={
                "userId": user_id,
                "role": "assistant",
                "content": ai_reply
            }
        )

        # ۸. خروجی نهایی
        return context.res.json({"reply": ai_reply})

    except Exception as e:
        context.error(f"Database or Logic Error: {str(e)}")
        return context.res.json({"error": "Internal Server Error"}, 500)