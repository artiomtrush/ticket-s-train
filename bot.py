import requests
import os
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

TOKEN = os.getenv("TELEGRAM_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def parse_tickets(date, train_number):
    url = (
        "https://pass.rw.by/ru/route/?"
        "from=%D0%9C%D0%B8%D0%BD%D1%81%D0%BA&from_exp=2100000&"
        "to=%D0%9C%D0%BE%D0%B7%D1%8B%D1%80%D1%8C&to_exp=2100254&"
        f"date={date}&type=1"
    )

    response = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    train = soup.find("div", class_="sch-table__row", attrs={"data-train-number": train_number})
    if not train:
        return "❌ Поезд не найден"

    ticket_items = train.find_all("div", class_="sch-table__t-item")
    if not ticket_items:
        return "❌ Мест нет"

    result = []
    for item in ticket_items:
        name = item.find("div", class_="sch-table__t-name").text.strip()
        prices = item.find_all("span", class_="ticket-cost")
        for price in prices:
            result.append(f"• {name}: {price.text.strip()} BYN")

    return "💺 Найдены билеты:\n" + "\n".join(result)

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

    try:
        result = parse_tickets(date, train_number)
    except Exception as e:
        result = f"⚠️ Ошибка: {e}"

    await update.message.reply_text(result)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.run_polling()

if __name__ == "__main__":
    main()
