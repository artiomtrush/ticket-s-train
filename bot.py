import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from parser import parse_tickets  # импортируем функцию

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚆 Бот поиска билетов\n\n"
        "Команда:\n"
        "/find ДАТА НОМЕР_ПОЕЗДА\n"
        "Пример:\n"
        "/find 2025-10-18 876Б"
    )

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❗ Используй: /find 2025-10-18 876Б")
        return

    date, train_number = context.args
    await update.message.reply_text("🔍 Ищу билеты...")

    prices, info = parse_tickets(date, train_number)

    if not prices and info:
        await update.message.reply_text(f"❌ {info}")
        return

    text = f"🚆 Поезд {train_number}\n📅 Дата: {date}\n💺 Билеты:\n"
    for p in prices:
        text += f"💰 {p} BYN\n"
    text += f"\n🔗 {info}"

    await update.message.reply_text(text)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.run_polling()

if __name__ == "__main__":
    main()
