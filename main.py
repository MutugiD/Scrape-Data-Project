#!/usr/bin/env python3
"""
main.py – full pipeline

1.  Scrape every manager on 13f.info   (optionally limit for testing)
2.  For each manager → scrape every 13F-HR quarter
3.  For each quarter → scrape **all COM rows**, aggregate by symbol
4.  Compare current-vs-previous quarter → change, % change, inferred txn
5.  Emit a single CSV:
       fund_name | filing_date | quarter | stock_symbol | cl
       value_($000) | shares | change | pct_change | inferred_transaction_type
"""

from __future__ import annotations
import csv, logging, re
from itertools import islice
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from scraper import Scraper   # ← your updated scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("main")

# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")

def qkey(q: str) -> Tuple[int, int]:
    """Return (year, quarter#) for sorting."""
    m = QUARTER_RE.match(q)
    if not m:
        raise ValueError(f"Bad quarter label: {q}")
    return (int(m.group(1)), int(m.group(2)))

def aggregate(rows: List[dict]) -> Dict[str, dict]:
    """
    Sum duplicate symbols inside one filing.  Returns
        { symbol: {"cl":..., "value": Σ, "shares": Σ} }
    """
    agg: Dict[str, dict] = defaultdict(lambda: {"cl": "COM", "value": 0.0, "shares": 0})
    for r in rows:
        sym = r["stock_symbol"]
        agg[sym]["value"]  += r["value"]
        agg[sym]["shares"] += r["shares"]
    return agg

def txn_type(prev_sh: int, cur_sh: int) -> str:
    if cur_sh > prev_sh:
        return "buy"
    if cur_sh < prev_sh:
        return "sell"
    return "hold"

# --------------------------------------------------------------------------- #
# main driver                                                                 #
# --------------------------------------------------------------------------- #
def main(
    out_csv: str = "scraped_fund_data.csv",
    manager_limit: Optional[int] = None,        # set e.g. 5 while testing
):
    scraper = Scraper(headless=True)
    rows: List[dict] = []

    # 1) managers ----------------------------------------------------------- #
    managers = scraper.scrape_fund_managers()
    if manager_limit:
        managers = list(islice(managers, manager_limit))

    # 2) loop managers ------------------------------------------------------ #
    for fund_name, mgr_url in managers:
        log.info("▶  %s", fund_name)
        quarters = scraper.scrape_filings(mgr_url)
        if not quarters:
            log.warning("No 13F-HR filings for %s", fund_name)
            continue

        # grab & aggregate every quarter’s holdings
        holdings_by_q: Dict[str, Dict[str, dict]] = {}
        for q in quarters:
            raw_rows = scraper.scrape_holdings(mgr_url, q)      # list[dict]
            holdings_by_q[q] = aggregate(raw_rows)

        # sort chronologically
        ordered_q = sorted(holdings_by_q, key=qkey)

        # 3) compare quarter-over-quarter ---------------------------------- #
        for i, cur_q in enumerate(ordered_q):
            cur_hold = holdings_by_q[cur_q]
            prev_hold = holdings_by_q[ordered_q[i - 1]] if i else {}

            # symbols that exist this quarter
            for sym, cdata in cur_hold.items():
                prev = prev_hold.get(sym, {"shares": 0})
                change = cdata["shares"] - prev["shares"]
                pct = (change / prev["shares"] * 100) if prev["shares"] else None
                rows.append({
                    "fund_name": fund_name,
                    "filing_date": cur_q,          # actual date not scraped, use label
                    "quarter": cur_q,
                    "stock_symbol": sym,
                    "cl": cdata["cl"],
                    "value_($000)": round(cdata["value"], 2),
                    "shares": cdata["shares"],
                    "change": change,
                    "pct_change": round(pct, 2) if pct is not None else None,
                    "inferred_transaction_type": txn_type(prev["shares"], cdata["shares"]),
                })

            # symbols that disappeared this quarter (full exit)
            if i:      # only if a previous quarter exists
                exited_syms = set(prev_hold) - set(cur_hold)
                for sym in exited_syms:
                    prev = prev_hold[sym]
                    rows.append({
                        "fund_name": fund_name,
                        "filing_date": cur_q,
                        "quarter": cur_q,
                        "stock_symbol": sym,
                        "cl": prev["cl"],
                        "value_($000)": 0,
                        "shares": 0,
                        "change": -prev["shares"],
                        "pct_change": -100.0,
                        "inferred_transaction_type": "sell",
                    })

    # 4) write CSV ---------------------------------------------------------- #
    if rows:
        cols = [
            "fund_name", "filing_date", "quarter", "stock_symbol", "cl",
            "value_($000)", "shares", "change", "pct_change",
            "inferred_transaction_type",
        ]
        with open(out_csv, "w", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        log.info("✅  Wrote %d rows → %s", len(rows), out_csv)
    else:
        log.warning("Nothing scraped – CSV not created")

    scraper.close()

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Use manager_limit while debugging to avoid multi-hour runs.
    main(manager_limit=20)
