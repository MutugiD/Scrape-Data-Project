#!/usr/bin/env python3
"""
scraper_with_processor.py – unified version
Scrapes 13f.info managers, filings *and* every COM-row holding (duplicates kept)
using one reusable Selenium session.
"""

from __future__ import annotations
import json, pathlib, re, logging, time
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Globals & helpers
# ---------------------------------------------------------------------------
log = logging.getLogger("scraper")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_URL  = "https://13f.info"
CACHE_DIR = pathlib.Path("cache"); CACHE_DIR.mkdir(exist_ok=True)

def _load(path: pathlib.Path, default):
    return json.loads(path.read_text()) if path.exists() else default

# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------
class Scraper:
    def __init__(self, headless: bool = True):
        opts = Options()
        if headless:
            opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=opts
        )

        self.managers_cache: list[tuple[str, str]] = _load(CACHE_DIR / "managers.json", [])
        self.filings_cache : Dict[str, list[str]] = _load(CACHE_DIR / "filings.json",  {})
        self.holdings_cache: Dict[str, list[dict]] = _load(CACHE_DIR / "holdings.json", {})

    # ------------------------------------------------------------------ #
    # generic helpers
    # ------------------------------------------------------------------ #
    def _col_index(self, headers: List[str], aliases: List[str]) -> int:
        """Return the first header index that matches any alias (case-insensitive)."""
        headers_lower = [h.lower() for h in headers]
        for a in aliases:
            if a in headers_lower:
                return headers_lower.index(a)
        raise ValueError(f"Column not found – tried {aliases} – saw {headers}")

    # ------------------------------------------------------------------ #
    # 1) Managers list  -------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def scrape_fund_managers(self, limit: int = 10) -> list[tuple[str, str]]:
        if self.managers_cache:
            log.info("Loaded %d managers from cache", len(self.managers_cache))
            return self.managers_cache

        results: Dict[str, str] = {}
        for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
            url = f"{BASE_URL}/managers/{ch}/"
            log.info("Loading %s", url)
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/manager/']"))
            )

            for a in self.driver.find_elements(By.CSS_SELECTOR, "a[href^='/manager/']"):
                results[a.text.strip()] = a.get_attribute("href")

            if len(results) >= limit:
                break

        self.managers_cache = list(results.items())[:limit]
        (CACHE_DIR / "managers.json").write_text(json.dumps(self.managers_cache, indent=2))
        return self.managers_cache

    # ------------------------------------------------------------------ #
    # 2) Filings for one manager  --------------------------------------- #
    # ------------------------------------------------------------------ #
    def scrape_filings(self, manager_url: str) -> list[str]:
        """
        Return *all* quarters for which a 13F-HR was filed,
        walking through every DataTables page.
        """
        if manager_url in self.filings_cache:
            return self.filings_cache[manager_url]

        self.driver.get(manager_url)
        WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located((By.ID, "managerFilings"))
        )
        tbl = self.driver.find_element(By.ID, "managerFilings")

        quarters: list[str] = []
        page = 1
        while True:
            # -- scrape current table body -------------------------------- #
            for tr in tbl.find_elements(By.CSS_SELECTOR, "tbody tr"):
                tds = tr.find_elements(By.TAG_NAME, "td")
                if not tds or tds[4].text.strip() != "13F-HR":
                    continue
                label = tds[0].text.split("–")[0].strip()       # “Q4 2024”
                m = re.fullmatch(r"Q([1-4])\s+(\d{4})", label)
                if m:
                    q, yr = m.groups()
                    quarters.append(f"{yr}Q{q}")

            # -- move to next DataTables page ----------------------------- #
            try:
                next_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#managerFilings_paginate a.paginate_button.next"
                )
            except Exception:
                break  # paginator absent → single page

            if "disabled" in next_btn.get_attribute("class"):
                break  # last page

            next_btn.click()
            page += 1
            WebDriverWait(self.driver, 20).until(
                lambda drv: drv.find_element(
                    By.CSS_SELECTOR,
                    "#managerFilings_paginate a.paginate_button.current"
                ).text == str(page)
            )

        self.filings_cache[manager_url] = quarters
        (CACHE_DIR / "filings.json").write_text(
            json.dumps(self.filings_cache, indent=2)
        )
        log.info("Found %d quarters for %s", len(quarters), manager_url)
        return quarters

    # ------------------------------------------------------------------ #
    # 3) Holdings for one filing  --------------------------------------- #
    # ------------------------------------------------------------------ #
    def scrape_holdings(self, manager_url: str, quarter: str) -> List[dict]:
        """
        Returns **all COM rows** (duplicates preserved) as a list of dicts:
        [{stock_symbol, cl, value, shares}, …]
        """
        key = f"{manager_url}#{quarter}"
        if key in self.holdings_cache:
            return self.holdings_cache[key]

        # 3-a) find the “detail” link for the requested quarter
        self.driver.get(manager_url)
        WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located((By.ID, "managerFilings"))
        )
        detail_link = None
        for tr in self.driver.find_element(By.ID, "managerFilings")\
                             .find_elements(By.TAG_NAME, "tr")[1:]:
            tds = tr.find_elements(By.TAG_NAME, "td")
            if not tds:
                continue
            m = re.fullmatch(r"Q([1-4])\s+(\d{4})",
                             tds[0].text.split("–")[0].strip())
            if not m:
                continue
            q, yr = m.groups()
            if f"{yr}Q{q}" == quarter:
                detail_link = tds[0].find_element(By.TAG_NAME, "a").get_attribute("href")
                break
        if not detail_link:
            log.warning("No filing link for %s %s", manager_url, quarter)
            self.holdings_cache[key] = []
            (CACHE_DIR / "holdings.json").write_text(json.dumps(self.holdings_cache, indent=2))
            return []

        # 3-b) Open the filing page and wait for the first holdings table
        self.driver.get(detail_link)
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )
        except Exception:
            log.warning("No holdings table at %s", detail_link)
            self.holdings_cache[key] = []
            (CACHE_DIR / "holdings.json").write_text(json.dumps(self.holdings_cache, indent=2))
            return []

        tbl = self.driver.find_elements(By.TAG_NAME, "table")[0]

        # 3-c) Discover column indices dynamically
        hdr_cells = tbl.find_elements(By.CSS_SELECTOR, "thead tr th") or \
                    tbl.find_elements(By.CSS_SELECTOR, "thead tr td")
        headers = [h.text.strip().lower() for h in hdr_cells]

        idx_sym = self._col_index(headers, ["sym", "symbol", "stock"])
        idx_cl  = self._col_index(headers, ["cl", "class"])
        idx_val = self._col_index(headers, ["value ($000)", "value ($)", "value"])
        idx_shr = self._col_index(headers, ["shares"])

        # -- minimal-patch guard: skip rows that are too short ------------ #
        required_idx = max(idx_sym, idx_cl, idx_val, idx_shr)

        # 3-d) Iterate through all DataTables pages (duplicates kept)       #
        rows: List[dict] = []
        page = 1
        while True:
            for tr in tbl.find_elements(By.CSS_SELECTOR, "tbody tr"):
                td = tr.find_elements(By.TAG_NAME, "td")
                if len(td) <= required_idx:
                    continue                               # summary / subtotal
                if not td[idx_cl].text.upper().startswith("COM"):
                    continue

                # -- safe numeric parsing -------------------------------- #
                val_raw = td[idx_val].text.replace(",", "").replace("$", "").strip()
                shr_raw = td[idx_shr].text.replace(",", "").strip()
                try:
                    value  = float(val_raw)
                    shares = int(shr_raw)
                except ValueError:
                    # blank or non-numeric → skip this row
                    log.debug("Skipped non-numeric row: %s", [c.text for c in td])
                    continue

                rows.append({
                    "stock_symbol": td[idx_sym].text.strip(),
                    "cl":           "COM",
                    "value":        value,
                    "shares":       shares
                })

            # Click “Next” if available
            next_btn = self.driver.find_element(By.CSS_SELECTOR,
                                                "a.paginate_button.next")
            if "disabled" in next_btn.get_attribute("class"):
                break
            next_btn.click()
            page += 1
            WebDriverWait(self.driver, 20).until(
                lambda drv: drv.find_element(By.CSS_SELECTOR,
                                             "a.paginate_button.current").text == str(page)
            )
            time.sleep(0.15)   # small render pause; table element stays valid

        log.info("Scraped %d COM rows (%d page[s]) for %s %s",
                 len(rows), page, manager_url.split('/')[-2], quarter)

        # 3-e) Cache & return
        self.holdings_cache[key] = rows
        (CACHE_DIR / "holdings.json").write_text(json.dumps(self.holdings_cache, indent=2))
        return rows

    # ------------------------------------------------------------------ #
    def close(self):
        self.driver.quit()
