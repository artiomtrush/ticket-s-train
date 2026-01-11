import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def parse_tickets(date: str, train_number: str):
    """
    Парсит страницу pass.rw.by по дате и номеру поезда.
    Возвращает список цен и URL маршрута.
    """
    url = (
        "https://pass.rw.by/ru/route/?"
        "from=%D0%9C%D0%B8%D0%BD%D1%81%D0%BA&from_exp=2100000&"
        "to=%D0%9C%D0%BE%D0%B7%D1%8B%D1%80%D1%8C&to_exp=2100254&"
        f"date={date}&type=1"
    )

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        return [], f"Ошибка запроса: {e}"

    soup = BeautifulSoup(r.text, "html.parser")
    train = soup.find(
        "div",
        class_="sch-table__row",
        attrs={"data-train-number": train_number}
    )

    if not train:
        return [], "Поезд не найден"

    no_info = train.find("div", class_="sch-table__no-info")
    if no_info:
        return [], "Мест нет"

    prices = []
    for price_el in train.select(".ticket-cost"):
        prices.append(price_el.text.strip())

    if not prices:
        return [], "Мест нет"

    return prices, url
