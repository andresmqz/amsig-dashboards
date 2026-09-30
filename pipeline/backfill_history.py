import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import append_history

load_dotenv()
FRED_KEY = os.getenv("FRED_API_KEY")

START_DATE = "2025-01-01"
COIN_IDS = {"usdt_supply": 1, "usdc_supply": 2, "usde_supply": 146}
LLAMA_URL = "https://stablecoins.llama.fi/stablecoincharts/all"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def unix_to_date(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def fetch_supply_history(coin_id):
    response = requests.get(LLAMA_URL, params={"stablecoin": coin_id}, timeout=60)
    response.raise_for_status()
    history = {}
    for entry in response.json():
        date = unix_to_date(entry["date"])
        if date >= START_DATE:
            history[date] = entry["totalCirculating"]["peggedUSD"]
    return history


def fetch_rate_history():
    params = {
        "series_id": "DTB3",
        "api_key": FRED_KEY,
        "file_type": "json",
        "observation_start": START_DATE,
    }
    response = requests.get(FRED_URL, params=params, timeout=60)
    response.raise_for_status()
    rates = {}
    for obs in response.json()["observations"]:
        if obs["value"] != ".":
            rates[obs["date"]] = obs["value"]
    return rates


def main():
    supplies = {col: fetch_supply_history(cid) for col, cid in COIN_IDS.items()}
    rates = fetch_rate_history()

    existing = append_history.read_history()
    kept = {r["date"]: r for r in existing}

    all_dates = sorted(set().union(*[s.keys() for s in supplies.values()]))
    last_rate, last_rate_date = "", ""
    added = 0

    for date in all_dates:
        if date in rates:
            last_rate, last_rate_date = rates[date], date
        if date in kept:
            continue
        row = {col: "" for col in append_history.COLUMNS}
        row["date"] = date
        row["source"] = "backfill"
        for col, series in supplies.items():
            row[col] = series.get(date, "")
        row["tbill_rate_pct"] = last_rate
        row["tbill_date"] = last_rate_date
        kept[date] = row
        added += 1

    rows = sorted(kept.values(), key=lambda r: r["date"])
    append_history.write_history(rows)
    print(f"Backfill added {added} rows. File now has {len(rows)} rows.")


if __name__ == "__main__":
    main()