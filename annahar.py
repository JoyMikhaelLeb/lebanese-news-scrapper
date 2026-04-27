#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 23:06:31 2026

@author: joy
"""
import time
from datetime import datetime
from urllib.parse import unquote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)

from webdriver_manager.chrome import ChromeDriverManager


# ---------------------------
# Helpers
# ---------------------------

def pretty_url(url: str) -> str:
    """
    Annahar hrefs are often percent-encoded.
    This decodes them so your TXT shows Arabic as on the page.
    (Display-only; the encoded URL is usually the safest one to request programmatically.)
    """
    try:
        return unquote(url, encoding="utf-8", errors="strict")
    except Exception:
        return unquote(url)  # fallback


def safe_scroll_center(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el)
    time.sleep(0.3)


def click_load_more(driver, wait, load_more_css="div.loadMore", cards_css="div.listingInfos"):
    """
    Robust click for Annahar "Load more" that avoids ElementClickInterceptedException.
    Returns True if new cards loaded, else False.
    """
    # Wait for button present + clickable
    btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, load_more_css)))
    safe_scroll_center(driver, btn)

    # count cards before click
    before_count = len(driver.find_elements(By.CSS_SELECTOR, cards_css))

    # Try multiple click strategies
    last_err = None
    for attempt in range(3):
        try:
            # re-find each attempt to avoid stale references
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, load_more_css)))
            safe_scroll_center(driver, btn)

            if attempt == 0:
                btn.click()
            elif attempt == 1:
                ActionChains(driver).move_to_element(btn).pause(0.2).click(btn).perform()
            else:
                driver.execute_script("arguments[0].click();", btn)

            # Wait until more cards appear
            for _ in range(30):  # ~15s
                time.sleep(0.5)
                after_count = len(driver.find_elements(By.CSS_SELECTOR, cards_css))
                if after_count > before_count:
                    return True
            return False

        except (ElementClickInterceptedException, WebDriverException) as e:
            last_err = e
            # small nudge scroll in case sticky header overlaps
            driver.execute_script("window.scrollBy(0, -120);")
            time.sleep(0.4)

    # If all attempts failed
    if last_err:
        print("Load more click failed:", repr(last_err))
    return False


# ---------------------------
# Driver
# ---------------------------

def login():
    url = "https://www.annahar.com"

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--start-maximized")

    try:
        driver = webdriver.Chrome(
            executable_path="/home/joy/Downloads/chromedriver_linux64/chromedriver",
            chrome_options=chrome_options
        )
    except Exception:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    driver.get(url)
    return driver


# ---------------------------
# Parsers
# ---------------------------
import re

def extract_date_ddmmyyyy(date_text: str):
    """
    Returns date as 'DD-MM-YYYY' from either:
    - '21-01-2026 | 15:03'
    - '1/22/2026 5:05:00 AM'
    """
    txt = " ".join(date_text.split())

    # Match 21-01-2026
    m = re.search(r"\b(\d{2}-\d{2}-\d{4})\b", txt)
    if m:
        return m.group(1)

    # Match 1/22/2026 or 01/22/2026
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", txt)
    if m:
        mm, dd, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{int(dd):02d}-{int(mm):02d}-{yyyy}"

    return None

def parse_cards(driver):
    cards = driver.find_elements(By.CSS_SELECTOR, "div.listingInfos")
    parsed = []

    for c in cards:
        try:
            date_text = c.find_element(By.CSS_SELECTOR, "div.listingDate").text.strip()
            date_part = extract_date_ddmmyyyy(date_text)

            title_a = c.find_element(By.CSS_SELECTOR, "div.listingTitle a")
            title = title_a.text.strip()
            link = title_a.get_attribute("href")

            if date_part and title and link:
                parsed.append((date_part, title, link))

        except Exception:
            continue

    return parsed


def date_to_tuple(d):  # "DD-MM-YYYY" -> (YYYY,MM,DD)
    dd, mm, yyyy = d.split("-")
    return (int(yyyy), int(mm), int(dd))


def get_section_today(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    target_date = datetime.now().strftime("%d-%m-%Y")
    target_tuple = date_to_tuple(target_date)

    results = []
    seen_urls = set()

    while True:
        parsed = parse_cards(driver)

        # collect today's articles
        for d, t, l in parsed:
            if d == target_date and l not in seen_urls:
                results.append({"date": d, "title": t, "url": l})
                seen_urls.add(l)

        # stop if we see any date older than today
        older_found = any(date_to_tuple(d) < target_tuple for d, _, _ in parsed if d)
        if older_found:
            break

        # click load more; if no new cards load, stop
        try:
            loaded = click_load_more(driver, wait)
        except TimeoutException:
            break

        if not loaded:
            break

    return results


def get_lebanon(driver):
    return get_section_today(driver, "https://www.annahar.com/lebanon/")


def get_lebanon_whispers(driver):
    return get_section_today(driver, "https://www.annahar.com/lebanon/whispers/")



def get_lebanon_special(driver):
    return get_section_today(driver,"https://www.annahar.com/articles/annahar-writers")


# ---------------------------
# Save
# ---------------------------

def save_articles_txt(articles, filename=None):
    today = datetime.now().strftime("%Y-%m-%d")
    if filename is None:
        filename = f"annahar_{today}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"ANNAHAR — {today}\n")
        f.write(f"Total: {len(articles)}\n\n")

        for i, item in enumerate(articles, start=1):
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            date = item.get("date", "").strip()

            f.write(f"{i}. [{date}] {title}\n")
            # Decode so it prints Arabic like on the page:
            f.write(f"   {pretty_url(url)}\n\n")

    print("Saved:", filename)

import csv
def save_articles_csv(articles, filename=None):
    today = datetime.now().strftime("%Y-%m-%d")
    if filename is None:
        filename = f"annahar_{today}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(["link", "title", "date"])

        # Rows
        for item in articles:
            writer.writerow([
                pretty_url(item.get("url", "")),   # Arabic visible
                item.get("title", ""),
                item.get("date", "")
            ])

    print("✅ CSV saved:", filename)
def get_annahar_data(driver):
    lebanon_articles = get_lebanon(driver)
    whispers_articles = get_lebanon_whispers(driver)
    for_annahar = get_lebanon_special(driver)

    merged = lebanon_articles + whispers_articles+for_annahar

    # drop duplicates by URL (keeps first occurrence)
    merged_unique = list({item["url"]: item for item in merged}.values())

    # save_articles_txt(merged_unique)
    save_articles_csv(merged_unique)


# ---------------------------
# Run
# ---------------------------
def fetch(driver):
    # already merges sections inside get_annahar_data(), but that saves a CSV.
    # We want it to RETURN data instead.
    lebanon = get_lebanon(driver)
    whispers = get_lebanon_whispers(driver)
    writers = get_lebanon_special(driver)

    merged = lebanon + whispers + writers
    merged_unique = list({item["url"]: item for item in merged}.values())

    out = []
    for it in merged_unique:
        out.append({
            "section": "lebanon/whispers/writers",
            "date": it.get("date", ""),
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "content": "",
        })
    return out


# if __name__ == "__main__":
#     driver = login()
#     try:
#         get_annahar_data(driver)
#     finally:
#         try:
#             driver.quit()
#         except Exception:
#             pass
