import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext

from parser import parse_tickets

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHECK_INTERVAL = 300  # 5 минут

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Используем глобальный словарь для хранения активных проверок
active_checks = {}

# ---------- команды ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "Я помогу отследить билеты.\n\n"
        "📌 Пример команды:\n"
        "/find 2026-01-14 874Щ\n"
        "Формат: /find <дата> <номер_поезда>"
    )

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат.\n"
            "Используй:\n/find 2026-01-14 874Щ"
        )
        return

    date, train_number = context.args
    chat_id = update.effective_chat.id
    
    # Сохраняем в контексте пользователя
    if 'active_checks' not in context.bot_data:
        context.bot_data['active_checks'] = {}
    
    context.bot_data['active_checks'][chat_id] = {"date": date, "train": train_number}
    active_checks[chat_id] = {"date": date, "train": train_number}

    # Сразу делаем первую проверку
    prices, info = parse_tickets(date, train_number)
    if prices:
        text = (
            f"🎉 БИЛЕТЫ УЖЕ ЕСТЬ!\n\n"
            f"📅 {date}\n"
            f"🚆 Поезд {train_number}\n"
            f"💺 Цены: {', '.join(prices)}\n\n"
            f"🔗 {info}"
        )
        await update.message.reply_text(text)
        if chat_id in active_checks:
            del active_checks[chat_id]
    else:
        await update.message.reply_text(
            f"🔍 Начал поиск билетов\n📅 Дата: {date}\n🚆 Поезд: {train_number}\n"
            f"Проверяю каждые {CHECK_INTERVAL // 60} минут.\n"
            f"Как только появятся билеты - сразу сообщу!\n\n"
            f"Чтобы остановить поиск, отправьте /stop"
        )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_checks:
        del active_checks[chat_id]
        await update.message.reply_text("✅ Поиск остановлен")
    else:
        await update.message.reply_text("🔍 У вас нет активных поисков")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_checks:
        data = active_checks[chat_id]
        await update.message.reply_text(
            f"📊 Статус поиска:\n"
            f"📅 Дата: {data['date']}\n"
            f"🚆 Поезд: {data['train']}\n"
            f"⏰ Следующая проверка: через {CHECK_INTERVAL // 60} минут"
        )
    else:
        await update.message.reply_text("🔍 Нет активных поисков")

# ---------- фоновая проверка ----------

async def background_checker(app: Application):
    """Фоновая проверка билетов"""
    logger.info("Фоновая проверка запущена")
    while True:
        try:
            # Создаем копию словаря, чтобы избежать ошибок при изменении
            checks_to_process = active_checks.copy()
            
            if checks_to_process:
                logger.info(f"Проверяю {len(checks_to_process)} запросов...")
                
                for chat_id, data in checks_to_process.items():
                    try:
                        prices, info = parse_tickets(data["date"], data["train"])
                        if prices:
                            text = (
                                f"🎉 БИЛЕТЫ НАЙДЕНЫ!\n\n"
                                f"📅 {data['date']}\n"
                                f"🚆 Поезд {data['train']}\n"
                                f"💺 Цены: {', '.join(prices)}\n\n"
                                f"🔗 {info}"
                            )
                            await app.bot.send_message(chat_id=chat_id, text=text)
                            
                            # Удаляем из активных проверок
                            if chat_id in active_checks:
                                del active_checks[chat_id]
                                
                    except Exception as e:
                        logger.error(f"Ошибка при проверке для {chat_id}: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Ошибка в фоновой проверке: {e}")
            await asyncio.sleep(60)  # Ждем минуту перед повторной попыткой

# ---------- запуск ----------

async def main():
    if not TOKEN:
        raise RuntimeError("❌ TELEGRAM_TOKEN не задан")

    # Создаем приложение с JobQueue
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))

    # Запускаем фоновую задачу
    asyncio.create_task(background_checker(app))

    logger.info("✅ Бот запущен и ждёт билеты")
    
    # Запускаем бота
    await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())
