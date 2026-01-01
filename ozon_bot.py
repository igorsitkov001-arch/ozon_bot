import time
import re
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# ====================================
# Настройки (TOKEN и CHAT_ID берутся
# из переменных окружения Render)
# ====================================
TOKEN = os.environ["TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
CHECK_INTERVAL = 300   # 5 минут

url = "https://www.ozon.ru/highlight/bally-za-otzyv-1171518/"

sent_items = set()

# ====================================
# Telegram уведомления
# ====================================
def send_message(text):
    try:
        api = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(api, data={"chat_id": CHAT_ID, "text": text})
    except:
        pass

# ====================================
# Парсинг Ozon
# ====================================
def load_page():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(5)

    # глубокий скролл
    for _ in range(70):
        driver.execute_script("window.scrollBy(0, 2500);")
        time.sleep(1)

    cards = driver.find_elements("css selector", "div.tile-root")

    results = []

    for card in cards:
        html = card.get_attribute("outerHTML")

        # название
        names = re.findall(r'<span[^>]*>([^<]{10,})</span>', html)
        if not names:
            continue
        name = max(names, key=len).strip()

        # цена
        price_m = re.search(r'(\d[\d\s\u2009\u202f]*)\s*₽', html)
        if not price_m:
            continue
        price = int(re.sub(r"\D", "", price_m.group(1)))

        # баллы
        bonus_m = re.search(r'(\d+)\s*балл', html)
        if not bonus_m:
            continue
        bonus = int(re.sub(r"\D", "", bonus_m.group(1)))

        profit = bonus - price

        # ссылка
        link_m = re.search(r'href="([^"]+)"', html)
        link = "https://www.ozon.ru" + link_m.group(1) if link_m else "Нет ссылки"

        results.append({
            "name": name,
            "price": price,
            "bonus": bonus,
            "profit": profit,
            "link": link
        })

    driver.quit()
    return results

# ====================================
# Комбинированный фильтр
# ====================================
def filter_goods(data):
    filtered = []

    for item in data:
        price = item["price"]
        bonus = item["bonus"]
        profit = item["profit"]

        # ✔ Выгода >= 100
        if profit >= 100:
            filtered.append(item)
            continue

        # ✔ Баллы ≈ цене (±10%), но цена >= 500
        if price >= 500 and abs(price - bonus) <= price * 0.10:
            filtered.append(item)
            continue

    return filtered

# ====================================
# Основной цикл бота
# ====================================
def main():
    send_message("🤖 Бот запущен! Ищу выгодные товары на Ozon каждые 5 минут...")

    while True:
        try:
            data = load_page()
            goods = filter_goods(data)

            for item in goods:
                if item["link"] in sent_items:
                    continue

                sent_items.add(item["link"])

                msg = (
                    f"🔥 Выгодный товар найден!\n\n"
                    f"{item['name']}\n"
                    f"Цена: {item['price']} ₽\n"
                    f"Баллы: {item['bonus']}\n"
                    f"Выгода: {item['profit']}\n\n"
                    f"{item['link']}"
                )

                send_message(msg)

        except Exception as e:
            send_message(f"⚠ Ошибка: {e}")

        time.sleep(CHECK_INTERVAL)

main()