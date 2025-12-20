import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
from loguru import logger
import os
import signal

from dotenv import load_dotenv

load_dotenv()

KEYWORDS: List[str] = list(map(str, os.getenv("KEYWORDS").split(",")))
SOURCE_CHANNELS: List[str] = list(map(str, os.getenv("SOURCE_CHANNELS").split(",")))
PARSE_INTERVAL_MINUTES: int = int(os.getenv("PARSE_INTERVAL_MINUTES"))
MAX_MESSAGES_PER_CHANNEL: int = int(os.getenv("MAX_MESSAGES_PER_CHANNEL"))

SERVER_URL: str = os.getenv("SERVER_URL")

TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID"))
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH")

class TelegramParserBot:
    def __init__(self):
        # Telegram Client для парсинга
        self.client = TelegramClient(
            'parser_session_v2',
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH
        )
        
        self.is_parsing = False
        self.last_parsed = {}
        self.processed_messages = set()
        self.is_running = True
        
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        logger.add(f"{log_dir}/parser_{{time:YYYY-MM-DD}}.log", rotation="1 day", retention="7 days")
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        logger.info(f"Получен сигнал {signum}, завершаю работу...")
        self.is_running = False
        
    async def start_parser(self) -> None:
        await self.client.start()
        logger.info("Telegram клиент запущен для парсинга")
        
        await self.parse_all_channels()
        
        asyncio.create_task(self.periodic_parser())
        
    async def periodic_parser(self):
        logger.info(f"Периодический парсинг запущен каждые {PARSE_INTERVAL_MINUTES} минут")
        
        while self.is_running:
            try:
                await asyncio.sleep(PARSE_INTERVAL_MINUTES * 60)
                
                if not self.is_running:
                    break
                    
                logger.info("Запуск планового парсинга...")
                await self.parse_all_channels()
                
            except asyncio.CancelledError:
                logger.info("Периодический парсинг отменен")
                break
            except Exception as e:
                logger.error(f"Ошибка в периодическом парсинге: {e}")
                
    async def parse_all_channels(self) -> None:
        if self.is_parsing:
            logger.warning("Парсинг уже выполняется, пропускаю")
            return
            
        self.is_parsing = True
        try:
            for channel in SOURCE_CHANNELS:
                try:
                    await self.parse_channel(channel)
                except Exception as e:
                    logger.error(f"Ошибка парсинга канала {channel}: {e}")
                    
        finally:
            self.is_parsing = False
            
    async def parse_channel(self, channel_identifier: str) -> None:
        try:
            logger.info(f"Начинаю парсинг канала: {channel_identifier}")
            
            entity = await self.client.get_entity(channel_identifier)
            logger.info(f"Канал найден: {entity.title}")
            
            since_date = datetime.now() - timedelta(hours=24)
            
            messages_data = []
            message_count = 0
            keyword_matches = 0
            
            logger.info(f"Загружаю сообщения с {since_date}...")
            
            async for message in self.client.iter_messages(
                entity,
                limit=MAX_MESSAGES_PER_CHANNEL,
                offset_date=since_date,
                reverse=True
            ):
                if message.id in self.processed_messages:
                    continue
                    
                if self.contains_keywords(message):
                    keyword_matches += 1
                    message_data = await self.process_message(message, entity)
                    if message_data:
                        messages_data.append(message_data)
                        self.processed_messages.add(message.id)
                        message_count += 1
                        
                        if len(messages_data) >= 10:
                            await self.send_to_server(messages_data)
                            messages_data = []
                            
            if messages_data:
                await self.send_to_server(messages_data)
                
            logger.info(f"Канал {channel_identifier}: проверено сообщений, найдено по ключевым словам: {keyword_matches}, обработано: {message_count}")
            self.last_parsed[channel_identifier] = datetime.now()
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге {channel_identifier}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def contains_keywords(self, message: Message) -> bool:
        if not message.text:
            return False
            
        text_lower = message.text.lower()
        for keyword in KEYWORDS:
            if keyword.lower() in text_lower:
                logger.debug(f"Найдено ключевое слово '{keyword}' в сообщении: {message.text[:50]}...")
                return True
        return False
        
    async def process_message(self, message: Message, channel: Channel) -> Dict[str, Any]:
        try:
            message_data = {
                'id': f"{channel.id}_{message.id}",
                'channel_id': channel.id,
                'channel_name': channel.title,
                'channel_username': getattr(channel, 'username', None),
                'message_id': message.id,
                'text': message.text,
                'date': message.date.isoformat() if message.date else None,
                'has_media': bool(message.media),
                'url': f"https://t.me/{channel.username}/{message.id}" if hasattr(channel, 'username') else None,
                'parsed_at': datetime.now().isoformat()
            }
                
            # Извлечение локации (если есть)
            if message.geo:
                message_data['location'] = {
                    'lat': message.geo.lat,
                    'long': message.geo.long
                }
                
            return message_data
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения {message.id}: {e}")
            return None
            
    async def send_to_server(self, messages: List[Dict[str, Any]]) -> bool:
        if not SERVER_URL:
            logger.warning("SERVER_URL не указан, данные не отправлены")
            for msg in messages:
                logger.info(f"Сообщение: {msg.get('text', '')[:100]}...")
            return False
            
        try:
            headers = {
                'Content-Type': 'application/json',
            }
                
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SERVER_URL,
                    json={'messages': messages},
                    headers=headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"Успешно отправлено {len(messages)} сообщений")
                        return True
                    else:
                        logger.error(f"Ошибка сервера: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Ошибка отправки на сервер: {e}")
            return False
        
    async def run(self) -> None:
        try:
            await self.start_parser()
            
            logger.info("Парсер запущен. Для остановки нажмите Ctrl+C")
            
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал KeyboardInterrupt")
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        logger.info("Завершаю работу парсера...")
        await self.client.disconnect()
        logger.info("Парсер остановлен")

async def main():
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.error("Не установлены TELEGRAM_API_ID или TELEGRAM_API_HASH в .env файле!")
        return
        
    if not SOURCE_CHANNELS:
        logger.error("Не указаны каналы для парсинга в SOURCE_CHANNELS!")
        return
        
    parser_bot = TelegramParserBot()
    await parser_bot.run()

if __name__ == "__main__":
    asyncio.run(main())