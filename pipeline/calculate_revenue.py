import csv
import json
import os
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPPLY_PATH = os.path.join(SCRIPT_DIR, "..", "data", "supply.json")
YIELD_PATH = os.path.join(SCRIPT_DIR, "..", "data", "yield.json")
SUSDE_PATH = os.path.join(SCRIPT_DIR, "..", "data", "susde.json")
RESERVES_PATH = os.path.join(SCRIPT_DIR, "..", "config", "reserves.json")
HISTORY_PATH = os.path.join(SCRIPT_DIR, "..", "data", "history", "daily.csv")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "data", "revenue_calculation.json")

TRAILING_DAYS = 30


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def trailing_tbill_rate(days=TRAILING_DAYS):
    """Average 3M T-bill rate over the last `days` rows of the history file.
    Weekends carry the prior business day's rate, so this is time-weighted."""
    if not os.path.exists(HISTORY_PATH):
        return None, 0
    with open(HISTORY_PATH, "r", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["tbill_rate_pct"]]
    recent = rows[-days:]
    if len(recent) < 10:
        return None, len(recent)
    values = [float(r["tbill_rate_pct"]) for r in recent]
    return sum(values) / len(values) / 100, len(values)


def estimate_usdt_revenue(supply, reserves, tbill_rate):
    usdt = reserves["USDT"]
    assets = usdt["assets"]
    # Earning base: bills and repo only; gold, BTC, equities, loans excluded.
    earning_base = (assets["us_treasury_bills_usd"] + assets["overnight_reverse_repo_usd"]
                    + assets["term_reverse_repo_usd"] + assets["non_us_treasury_bills_usd"])
    # Scale to live supply; assumes reserve mix holds between attestations.
    scale = supply["supply"]["USDT"] / usdt["tokens_issued_usd"]
    return earning_base * scale * tbill_rate


def estimate_usdc_revenue(supply, reserves):
    usdc = reserves["USDC"]
    reserve_income = supply["supply"]["USDC"] * usdc["reserve_return_rate_pct"]
    # Approximate: Coinbase's reported stablecoin revenue over Circle's reserve income.
    coinbase_ratio = usdc["of_which_paid_to_coinbase_usd"] / usdc["reserve_income_usd"]
    coinbase_share = reserve_income * coinbase_ratio
    return {
        "reserve_income": reserve_income,
        "coinbase_share": coinbase_share,
        "circle_retained": reserve_income - coinbase_share,
    }


def estimate_usde_revenue(supply, reserves, susde):
    usde = reserves["USDe"]
    # Ethena's retained share: DeFiLlama Revenue metric, annualized (config snapshot).
    ethena_share = usde["revenue_30d_usd"] * (365 / 30)
    # Holder payout: live staked USDe (on-chain) x realized 7-day APY,
    # falling back to the config APY until 7 days of exchange-rate history exist.
    staked = susde["staked_usde"]
    if susde["apy_7d"] is not None:
        apy, apy_source = susde["apy_7d"], "onchain_7d"
    else:
        apy, apy_source = usde["susde_apy_pct"], "config_snapshot"
    passed_to_holders = staked * apy
    return {
        "reserve_income": ethena_share + passed_to_holders,
        "ethena_share": ethena_share,
        "passed_to_holders": passed_to_holders,
        "susde_staked": staked,
        "staked_share_of_supply": staked / supply["supply"]["USDe"],
        "apy_used": apy,
        "apy_source": apy_source,
    }


def save_revenue(supply, rate, reserves, susde, rate_info, usdt, usdc, usde):
    record = {
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "supply_fetched_at": supply["fetched_at"],
            "yield_fetched_at": rate["fetched_at"],
            "yield_observation_date": rate["yield"]["date"],
            "tbill_spot_pct": rate_info["spot"],
            "tbill_rate_used_pct": rate_info["used"],
            "tbill_rate_basis": rate_info["basis"],
            "USDT_reserves_as_of": reserves["USDT"]["as_of"],
            "USDC_reserves_as_of": reserves["USDC"]["as_of"],
            "USDe_reserves_as_of": reserves["USDe"]["as_of"],
            "susde_fetched_at": susde["fetched_at"],
        },
        "USDT": {"gross_interest": usdt},
        "USDC": usdc,
        "USDe": usde,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(record, f, indent=2)


def main():
    supply = load_json(SUPPLY_PATH)
    rate = load_json(YIELD_PATH)
    reserves = load_json(RESERVES_PATH)
    susde = load_json(SUSDE_PATH)

    # Rate for USDT: trailing average if enough history, else the spot rate.
    spot_rate = float(rate["yield"]["value"]) / 100
    avg_rate, n_days = trailing_tbill_rate()
    if avg_rate is not None:
        tbill_rate, basis = avg_rate, f"trailing_{n_days}d_avg"
    else:
        tbill_rate, basis = spot_rate, "spot"
    rate_info = {"spot": spot_rate, "used": tbill_rate, "basis": basis}

    usdt = estimate_usdt_revenue(supply, reserves, tbill_rate)
    print(f"USDT estimated annual gross interest: ${usdt/1e9:,.2f}B  (rate {tbill_rate:.2%}, {basis})")

    usdc = estimate_usdc_revenue(supply, reserves)
    print(f"USDC reserve income (annual): ${usdc['reserve_income']/1e9:,.2f}B")
    print(f"  to Coinbase: ${usdc['coinbase_share']/1e9:,.2f}B")
    print(f"  retained by Circle: ${usdc['circle_retained']/1e9:,.2f}B")

    usde = estimate_usde_revenue(supply, reserves, susde)
    print(f"USDe reserve income (annual): ${usde['reserve_income']/1e6:,.2f}M")
    print(f"  Retained by Ethena: ${usde['ethena_share']/1e6:,.2f}M")
    print(f"  Distributed to holders: ${usde['passed_to_holders']/1e6:,.2f}M")
    print(f"  sUSDe staked: ${usde['susde_staked']/1e9:,.2f}B ({usde['staked_share_of_supply']:.1%} of supply), "
          f"APY {usde['apy_used']:.2%} [{usde['apy_source']}]")

    save_revenue(supply, rate, reserves, susde, rate_info, usdt, usdc, usde)

if __name__ == "__main__":
    main()