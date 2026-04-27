#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 23:39:31 2026

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
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


BASE = "https://www.nidaalwatan.com"
URL = "https://www.nidaalwatan.com/section/4-%D9%85%D8%AD%D9%84%D9%8A%D8%A7%D8%AA"


# ---------------------------
# Helpers
# ---------------------------

def pretty_url(url):
    return unquote(url)


def scroll_to_bottom(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


# ---------------------------
# Driver
# ---------------------------

def open_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)


# ---------------------------
# Scraper
# ---------------------------

def get_nidaa_watan_today(driver):
    driver.get(URL)
    wait = WebDriverWait(driver, 20)

    # TODAY format on site: "21 . 01 . 2026"
    today = datetime.now().strftime("%d . %m . %Y")

    results = []
    seen = set()

    def parse_items():
        items = driver.find_elements(By.CSS_SELECTOR, "li.ias-item")
        parsed = []

        for it in items:
            try:
                link = it.find_element(By.TAG_NAME, "a").get_attribute("href")
                title = it.find_element(By.TAG_NAME, "h2").text.strip()
                date = it.find_element(By.CSS_SELECTOR, "span.time").text.strip()

                parsed.append((date, title, link))
            except Exception:
                continue

        return parsed

    max_scrolls = 60
    scrolls = 0

    while scrolls < max_scrolls:
        parsed = parse_items()

        new_today_found = False

        for d, t, l in parsed:
            if d == today and l not in seen:
                results.append({
                    "date": d,
                    "title": t,
                    "url": l
                })
                seen.add(l)
                new_today_found = True

        # ✅ STOP when scrolling no longer yields NEW today articles
        if not new_today_found:
            print("✔ No new TODAY articles → stopping scroll")
            break

        prev_count = len(parsed)

        scroll_to_bottom(driver)
        time.sleep(1.8)

        # Wait for new items to load
        for _ in range(10):
            time.sleep(0.4)
            if len(parse_items()) > prev_count:
                break

        scrolls += 1

    return results


# ---------------------------
# Save
# ---------------------------

def save_txt(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"nidaa_watan_{today}.txt"

    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"NIDAA EL WATAN — محليات — {today}\n")
        f.write(f"Total: {len(articles)}\n\n")

        for i, a in enumerate(articles, 1):
            f.write(f"{i}. [{a['date']}] {a['title']}\n")
            f.write(f"   {pretty_url(a['url'])}\n\n")

    print("✅ Saved:", fn)

def get_nidaa_watan_asrar_today(driver):
    url = "https://www.nidaalwatan.com/section/64-%D8%A3%D8%B3%D8%B1%D8%A7%D8%B1"
    driver.get(url)

    today = datetime.now().strftime("%d.%m.%Y")

    results = []

    items = driver.find_elements(By.CSS_SELECTOR, "div.wrapper.ias-item")

    for it in items:
        try:
            # Date + link are the same anchor
            h3_a = it.find_element(By.CSS_SELECTOR, "h3 a")
            date = h3_a.text.strip()
            link = h3_a.get_attribute("href")

            if date != today:
                continue

            paragraphs = [
                p.text.strip()
                for p in it.find_elements(By.CSS_SELECTOR, "div.content p")
                if p.text.strip()
            ]

            if paragraphs:
                results.append({
                    "date": date,
                    "url": link,
                    "paragraphs": paragraphs
                })

        except Exception:
            continue

    return results

def save_csv(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"nidaa_watan_{today}.csv"

    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["link", "title", "date"])

        for a in articles:
            w.writerow([
                pretty_url(a["url"]),
                a["title"],
                a["date"]
            ])

    print("✅ Saved:", fn)


# ---------------------------
# Run
# ---------------------------

if __name__ == "__main__":
    driver = open_driver()
    try:
        articles = get_nidaa_watan_today(driver)
        save_txt(articles)
        save_csv(articles)
    finally:
        driver.quit()
