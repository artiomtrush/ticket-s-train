import os
import asyncio
import time
import requests
from bs4 import BeautifulSoup
from telegram.ext import Application

# ====== НАСТРОЙКИ ======
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CHECK_INTERVAL = 300  # 5 минут

TRIP_DATE = "2025-10-18"
TRAIN_NUMBER = "874Щ"

URL = (
    "https://pass.rw.by/ru/route/?"
    "from=%D0%9C%D0%B8%D0%BD%D1%81%D0%BA&from_exp=2100000&from_esr=140210&"
    "to=%D0%9C%D0%BE%D0%B7%D1%8B%D1%80%D1%8C&to_exp=2100254&to_esr=151605&"
    f"date={TRIP_DATE}&type=1"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ======================

def check_train():
    response = requests.get(URL, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    train = soup.find("div", class_="sch-table__row", attrs={"data-train-number": TRAIN_NUMBER})

    if not train:
        print("Поезд не найден")
        return None

    tickets = train.find("div", class_="sch-table__tickets")
    no_tickets = train.find("div", class_="sch-table__no-info")

    if tickets and not no_tickets:
        price_el = tickets.find("span", class_="ticket-cost")
        price = price_el.text.strip() if price_el else "неизвестно"

        return (
            f"🚆 Минск → Мозырь\n"
            f"💺 Билеты появились!\n"
            f"Цена: {price} BYN\n\n"
            f"{URL}"
        )

    print(f"[{time.strftime('%H:%M:%S')}] Билетов нет")
    return None


async def main():
    if not TOKEN:
        raise RuntimeError("❌ TELEGRAM_TOKEN не задан")

    app = Application.builder().token(TOKEN).build()

    print("✅ Бот запущен и ждёт билеты")

    while True:
        try:
            message = check_train()
            if message:
                await app.bot.send_message(chat_id=CHAT_ID, text=message)
        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
