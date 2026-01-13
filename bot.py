import os
from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from parser import parse_tickets  # твой парсер билетов

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHECK_INTERVAL = 300  # 5 минут

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚆 Бот поиска билетов\n\n"
        "Команды:\n"
        "/find ДАТА НОМЕР_ПОЕЗДА — начать мониторинг\n"
        "/stop — остановить мониторинг\n\n"
        "Пример:\n"
        "/find 2025-10-18 876Б"
    )

# ---------- задача проверки ----------
async def check_tickets_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    date = job.data["date"]
    train_number = job.data["train_number"]

    prices, info = parse_tickets(date, train_number)

    if prices:
        text = (
            f"🚆 Поезд {train_number}\n"
            f"📅 Дата: {date}\n"
            f"💺 Билеты появились!\n\n"
        )
        for p in prices:
            text += f"💰 {p} BYN\n"
        text += f"\n🔗 {info}"

        await context.bot.send_message(chat_id=chat_id, text=text)

        # ⛔ Останавливаем задачу после нахождения билетов
        job.schedule_removal()

# ---------- /find ----------
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❗ Используй: /find 2025-10-18 876Б")
        return

    date, train_number = context.args
    chat_id = update.effective_chat.id

    # Удаляем старую задачу, если была
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()

    # Создаём периодическую задачу
    context.job_queue.run_repeating(
        check_tickets_job,
        interval=CHECK_INTERVAL,
        first=1,
        chat_id=chat_id,
        name=str(chat_id),
        data={
            "date": date,
            "train_number": train_number,
        },
    )

    await update.message.reply_text(
        f"🔄 Начал поиск билетов\n"
        f"🚆 Поезд: {train_number}\n"
        f"📅 Дата: {date}\n"
        f"⏱ Проверка каждые 5 минут"
    )

# ---------- /stop ----------
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if not jobs:
        await update.message.reply_text("ℹ️ Активных проверок нет.")
        return

    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("⛔ Поиск билетов остановлен.")

# ---------- main ----------
def main():
    # --- Очистка старых обновлений и webhook, чтобы не было конфликта ---
    bot = Bot(token=TOKEN)
    bot.delete_webhook(drop_pending_updates=True)

    # --- Создание приложения ---
    app = ApplicationBuilder().token(TOKEN).build()

    # --- Хэндлеры команд ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("stop", stop))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
