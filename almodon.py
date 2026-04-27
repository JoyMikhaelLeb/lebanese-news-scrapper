#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import csv
import re
from datetime import datetime
from urllib.parse import unquote, urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


BASE = "https://www.almodon.com"

SECTIONS = {
    "opinion": f"{BASE}/opinion",
    "politics": f"{BASE}/politics",
}

DATE_IN_URL_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")  # /2026/01/22/


def pretty_url(url: str) -> str:
    try:
        return unquote(url)
    except Exception:
        return url


def open_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)


def extract_date_from_url(href: str):
    """
    Returns YYYY-MM-DD from a URL like /politics/2026/01/22/slug
    """
    m = DATE_IN_URL_RE.search(href or "")
    if not m:
        return None
    yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
    return f"{yyyy}-{mm}-{dd}"


def date_to_tuple(iso_date: str):
    # YYYY-MM-DD -> (YYYY,MM,DD)
    y, m, d = iso_date.split("-")
    return (int(y), int(m), int(d))


def parse_cards(driver):
    """
    Your card wrapper:
    div.w-full.lg:w-1/2.lg:px-3.mb-6  (repeats)
    Title link:
    h2 a[href]
    Date also appears in a span, but URL is the most stable.
    """
    cards = driver.find_elements(By.CSS_SELECTOR, "div.w-full.lg\\:w-1\\/2.lg\\:px-3.mb-6")
    parsed = []

    for c in cards:
        try:
            a = c.find_element(By.CSS_SELECTOR, "h2 a")
            title = a.text.strip()
            href = a.get_attribute("href") or ""

            # Normalize to full URL
            url = urljoin(BASE, href)

            date_iso = extract_date_from_url(url)
            if not date_iso:
                continue

            parsed.append((date_iso, title, url))
        except Exception:
            continue

    return parsed


def click_load_more_if_exists(driver):
    """
    Almodon sometimes has pagination / load more depending on viewport.
    We'll try a few common patterns; if none found, return False.
    """
    candidates = [
        # common "Load more" buttons (best-effort)
        (By.XPATH, "//button[contains(.,'المزيد') or contains(.,'إظهار المزيد') or contains(.,'تحميل المزيد')]"),
        (By.XPATH, "//a[contains(.,'المزيد') or contains(.,'إظهار المزيد') or contains(.,'تحميل المزيد')]"),
        (By.CSS_SELECTOR, "button.load-more"),
        (By.CSS_SELECTOR, "a.load-more"),
    ]

    for by, sel in candidates:
        try:
            el = driver.find_element(by, sel)
            if el.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", el)
                return True
        except Exception:
            continue

    return False


def scrape_section_today(driver, section_name, url):
    wait = WebDriverWait(driver, 20)
    driver.get(url)

    # Wait for at least one card
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.w-full.lg\\:w-1\\/2.lg\\:px-3.mb-6")))
    except TimeoutException:
        return []

    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_tuple = date_to_tuple(today_iso)

    results = []
    seen = set()

    max_steps = 60
    steps = 0

    while steps < max_steps:
        parsed = parse_cards(driver)

        # Collect today's items from what we have now
        for d, t, l in parsed:
            if d == today_iso and l not in seen:
                seen.add(l)
                results.append({
                    "section": section_name,
                    "date": d,
                    "title": t,
                    "url": l
                })

        # Stop if we can see any item older than today (we passed today's batch)
        older_found = any(date_to_tuple(d) < today_tuple for d, _, _ in parsed if d)
        if older_found:
            break

        # Try to load more
        before_count = len(parsed)
        loaded = click_load_more_if_exists(driver)
        if not loaded:
            break

        # wait for new cards
        for _ in range(20):
            time.sleep(0.5)
            after_count = len(parse_cards(driver))
            if after_count > before_count:
                break
        else:
            break

        steps += 1

    return results


def save_txt(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"almodon_{today}.txt"

    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"ALMODON — {today}\n")
        f.write(f"Total: {len(items)}\n\n")
        for i, it in enumerate(items, 1):
            f.write(f"{i}. [{it['section']}] [{it['date']}] {it['title']}\n")
            f.write(f"   {pretty_url(it['url'])}\n\n")

    print("✅ Saved TXT:", fn)


def save_csv(items):
    today = datetime.now().strftime("%Y-%m-%d")
    fn = f"almodon_{today}.csv"

    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["section", "date", "title", "link"])
        for it in items:
            w.writerow([it["section"], it["date"], it["title"], pretty_url(it["url"])])

    print("✅ Saved CSV:", fn)

def fetch(driver):
    merged = []
    for sec, url in SECTIONS.items():
        merged.extend(scrape_section_today(driver, sec, url))

    merged_unique = list({it["url"]: it for it in merged}.values())

    out = []
    for it in merged_unique:
        out.append({
            "section": it.get("section", ""),
            "date": it.get("date", ""),
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "content": "",
        })
    return out

# if __name__ == "__main__":
#     driver = open_driver()
#     try:
#         merged = []
#         for sec, url in SECTIONS.items():
#             merged.extend(scrape_section_today(driver, sec, url))

#         # dedupe by URL across sections
#         merged_unique = list({it["url"]: it for it in merged}.values())

#         # save_txt(merged_unique)
#         save_csv(merged_unique)

#     finally:
#         driver.quit()
