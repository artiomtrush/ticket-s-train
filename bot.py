import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Токен бота
CHECK_INTERVAL = 300  # 5 минут в секундах

# ========== ХРАНИЛИЩЕ ЗАПРОСОВ ==========
# Вместо базы данных - простой словарь
# В реальном проекте лучше использовать SQLite или Redis
user_requests = {}

# ========== ПАРСЕР ==========
def parse_tickets(date: str, train_number: str):
    """
    Проверяет билеты на сайте pass.rw.by
    Возвращает: (список_цен, ссылка_на_маршрут)
    """
    # URL для маршрута Минск → Мозырь
    url = (
        "https://pass.rw.by/ru/route/?"
        "from=%D0%9C%D0%B8%D0%BD%D1%81%D0%BA&from_exp=2100000&"
        "to=%D0%9C%D0%BE%D0%B7%D1%8B%D1%80%D1%8C&to_exp=2100254&"
        f"date={date}&type=1"
    )
    
    try:
        # Делаем запрос к сайту
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем нужный поезд по номеру
        train = soup.find("div", attrs={"data-train-number": train_number})
        
        if not train:
            return [], url  # Поезд не найден
        
        # Проверяем, есть ли сообщение "нет мест"
        no_seats = train.find("div", class_="sch-table__no-info")
        if no_seats:
            return [], url  # Мест нет
        
        # Ищем цены билетов
        prices = []
        for price_element in train.select(".ticket-cost"):
            price_text = price_element.text.strip()
            if price_text and price_text != "—":  # Пропускаем пустые
                prices.append(price_text)
        
        return prices, url
        
    except requests.RequestException as e:
        print(f"Ошибка при запросе: {e}")
        return [], url
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return [], url

# ========== КОМАНДЫ БОТА ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🚆 *Поиск билетов Белорусской железной дороги*\n\n"
        "🔍 *Проверить билеты:*\n"
        "`/find 2026-01-15 874Щ`\n\n"
        "🛑 *Остановить поиск:*\n"
        "`/stop`\n\n"
        "📋 *Мои запросы:*\n"
        "`/list`",
        parse_mode="Markdown"
    )

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find"""
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ *Неверный формат!*\n"
            "✅ *Правильно:*\n"
            "`/find ГГГГ-ММ-ДД НОМЕР_ПОЕЗДА`\n\n"
            "📌 *Пример:*\n"
            "`/find 2026-01-15 874Щ`",
            parse_mode="Markdown"
        )
        return
    
    date, train_number = context.args
    chat_id = update.effective_chat.id
    
    await update.message.reply_text(f"🔍 *Ищу билеты...*\nПоезд: `{train_number}`\nДата: `{date}`", 
                                   parse_mode="Markdown")
    
    # Проверяем билеты
    prices, url = parse_tickets(date, train_number)
    
    if prices:
        # Билеты найдены
        await update.message.reply_text(
            f"🎉 *БИЛЕТЫ НАЙДЕНЫ!*\n\n"
            f"🚆 *Поезд:* {train_number}\n"
            f"📅 *Дата:* {date}\n"
            f"💰 *Цены:* {', '.join(prices)}\n\n"
            f"🔗 [Купить билеты]({url})",
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
    else:
        # Билетов нет - добавляем в отслеживание
        user_requests[chat_id] = {
            "date": date, 
            "train": train_number,
            "url": url
        }
        
        await update.message.reply_text(
            f"😔 *Билетов пока нет*\n\n"
            f"🚆 *Поезд:* {train_number}\n"
            f"📅 *Дата:* {date}\n\n"
            f"⏰ *Бот будет проверять автоматически*\n"
            f"Как только появятся билеты - сразу пришлю уведомление!\n\n"
            f"🛑 Чтобы остановить поиск: `/stop`",
            parse_mode="Markdown"
        )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stop"""
    chat_id = update.effective_chat.id
    
    if chat_id in user_requests:
        train = user_requests[chat_id]["train"]
        date = user_requests[chat_id]["date"]
        del user_requests[chat_id]
        
        await update.message.reply_text(
            f"✅ *Поиск остановлен*\n\n"
            f"🚆 Поезд: {train}\n"
            f"📅 Дата: {date}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "ℹ️ *У вас нет активных поисков*\n"
            "Начните поиск командой: `/find`",
            parse_mode="Markdown"
        )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list"""
    chat_id = update.effective_chat.id
    
    if chat_id in user_requests:
        data = user_requests[chat_id]
        await update.message.reply_text(
            f"📋 *Ваш активный поиск:*\n\n"
            f"🚆 *Поезд:* {data['train']}\n"
            f"📅 *Дата:* {data['date']}\n"
            f"🔗 [Ссылка на маршрут]({data['url']})\n\n"
            f"⏰ Проверка каждые 5 минут\n"
            f"🛑 Остановить: `/stop`",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            "📭 *Нет активных поисков*\n"
            "Начните поиск: `/find 2026-01-15 874Щ`",
            parse_mode="Markdown"
        )

# ========== ФОНОВАЯ ПРОВЕРКА ==========
async def check_tickets_periodically(application):
    """Фоновая проверка билетов"""
    print("🔄 Фоновая проверка запущена")
    
    while True:
        try:
            # Создаем копию, чтобы избежать ошибок при изменении
            requests_copy = user_requests.copy()
            
            if requests_copy:
                print(f"🔍 Проверяю {len(requests_copy)} запросов...")
                
                for chat_id, data in requests_copy.items():
                    try:
                        # Проверяем билеты
                        prices, url = parse_tickets(data["date"], data["train"])
                        
                        if prices:
                            # БИЛЕТЫ НАЙДЕНЫ!
                            message = (
                                f"🎉 *БИЛЕТЫ ПОЯВИЛИСЬ!*\n\n"
                                f"🚆 *Поезд:* {data['train']}\n"
                                f"📅 *Дата:* {data['date']}\n"
                                f"💰 *Цены:* {', '.join(prices)}\n\n"
                                f"🔗 [Купить билеты]({url})"
                            )
                            
                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=message,
                                parse_mode="Markdown",
                                disable_web_page_preview=False
                            )
                            
                            # Удаляем из отслеживания
                            if chat_id in user_requests:
                                del user_requests[chat_id]
                                print(f"✅ Отправил билеты пользователю {chat_id}")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка при проверке {chat_id}: {e}")
                        # Не удаляем запрос при ошибке
                        
            # Ждем перед следующей проверкой
            import asyncio
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"⚠️ Ошибка в фоновой проверке: {e}")
            import asyncio
            await asyncio.sleep(60)  # Ждем минуту при ошибке

# ========== ЗАПУСК БОТА ==========
def main():
    """Главная функция запуска бота"""
    
    # Проверяем токен
    if not TOKEN:
        print("❌ ОШИБКА: Не задан TELEGRAM_TOKEN!")
        print("Добавьте переменную окружения TELEGRAM_TOKEN")
        return
    
    print("🚀 Запуск бота...")
    
    # Создаем приложение бота
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("list", list_command))
    
    # Запускаем фоновую проверку
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(check_tickets_periodically(app))
    
    print("✅ Бот успешно запущен!")
    print("👂 Ожидаю команды от пользователей...")
    
    # Запускаем бота
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    main()
