#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 23:48:46 2026

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

URL_MAHALIYAT = "https://www.nidaalwatan.com/section/4-%D9%85%D8%AD%D9%84%D9%8A%D8%A7%D8%AA"
URL_ASRAR = "https://www.nidaalwatan.com/section/64-%D8%A3%D8%B3%D8%B1%D8%A7%D8%B1"


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
# محليات (Infinite scroll)
# ---------------------------

def get_nidaa_watan_mahaliyat_today(driver):
    driver.get(URL_MAHALIYAT)
    wait = WebDriverWait(driver, 20)

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
                    "section": "محليات",
                    "date": d,
                    "title": t,
                    "url": l,
                    "content": ""
                })
                seen.add(l)
                new_today_found = True

        if not new_today_found:
            break

        prev_count = len(parsed)
        scroll_to_bottom(driver)
        time.sleep(1.8)

        for _ in range(10):
            time.sleep(0.4)
            if len(parse_items()) > prev_count:
                break

        scrolls += 1

    return results


# ---------------------------
# أسرار (special structure)
# ---------------------------

def get_nidaa_watan_asrar_today(driver):
    driver.get(URL_ASRAR)

    today = datetime.now().strftime("%d.%m.%Y")
    results = []

    items = driver.find_elements(By.CSS_SELECTOR, "div.wrapper.ias-item")

    for it in items:
        try:
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

            results.append({
                "section": "أسرار",
                "date": date,
                "title": "أسرار اليوم",
                "url": link,
                "content": " || ".join(paragraphs)
            })

        except Exception:
            continue

    return results


# ---------------------------
# Save
# ---------------------------

def save_txt(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"nidaa_watan_{today}.txt"

    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"NIDAA EL WATAN — {today}\n")
        f.write(f"Total: {len(items)}\n\n")

        for i, it in enumerate(items, 1):
            f.write(f"{i}. [{it['section']}] [{it['date']}] {it['title']}\n")
            f.write(f"   {pretty_url(it['url'])}\n")

            if it["content"]:
                for p in it["content"].split(" || "):
                    f.write(f"   - {p}\n")

            f.write("\n")

    print("✅ Saved TXT:", fn)


def save_csv(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"nidaa_watan_{today}.csv"

    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["section", "link", "title", "date", "content"])

        for it in items:
            # 🔹 For محليات (no paragraphs)
            if it["section"] != "أسرار":
                w.writerow([
                    it["section"],
                    pretty_url(it["url"]),
                    it["title"],
                    it["date"],
                    ""
                ])
                continue

            # 🔹 For أسرار: split into multiple rows
            paragraphs = it["content"].split(" || ")

            for p in paragraphs:
                if not p.strip():
                    continue

                w.writerow([
                    it["section"],
                    pretty_url(it["url"]),
                    it["title"],
                    it["date"],
                    p.strip()
                ])

    print("✅ Saved CSV:", fn)


# ---------------------------
# Run
# ---------------------------
def fetch(driver):
    data = []
    data.extend(get_nidaa_watan_mahaliyat_today(driver))
    data.extend(get_nidaa_watan_asrar_today(driver))

    out = []
    for it in data:
        out.append({
            "section": it.get("section", ""),
            "date": it.get("date", ""),
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "content": it.get("content", "") or "",
        })
    return out

# if __name__ == "__main__":
#     driver = open_driver()
#     try:
#         data = []
#         data.extend(get_nidaa_watan_mahaliyat_today(driver))
#         data.extend(get_nidaa_watan_asrar_today(driver))

#         # save_txt(data)
#         save_csv(data)
#     finally:
#         driver.quit()
