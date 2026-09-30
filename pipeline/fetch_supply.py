import json
import os
from datetime import datetime, timezone

import requests

URL = "https://stablecoins.llama.fi/stablecoins"
TARGETS = {"USDT", "USDC", "USDe"}
TOP_CHAINS = 5

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "supply.json")
CHAINS_PATH = os.path.join(SCRIPT_DIR, "..", "data", "supply_by_chain.json")


def fetch_stablecoins():
    response = requests.get(URL, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_supply(data):
    supply = {}
    for asset in data["peggedAssets"]:
        symbol = asset["symbol"]
        if symbol in TARGETS:
            supply[symbol] = asset["circulating"]["peggedUSD"]
    return supply


def chain_amount(entry, period):
    """Read one period ('current', 'circulatingPrevMonth') from a chain entry, 0 if missing."""
    return (entry.get(period) or {}).get("peggedUSD", 0) or 0


def extract_chains(data, top_n=TOP_CHAINS):
    chains = {}
    for asset in data["peggedAssets"]:
        symbol = asset["symbol"]
        if symbol not in TARGETS:
            continue
        rows = []
        for chain, entry in asset["chainCirculating"].items():
            rows.append({
                "chain": chain,
                "current": chain_amount(entry, "current"),
                "prev_month": chain_amount(entry, "circulatingPrevMonth"),
            })
        rows.sort(key=lambda r: r["current"], reverse=True)

        top = rows[:top_n]
        rest = rows[top_n:]
        top.append({
            "chain": "Other",
            "current": sum(r["current"] for r in rest),
            "prev_month": sum(r["prev_month"] for r in rest),
            "chain_count": len(rest),
        })

        total = sum(r["current"] for r in rows)
        for r in top:
            r["share"] = r["current"] / total if total else 0
            r["change_30d"] = (r["current"] / r["prev_month"] - 1) if r["prev_month"] else None
        chains[symbol] = {"total": total, "chains": top}
    return chains


def save_json(path, payload):
    record = {"fetched_at": datetime.now(timezone.utc).isoformat(), **payload}
    with open(path, "w") as f:
        json.dump(record, f, indent=2)


def main():
    data = fetch_stablecoins()

    supply = extract_supply(data)
    for symbol, amount in supply.items():
        print(f"{symbol}: ${amount/1e9:,.2f}B")
    save_json(DATA_PATH, {"supply": supply})

    chains = extract_chains(data)
    for symbol, info in chains.items():
        top = info["chains"][0]
        print(f"  {symbol} largest chain: {top['chain']} {top['share']:.1%}")
    save_json(CHAINS_PATH, {"by_chain": chains})

if __name__ == "__main__":
    main()