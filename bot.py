import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from parser import parse_tickets
import asyncio

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHECK_INTERVAL = 300  # 5 минут
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

    await update.message.reply_text(
        f"🔍 Начал поиск билетов\n📅 Дата: {date}\n🚆 Поезд: {train_number}\nПроверяю каждые 5 минут."
    )

# ---------- фоновая проверка ----------

async def ticket_checker(app: Application):
    while True:
        for chat_id, data in list(active_checks.items()):
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
                del active_checks[chat_id]
        await asyncio.sleep(CHECK_INTERVAL)

# ---------- запуск ----------

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("❌ TELEGRAM_TOKEN не задан")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))

    # фоновая задача
    app.create_task(ticket_checker(app))

    print("✅ Бот запущен и ждёт билеты")
    # 🚫 Никакого asyncio.run()!
    app.run_polling(drop_pending_updates=True)
