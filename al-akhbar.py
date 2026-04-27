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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta


BASE = "https://www.al-akhbar.com"
URL = BASE + "/category/lebanon"


def pretty_url(url: str) -> str:
    return unquote(url or "")


def open_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)


def safe_js_click(driver, el):
    # scroll just enough to reach the button (center), then click
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", el)


def wait_for_count_increase(driver, xpath: str, old_count: int, timeout: int = 25) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            new_count = len(driver.find_elements(By.XPATH, xpath))
            if new_count > old_count:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def parse_ddmmyyyy(s: str):
    # returns datetime.date or None
    try:
        return datetime.strptime(s.strip(), "%d.%m.%Y").date()
    except Exception:
        return None


def get_alakhbar_until_date(driver, max_clicks: int = 80):
    """
    Collect articles from category/lebanon and keep clicking "إظهار المزيد"
    until we reach stop_at_date_str (or older) in the loaded cards.
    """
    driver.get(URL)
    wait = WebDriverWait(driver, 25)

    today = datetime.now().date()
    stop_at_date = today - timedelta(days=1)  # ✅ yesterday
    print("Stopping at:", stop_at_date.strftime("%d.%m.%Y"))

    # card wrapper based on your HTML
    CARD_XPATH = "//div[contains(@class,'flex') and contains(@class,'group') and contains(@class,'flex-1')]"

    # the clickable "load more" div
    LOAD_MORE_XPATH = "//div[contains(@class,'cursor-pointer') and normalize-space(text())='إظهار المزيد']"

    results = []
    seen = set()

    def parse_cards_once():
        cards = driver.find_elements(By.XPATH, CARD_XPATH)
        parsed = []

        for card in cards:
            try:
                a = card.find_element(
                    By.XPATH,
                    ".//a[contains(@href,'/news/lebanon/') or contains(@href,'/Newspaper%20Articles/lebanon/')]"
                )
                href = a.get_attribute("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = BASE + href

                title = card.find_element(By.XPATH, ".//h2").text.strip()

                # date usually in this p:
                date_txt = ""
                try:
                    date_txt = card.find_element(By.XPATH, ".//p[contains(@class,'text-[#3d3d3c]')]").text.strip()
                except Exception:
                    m = re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", card.text)
                    if m:
                        date_txt = m.group(0)

                parsed.append((href, title, date_txt))
            except (StaleElementReferenceException, Exception):
                continue

        return parsed

    clicks = 0

    while clicks <= max_clicks:
        parsed = parse_cards_once()

        # save uniques
        for href, title, date_txt in parsed:
            if href in seen:
                continue
            seen.add(href)
            results.append({"url": href, "title": title, "date": date_txt})

        # compute the oldest date currently visible; if we reached stop date or older -> stop
        dates = []
        for _, _, date_txt in parsed:
            d = parse_ddmmyyyy(date_txt) if date_txt else None
            if d:
                dates.append(d)

        oldest = min(dates) if dates else None
        newest = max(dates) if dates else None
        print(f"Round {clicks}: total={len(results)} newest={newest} oldest={oldest}")

        if oldest and oldest <= stop_at_date:
            print(f"✔ Reached {stop_at_date} (or older) → stopping")
            break

        # click load more
        try:
            old_count = len(driver.find_elements(By.XPATH, CARD_XPATH))
            load_more = wait.until(EC.presence_of_element_located((By.XPATH, LOAD_MORE_XPATH)))
            safe_js_click(driver, load_more)

            grew = wait_for_count_increase(driver, CARD_XPATH, old_count, timeout=25)
            if not grew:
                print("✔ Clicked load more, but no more cards loaded → stopping")
                break

        except TimeoutException:
            print("✔ No load more button found → stopping")
            break

        clicks += 1
        time.sleep(0.6)

    return results


def save_csv(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"alakhbar_until_{today}.csv"

    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["link", "title", "date"])
        for a in articles:
            w.writerow([pretty_url(a["url"]), a["title"], a["date"]])

    print("✅ Saved:", fn)


def fetch(driver):
    """
    Called by main.py.
    Returns a list of dicts in unified format keys.
    Stops at yesterday automatically (your existing logic).
    """
    items = get_alakhbar_until_date(driver, max_clicks=80)

    out = []
    for it in items:
        out.append({
            "section": "lebanon",
            "date": it.get("date", ""),
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "content": "",
        })
    return out

# if __name__ == "__main__":
#     driver = open_driver()
#     try:
#         # Stops once page reaches 26.01.2026
#         articles = get_alakhbar_until_date(driver,  max_clicks=80)
#         save_csv(articles)
#         print("✅ FINAL total:", len(articles))
#     finally:
#         driver.quit()
