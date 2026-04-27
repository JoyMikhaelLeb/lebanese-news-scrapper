#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import csv
import re
from datetime import datetime
from urllib.parse import unquote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


BASE = "https://www.aljoumhouria.com"
URL = "https://www.aljoumhouria.com/ar/news/category/1/محلي"

TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")   # 0:05, 9:10, 21:55
MONTH_RE = re.compile(r"^[A-Za-z]{3}\s+\d{1,2}$")  # Jan 20


def pretty_url(url: str) -> str:
    try:
        return unquote(url)
    except Exception:
        return url


def start_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)


def safe_js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.25)
    driver.execute_script("arguments[0].click();", el)


def get_time_text(card):
    try:
        t = card.find_element(By.CSS_SELECTOR, "div.info-feed div.time").text.strip()
        # normalize whitespace/newlines
        t = " ".join(t.split())
        return t
    except Exception:
        return ""


def parse_cards(driver):
    cards = driver.find_elements(By.CSS_SELECTOR, "div.card.animation")
    out = []

    for c in cards:
        try:
            a = c.find_element(By.CSS_SELECTOR, "a")
            href = a.get_attribute("href") or ""
            if href.startswith("/"):
                href = BASE + href

            title = c.find_element(By.CSS_SELECTOR, "div.card-text").text.strip()
            t = get_time_text(c)

            out.append({"time": t, "title": title, "url": href})
        except Exception:
            continue

    return out


def load_until_month(driver, max_clicks=120):
    driver.get(URL)
    wait = WebDriverWait(driver, 25)

    # Wait for cards to appear
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.animation")))

    clicks = 0

    while clicks < max_clicks:
        cards = driver.find_elements(By.CSS_SELECTOR, "div.card.animation")

        # ✅ Stop condition: if ANY visible card shows month format (e.g. "Jan 20")
        month_found = False
        for c in cards:
            t = get_time_text(c)
            if MONTH_RE.match(t):
                month_found = True
                break
        if month_found:
            break

        before = len(cards)

        # Find "المزيد"
        try:
            load_more = driver.find_element(By.CSS_SELECTOR, "div#loadMore.load-more")
        except Exception:
            break

        try:
            if not load_more.is_displayed():
                break
        except Exception:
            break

        # Click and wait for new cards
        try:
            safe_js_click(driver, load_more)
        except WebDriverException:
            break

        loaded = False
        for _ in range(20):  # ~10s
            time.sleep(0.5)
            after = len(driver.find_elements(By.CSS_SELECTOR, "div.card.animation"))
            if after > before:
                loaded = True
                break

        if not loaded:
            break

        clicks += 1

    # After stopping, parse everything loaded
    return parse_cards(driver)


def filter_today_time_only(items):
    """
    Keep only items whose 'time' is HH:MM (today items),
    drop month labels like "Jan 20".
    """
    filtered = []
    seen = set()

    for it in items:
        t = (it.get("time") or "").strip()
        if not TIME_RE.match(t):
            continue

        url = it.get("url", "")
        if url and url not in seen:
            seen.add(url)
            filtered.append(it)

    return filtered


def save_txt(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"aljoumhouria_local_{today}.txt"

    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"AL JOUMHOURIA — محلي (time-only) — {today}\n")
        f.write(f"Total: {len(items)}\n\n")

        for i, it in enumerate(items, 1):
            f.write(f"{i}. [{it['time']}] {it['title']}\n")
            f.write(f"   {pretty_url(it['url'])}\n\n")

    print("✅ Saved TXT:", fn)


def save_csv(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"aljoumhouria_local_{today}.csv"

    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["time", "title", "link"])

        for it in items:
            w.writerow([it["time"], it["title"], pretty_url(it["url"])])

    print("✅ Saved CSV:", fn)

def fetch(driver):
    items = load_until_month(driver, max_clicks=120)  # gets a lot
    items = filter_today_time_only(items)            # keeps today
    out = []
    for it in items:
        out.append({
            "section": "lebanon",
            "date": it.get("time", ""),   # or keep as time string
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "content": "",
        })
    return out

# if __name__ == "__main__":
#     driver = start_driver()
#     try:
#         loaded_items = load_until_month(driver)
#         today_items = filter_today_time_only(loaded_items)
#         # save_txt(today_items)
#         save_csv(today_items)
#     finally:
#         driver.quit()
