import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Deque
from collections import deque
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import aiohttp
import asyncpg
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_SERVER_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
MESSAGES_LIMIT = 5

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None

# Кэш сообщений по chat_id
message_cache: Dict[int, Deque[Dict]] = {}

@dataclass
class Database:
    
    @staticmethod
    async def connect():
        global db_pool
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        print("✓ Подключение к БД установлено")
    
    @staticmethod
    async def save_message(chat_id: int, role: str, text: str):
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (chat_id, role, message_text) VALUES ($1, $2, $3)",
                chat_id, role, text
            )
    
    @staticmethod
    async def get_recent_messages(chat_id: int, limit: int = 5) -> List[Dict]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role, message_text, created_at FROM messages "
                "WHERE chat_id = $1 ORDER BY created_at LIMIT $2",
                chat_id, limit
            )
            
            messages = []
            for row in rows:
                messages.append({
                    "text": row["message_text"],
                    "author": row["role"],
                    "date": row["created_at"].isoformat()
                })
            return messages

def update_cache(chat_id: int, role: str, text: str):
    if chat_id not in message_cache:
        message_cache[chat_id] = deque(maxlen=MESSAGES_LIMIT)
    
    message_cache[chat_id].append({
        "text": text,
        "author": role,
        "date": datetime.now().isoformat()
    })

async def send_to_api(messages: List[Dict]) -> str:
    if not API_URL:
        return "Сервис временно недоступен"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL,
                json={"messages": messages},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", "Ответ получен")
                else:
                    return f"Ошибка сервера: {response.status}"
    except Exception as e:
        print(f"Ошибка API: {e}")
        return "Сервис временно недоступен"

async def handle_message(message: Message):
    chat_id = message.chat.id
    user_text = message.text or message.caption or ""
    
    await Database.save_message(chat_id, "user", user_text)
    update_cache(chat_id, "user", user_text)
    
    await bot.send_chat_action(chat_id=chat_id, action="typing")
    
    if chat_id in message_cache:
        recent_messages = list(message_cache[chat_id])
    else:
        recent_messages = await Database.get_recent_messages(chat_id, MESSAGES_LIMIT)
    
    bot_response = await send_to_api(recent_messages)
    
    await Database.save_message(chat_id, "bot", bot_response)
    update_cache(chat_id, "bot", bot_response)
    
    await message.answer(bot_response)

async def start_command(message: Message):
    await message.answer(
        "Привет! Я бот для рекомендаций мест отдыха.\n"
        "Просто напишите, что вы ищете!"
    )

async def load_cache():
    async with db_pool.acquire() as conn:
        # Прогрев кэша
        rows = await conn.fetch(
            "SELECT DISTINCT chat_id FROM messages WHERE created_at > current_timestamp - interval '1 hour' LIMIT 100;"
        )
        
        for row in rows:
            chat_id = row["chat_id"]
            messages = await Database.get_recent_messages(chat_id, MESSAGES_LIMIT)
            if messages:
                message_cache[chat_id] = deque(messages, maxlen=MESSAGES_LIMIT)
        
        print(f"✓ Загружен кэш для {len(message_cache)} чатов")

async def main():
    await Database.connect()
    
    await load_cache()
    
    dp.message.register(start_command, Command("start"))
    dp.message.register(handle_message)
    
    print("✓ Бот запущен")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен в .env файле")
        exit(1)
    
    asyncio.run(main())