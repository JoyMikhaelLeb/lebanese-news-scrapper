#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 28 10:52:32 2026

@author: admin
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import csv
from datetime import datetime
from urllib.parse import unquote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


BASE = "https://aliwaa.com.lb"

SECTIONS = {
    "سياسة": "https://aliwaa.com.lb/أخبار-لبنان/سياسة/",
    "أمن قضاء": "https://aliwaa.com.lb/أخبار-لبنان/أمن-قضاء/",
}

AR_MONTHS = {
    "كانون الثاني": 1,
    "شباط": 2,
    "آذار": 3,
    "نيسان": 4,
    "أيار": 5,
    "حزيران": 6,
    "تموز": 7,
    "آب": 8,
    "أيلول": 9,
    "تشرين الأول": 10,
    "تشرين الثاني": 11,
    "كانون الأول": 12,
}


# ---------------------------
# Helpers
# ---------------------------

def pretty_url(url):
    return unquote(url)


def parse_arabic_date(txt):
    """
    '21 كانون الثاني 2026' → '2026-01-21'
    """
    parts = txt.replace("\xa0", " ").split()
    if len(parts) < 3:
        return None

    day = int(parts[0])
    month_name = " ".join(parts[1:-1])
    year = int(parts[-1])

    month = AR_MONTHS.get(month_name)
    if not month:
        return None

    return f"{year:04d}-{month:02d}-{day:02d}"


def open_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)


# ---------------------------
# Scraper
# ---------------------------

def scrape_section_today(driver, section_name, base_url):
    wait = WebDriverWait(driver, 20)

    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_tuple = datetime.strptime(today_iso, "%Y-%m-%d").date()

    results = []
    seen = set()
    page = 1

    while True:
        url = base_url if page == 1 else f"{base_url}?page={page}"
        driver.get(url)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.item")))
        except TimeoutException:
            break

        cards = driver.find_elements(By.CSS_SELECTOR, "div.item")
        if not cards:
            break

        stop = False

        for c in cards:
            try:
                date_txt = c.find_element(By.CSS_SELECTOR, "span.meta").text.strip()
                date_iso = parse_arabic_date(date_txt)
                if not date_iso:
                    continue

                article_date = datetime.strptime(date_iso, "%Y-%m-%d").date()

                title_a = c.find_element(By.CSS_SELECTOR, "h6.title a")
                title = title_a.text.strip()
                link = title_a.get_attribute("href")

                if link.startswith("/"):
                    link = BASE + link

                if article_date == today_tuple:
                    if link not in seen:
                        seen.add(link)
                        results.append({
                            "section": section_name,
                            "date": date_iso,
                            "title": title,
                            "url": link
                        })

                elif article_date < today_tuple:
                    stop = True
                    break

            except Exception:
                continue

        if stop:
            break

        page += 1
        time.sleep(0.6)

    return results


# ---------------------------
# Save
# ---------------------------

def save_txt(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"aliwaa_{today}.txt"

    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"AL LIWAA — {today}\n")
        f.write(f"Total: {len(items)}\n\n")

        for i, it in enumerate(items, 1):
            f.write(f"{i}. [{it['section']}] [{it['date']}] {it['title']}\n")
            f.write(f"   {pretty_url(it['url'])}\n\n")

    print("✅ Saved TXT:", fn)


def save_csv(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"aliwaa_{today}.csv"

    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["section", "date", "title", "link"])

        for it in items:
            w.writerow([
                it["section"],
                it["date"],
                it["title"],
                pretty_url(it["url"])
            ])

    print("✅ Saved CSV:", fn)


# ---------------------------
# Run
# ---------------------------
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
#     driver = open_driver()
#     try:
#         all_items = []

#         for section, url in SECTIONS.items():
#             all_items.extend(scrape_section_today(driver, section, url))

#         # save_txt(all_items)
#         save_csv(all_items)

#     finally:
#         driver.quit()
