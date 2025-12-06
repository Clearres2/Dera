import os
import httpx
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
import os
from supabase import create_client
from datetime import datetime, timezone, timedelta
from fastapi.middleware.cors import CORSMiddleware



TOKEN = os.getenv('TOKEN')
VERCEL_URL = os.getenv('VERCEL_URL')
TOKEN_DEEP_SEEK = os.getenv('TOKEN_DEEP_SEEK')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

active_users = set()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CHAT_ADMIN = "5108832503"


if not TOKEN:
    raise ValueError("Bot token is not set in environment variables")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=TOKEN_DEEP_SEEK,
)

MAX_MESSAGE_LENGTH = 4096 

def split_text(text, max_length=MAX_MESSAGE_LENGTH):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def get_total_users_id():
    usersID = []
    all_users_id = supabase.table("users").select("user_id").execute()
    for row in all_users_id.data:
        usersID.append(str(row["user_id"]))
    return usersID

async def broadcast_to_users(listToCheckId, txt):
    for row in listToCheckId:
        await tel_send_message_not_button(int(row), txt)




async def generate_response(text: str):
    try:
        completion = await client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[{"role": "user", "content": text}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("Ошибка при генерации ответа:", e)
        return "Произошла ошибка при обработке вашего запроса."

def parse_message(message):
    if "message" not in message or "text" not in message["message"]:
        return None, None  

    chat_id = message["message"]["chat"]["id"]
    txt = message["message"]["text"]
    return chat_id, txt


def add_user_to_state(chat_id: int):
    try:
        res = supabase.table("users").select("user_id").eq("user_id", chat_id).execute()
        if not res.data: 
            supabase.table("users").insert({"user_id": chat_id}).execute()
    except Exception as e:
        print("Supabase error")


def false_user_to_active(chat_id: int):
    try:
        supabase.table("users").update({"active_users": False}).eq("user_id", chat_id).execute()
    except Exception as e:
        print("Supabase error")

def true_user_to_active(chat_id: int):
    try:
        supabase.table("users").update({"active_users": True}).eq("user_id", chat_id).execute()
    except Exception as e:
        print("Supabase error")


def get_true_users():
    try:
        res = supabase.table("users").select("*", count="exact").eq("active_users", True).execute()
        return res.count or 0
    except:
        return 0


def get_total_users():
    try:
        res = supabase.table("users").select("*", count="exact").execute()
        return res.count or 0
    except:
        return 0


@app.post('/setwebhook')
async def setwebhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    payload = {
        "url": "https://dera-flame.vercel.app/webhook",
        "allowed_updates": ["message", "callback_query", "my_chat_member"]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code == 200:
        return JSONResponse(content={"status": "Webhook set with my_chat_member support"}, status_code=200)
    else:
        return JSONResponse(content={"error": response.text}, status_code=response.status_code)
        
#@app.post('/setwebhook')
#async def setwebhook():
#    webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://dera-flame.vercel.app/webhook"
#   async with httpx.AsyncClient() as client:
#        response = await client.get(webhook_url)
        
#    if response.status_code == 200:
        return JSONResponse(content={"status": "Webhook successfully set"}, status_code=200)
#   else:
#     return JSONResponse(content={"error": f"Error setting webhook: {response.text}"}, status_code=response.status_code)

@app.on_event("startup")
async def startup_event():
    await setwebhook()


async def tel_send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "Открыть Муз Чат", "web_app": {"url": "https://clearres2.github.io/bababab/"}},
                ]
            ]
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        print("Ошибка отправки сообщения:", response.text)

    return response


async def tel_send_message_not_button(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code == 403:
        false_user_to_active(chat_id)

    if response.status_code != 200:
        print("Ошибка отправки сообщения:", response.text)

    return response




async def tel_send_message_not_markup(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        print("Ошибка отправки сообщения:", response.text)

    return response

user_states = {}

async def process_user_request(chat_id, txt):
    await tel_send_message_not_markup(chat_id, '🏈 Идет обработка...')
    response_text = await generate_response(txt)
    for part in split_text(response_text):
        await tel_send_message_not_markup(chat_id, part)
    user_states[chat_id] = None 

def count_users_to_time():
    timeToAnd = datetime.now(timezone.utc) - timedelta(seconds=45)
    res = supabase.table("users").select("user_id", count="exact").gte("last_active_webapp", timeToAnd).execute()
    return res.count or 0
    
@app.post('/ping_users')
async def requestActiveUsers(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    print("Начало")

    try:
        if (user_id):
            supabase.table("users").upsert({"user_id": int(user_id), "last_active_webapp": datetime.now(timezone.utc).isoformat()}).execute()
        return {"ok": True}
    except Exception as e:
        print(f"❌ ОШИБКА в /ping_users: {e}")
        return {"ok": False}
    


@app.post('/webhook')
async def webhook(request: Request, background_tasks: BackgroundTasks):
    msg = await request.json()
    print("Получен вебхук:", msg)

    if "my_chat_member" in msg:
        chat = msg["my_chat_member"]["chat"]
        user_id = chat["id"]
        new_status = msg["my_chat_member"]["new_chat_member"]["status"]
        is_active = new_status not in ("left", "kicked")

        if is_active:
            true_user_to_active(user_id)
        else:
            false_user_to_active(user_id)
    

    if "callback_query" in msg:
        callback = msg["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        if chat_id is not None:
            active_users.add(chat_id)
        callback_data = callback["data"]

        if callback_data == "deepSeek":
            await tel_send_message_not_markup(chat_id, "Вы выбрали диалог с ИИ. Как я могу помочь вам?")
            user_states[chat_id] = 'awaiting_response'
            return JSONResponse(content={"status": "message_sent"}, status_code=200)

        return JSONResponse(content={"status": "deleted"}, status_code=200)

    chat_id, txt = parse_message(msg)
    if chat_id is None or txt is None:
        return JSONResponse(content={"status": "ignored"}, status_code=200)

    if chat_id in user_states and user_states[chat_id] == "awaiting_response":
        background_tasks.add_task(process_user_request, chat_id, txt)
    
    elif chat_id in user_states and user_states[chat_id] == "send_all_users":
        listUsersId = get_total_users_id()
        await broadcast_to_users(listUsersId, txt)
        

    elif txt.lower() == "/start":
        true_user_to_active(chat_id)
        active_users.add(chat_id)
        add_user_to_state(chat_id)
        
        await tel_send_message(chat_id, 
            "🎵 Добро пожаловать в наш уникальный музыкальный мир! "
            "Здесь вас ждут любимые треки и вдохновляющие клипы. 🎶\n\n"
            "✨ Мечтаете о персональной композиции? "
            "Закажите эксклюзивное музыкальное произведение, созданное специально для вас! 🎼\n\n"
            "🤖 Используйте возможности искусственного интеллекта для творческих запросов и новых идей. 🚀"
        )
        
    elif txt.lower() == "/admin":
        active_users.add(chat_id)
        total = get_total_users()
        await tel_send_message_not_button(chat_id, 
            "🎵 Добро пожаловать в статистику!\n\n"
            f"Активных пользователей: {count_users_to_time()}\n"
            f"Подписаных пользователей: {get_true_users()}\n"
            f"👥 Всего пользователей: {total}"
        )

    elif txt.lower() == "/send_to_sub":
       if chat_id == CHAT_ADMIN:   
          user_states[chat_id] = "send_all_users"
          await tel_send_message_not_markup(chat_id, "📩 Пришлите текст рассылки для всех пользователей:")
       else:
           await tel_send_message_not_button(chat_id, "Это только администраторам!")






    return JSONResponse(content={"status": "ok"}, status_code=200)

@app.get("/")
async def index():
    return "<h1>Telegram Bot Webhook is Running</h1>"

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)), log_level="info")
