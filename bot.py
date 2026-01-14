import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext
from parser import parse_tickets

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHECK_INTERVAL = 300  # 5 минут

# Используем глобальный словарь для хранения активных проверок
# В production лучше использовать базу данных
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
        del active_checks[chat_id]
    else:
        await update.message.reply_text(
            f"🔍 Начал поиск билетов\n📅 Дата: {date}\n🚆 Поезд: {train_number}\n"
            f"Проверяю каждые {CHECK_INTERVAL // 60} минут.\n"
            f"Как только появятся билеты - сразу сообщу!"
        )

# ---------- фоновая проверка ----------

async def check_tickets(context: CallbackContext):
    """Проверка билетов по расписанию"""
    if not active_checks:
        return
    
    for chat_id, data in list(active_checks.items()):
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
                await context.bot.send_message(chat_id=chat_id, text=text)
                del active_checks[chat_id]
        except Exception as e:
            print(f"Ошибка при проверке билетов для {chat_id}: {e}")
            # Можно добавить отправку сообщения об ошибке пользователю

# ---------- запуск ----------

def main():
    if not TOKEN:
        raise RuntimeError("❌ TELEGRAM_TOKEN не задан")

    # Создаем приложение
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))

    # Добавляем job для периодической проверки
    # Используем run_repeating для повторяющейся задачи
    app.job_queue.run_repeating(
        check_tickets,
        interval=CHECK_INTERVAL,
        first=10  # Первая проверка через 10 секунд после запуска
    )

    print("✅ Бот запущен и ждёт билеты")
    
    # Запускаем бота
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
