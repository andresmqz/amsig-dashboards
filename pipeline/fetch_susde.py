import csv
import json
import os
from datetime import datetime, timedelta, timezone

from web3 import Web3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "susde.json")
HISTORY_PATH = os.path.join(SCRIPT_DIR, "..", "data", "history", "daily.csv")

RPC_URL = os.getenv("ETH_RPC_URL", "https://ethereum-rpc.publicnode.com")
SUSDE_ADDRESS = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"
APY_WINDOW_DAYS = 7

# Minimal ABI: only the two read functions we call.
SUSDE_ABI = [
    {"name": "totalAssets", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "convertToAssets", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "shares", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
]


def fetch_onchain():
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 30}))
    contract = w3.eth.contract(address=SUSDE_ADDRESS, abi=SUSDE_ABI)
    staked = contract.functions.totalAssets().call() / 1e18
    rate = contract.functions.convertToAssets(10**18).call() / 1e18
    return staked, rate, w3.eth.block_number


def rate_days_ago(days):
    if not os.path.exists(HISTORY_PATH):
        return None
    target = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    with open(HISTORY_PATH, "r", newline="") as f:
        for row in csv.DictReader(f):
            if row["date"] == target and row.get("susde_exchange_rate"):
                return float(row["susde_exchange_rate"])
    return None


def main():
    staked, rate, block = fetch_onchain()
    old_rate = rate_days_ago(APY_WINDOW_DAYS)
    apy = None
    if old_rate:
        apy = (rate / old_rate) ** (365 / APY_WINDOW_DAYS) - 1

    record = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "block": block,
        "staked_usde": staked,
        "exchange_rate": rate,
        "apy_7d": apy,
    }
    with open(DATA_PATH, "w") as f:
        json.dump(record, f, indent=2)

    print(f"sUSDe staked: ${staked / 1e9:,.2f}B  rate: {rate:.6f}  block: {block}")
    print(f"7-day APY: {apy:.2%}" if apy is not None else "7-day APY: not enough history yet")


if __name__ == "__main__":
    main()