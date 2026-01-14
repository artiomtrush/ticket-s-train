import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

def parse_tickets(date: str, train_number: str):
    """
    Парсит страницу pass.rw.by по дате и номеру поезда.
    Возвращает список цен и URL маршрута.
    """
    # Кодированные станции (Минск и Мозырь)
    url = (
        "https://pass.rw.by/ru/route/?"
        "from=%D0%9C%D0%B8%D0%BD%D1%81%D0%BA&from_exp=2100000&"
        "to=%D0%9C%D0%BE%D0%B7%D1%8B%D1%80%D1%8C&to_exp=2100254&"
        f"date={date}&type=1"
    )

    try:
        # Добавляем небольшую задержку и retry логику
        time.sleep(1)  # Защита от блокировки
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса к {url}: {e}")
        return [], f"Ошибка запроса: {e}"

    soup = BeautifulSoup(r.content, 'html.parser')
    
    # Ищем поезд по номеру
    train = soup.find(
        "div",
        class_="sch-table__row",
        attrs={"data-train-number": train_number}
    )

    if not train:
        print(f"Поезд {train_number} не найден на странице")
        return [], f"Поезд {train_number} не найден"

    # Проверяем наличие мест
    no_info = train.find("div", class_="sch-table__no-info")
    if no_info:
        print(f"Мест нет для поезда {train_number}")
        return [], "Мест нет"

    # Ищем цены
    prices = []
    price_elements = train.select(".ticket-cost")
    
    for price_el in price_elements:
        price_text = price_el.text.strip()
        if price_text:
            prices.append(price_text)

    if not prices:
        # Проверяем другие возможные элементы с ценами
        alternative_prices = train.select(".sch-table__cell-cost")
        for alt_price in alternative_prices:
            price_text = alt_price.text.strip()
            if price_text and price_text != "—":
                prices.append(price_text)

    if not prices:
        print(f"Цены не найдены для поезда {train_number}")
        return [], "Мест нет"

    return prices, url
