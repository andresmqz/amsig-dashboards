import json
from datetime import datetime, timezone
import os

import requests

URL = "https://stablecoins.llama.fi/stablecoins"
TARGETS = {"USDT","USDC","USDe"}

def fetch_stablecoins():
    response = requests.get(URL,timeout=30)
    response.raise_for_status()
    return response.json()

def extract_supply(data):
    supply = {}
    for asset in data["peggedAssets"]:
        symbol = asset["symbol"]
        if symbol in TARGETS:
            supply[symbol] = asset["circulating"]["peggedUSD"]
    return supply


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "supply.json")

def save_supply(supply):
    record = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "supply": supply,
    }
    with open(DATA_PATH,"w") as f:
        json.dump(record,f,indent=2)

def main():
    data = fetch_stablecoins()
    supply = extract_supply(data)
    for symbol, amount in supply.items():
        print(f"{symbol}: ${amount/1e9:,.2f}B")
    save_supply(supply)

if __name__ == "__main__":
    main()
