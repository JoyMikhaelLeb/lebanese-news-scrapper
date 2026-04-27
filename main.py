#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 27 22:14:14 2026

@author: admin
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import traceback
import importlib.util
from datetime import datetime
from typing import List, Dict, Optional

# ---------
# Unified CSV schema
# ---------
CSV_FIELDS = [
    "source",        # e.g. al-akhbar, annahar
    "section",       # e.g. lebanon, whispers, politics
    "date",          # keep as string (site format) OR convert later
    "title",
    "url",
    "content",       # optional (empty if not available)
    "status",        # ok / failed
    "error",         # error message if failed
]


def load_module_from_path(path: str):
    """
    Load a .py module from file path, even if filename has '-' (not importable normally).
    """
    base = os.path.basename(path)
    mod_name = os.path.splitext(base)[0].replace("-", "_")  # safe name
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def normalize_item(source: str, item: dict) -> dict:
    """
    Make sure every row has the unified schema.
    """
    return {
        "source": source,
        "section": item.get("section", "") or "",
        "date": item.get("date", "") or "",
        "title": item.get("title", "") or "",
        "url": item.get("url", "") or "",
        "content": item.get("content", "") or "",
        "status": item.get("status", "ok") or "ok",
        "error": item.get("error", "") or "",
    }


def save_unified_csv(rows: List[Dict], out_dir: str = ".", filename: Optional[str] = None) -> str:

    day = datetime.now().strftime("%Y-%m-%d")
    if filename is None:
        filename = f"news_{day}.csv"
    out_path = os.path.join(out_dir, filename)

    # dedupe by url (keep first)
    seen = set()
    deduped = []
    for r in rows:
        u = r.get("url", "")
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(r)

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(deduped)

    print("✅ Saved unified CSV:", out_path)
    print("✅ Total unique rows:", len(deduped))
    return out_path


def run_all():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Running in Jupyter / Spyder
        here = os.getcwd()


    # Only run these scripts (edit this list whenever you add/remove sources)
    scripts = [
        "al-akhbar.py",
        "annahar.py",
        "almodon.py",
        "nidaa-elwatan.py",
        "jomhouriya.py",
    ]

    # Import YOUR driver creator from one place.
    # For now, reuse al-akhbar.open_driver() as the shared Selenium driver.
    # Later when you move to nodriver, you’ll swap this in one spot only.
    akhbar_path = os.path.join(here, "al-akhbar.py")
    akhbar_mod = load_module_from_path(akhbar_path)
    driver = akhbar_mod.open_driver()

    all_rows = []

    try:
        for fname in scripts:
            path = os.path.join(here, fname)
            if not os.path.exists(path):
                print("⚠️ Missing:", fname)
                continue

            mod = load_module_from_path(path)

            # source name = filename without extension
            source = os.path.splitext(fname)[0]

            if not hasattr(mod, "fetch"):
                print(f"⚠️ {fname} has no fetch(driver) — skipping")
                continue

            print("\n==============================")
            print("Running:", fname)
            print("==============================")

            try:
                items = mod.fetch(driver)  # must return list[dict]
                for it in items:
                    all_rows.append(normalize_item(source, it))
                print(f"✅ {fname}: {len(items)} items")
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                print("❌ Failed:", fname, err)

                # add one failed row so you can see it in the CSV
                all_rows.append(normalize_item(source, {
                    "section": "",
                    "date": "",
                    "title": "",
                    "url": "",
                    "content": "",
                    "status": "failed",
                    "error": err,
                }))
                # optional: print traceback for debugging
                traceback.print_exc()

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    save_unified_csv(all_rows, out_dir=here)


if __name__ == "__main__":
    run_all()
