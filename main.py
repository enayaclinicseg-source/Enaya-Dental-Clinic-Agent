import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

# جلب المتغيرات السرية من إعدادات Render
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_custom_secret_123")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# إعداد نموذج Gemini
ai_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
أنت مساعد خدمة عملاء ذكي ومحترف لصفحة فيسبوك.
- أجب عن استفسارات المتابعين بأسلوب ودود ومهذب وموجز.
- شجع العميل على التواصل عبر رسائل الصفحة الخاصة (Inbox) لمعرفة التفاصيل أو الحجز.
- لا تبتكر تفاصيل أسعار إذا لم تكن محددة بدقة في سياق السؤال.
- اجعل الرد من سطر إلى سطرين كحد أقصى.
"""

def generate_ai_reply(comment_text):
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=comment_text,
            config={'system_instruction': SYSTEM_INSTRUCTION}
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "أهلاً بك! نسعد بتواصلك معنا، يرجى مراسلتنا في رسائل الصفحة لمزيد من التفاصيل."

def reply_to_facebook_comment(comment_id, reply_message):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
    payload = {
        "message": reply_message,
        "access_token": PAGE_ACCESS_TOKEN
    }
    requests.post(url, data=payload)

@app.route("/", methods=["GET"])
def health_check():
    return "AI Agent is running!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification token mismatch", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook_event():
    data = request.get_json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                item = value.get("item")
                verb = value.get("verb")

                if item == "comment" and verb == "add":
                    sender_id = value.get("from", {}).get("id")
                    if sender_id == PAGE_ID:
                        continue  # تجاهل التعليقات الصادرة من صفحتك

                    comment_id = value.get("comment_id")
                    comment_text = value.get("message", "")

                    if comment_text:
                        reply = generate_ai_reply(comment_text)
                        reply_to_facebook_comment(comment_id, reply)

        return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
