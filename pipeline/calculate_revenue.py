import json
import os

from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPPLY_PATH = os.path.join(SCRIPT_DIR, "..", "data", "supply.json")
YIELD_PATH = os.path.join(SCRIPT_DIR, "..", "data", "yield.json")
RESERVES_PATH = os.path.join(SCRIPT_DIR, "..", "config", "reserves.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "data", "revenue_calculation.json")
SUSDE_PATH = os.path.join(SCRIPT_DIR, "..", "data", "susde.json")

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def estimate_usdt_revenue(supply,rate,reserves):
    usdt = reserves["USDT"]
    assets = usdt["assets"]
    #only includes earning base of reserves, excludes other categories
    earning_base = (assets["us_treasury_bills_usd"]+assets["overnight_reverse_repo_usd"]+assets["term_reverse_repo_usd"]+assets["non_us_treasury_bills_usd"])
    live_supply = supply["supply"]["USDT"]
    scale = live_supply/usdt["tokens_issued_usd"]
    tbill_rate = float(rate["yield"]["value"])/100
    return earning_base * scale * tbill_rate

def estimate_usdc_revenue(supply,rate,reserves):
    usdc = reserves["USDC"]
    live_supply = supply["supply"]["USDC"]
    reserve_income = live_supply * usdc["reserve_return_rate_pct"]
    coinbase_ratio = usdc["of_which_paid_to_coinbase_usd"]/usdc["reserve_income_usd"]
    coinbase_share = reserve_income * coinbase_ratio
    return {
        "reserve_income": reserve_income,
        "coinbase_share":coinbase_share,
        "circle_retained": reserve_income - coinbase_share,
    }

def estimate_usde_revenue(supply, rate, reserves, susde):
    usde = reserves["USDe"]

    # Ethena's retained share: DeFiLlama Revenue metric, annualized (config snapshot).
    ethena_share = usde["revenue_30d_usd"] * (365 / 30)

    # Holder payout: live staked USDe (on-chain) x realized 7-day APY.
    # Falls back to the config APY until 7 days of exchange-rate history exist.
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

def save_revenue(supply, rate, reserves, susde, usdt, usdc, usde):
    record = {
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "supply_fetched_at": supply["fetched_at"],
            "yield_fetched_at": rate["fetched_at"],
            "yield_observation_date": rate["yield"]["date"],
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
    
    usdt = estimate_usdt_revenue(supply,rate,reserves)
    print(f"USDT estimated annual gross interest: ${usdt/1e9:,.2f}B")
    usdc = estimate_usdc_revenue(supply,rate,reserves)
    print(f"USDC reserve income (annual): ${usdc['reserve_income']/1e9:,.2f}B")
    print(f"  to Coinbase: ${usdc['coinbase_share']/1e9:,.2f}B")
    print(f"  retained by Circle: ${usdc['circle_retained']/1e9:,.2f}B")
    usde = estimate_usde_revenue(supply,rate,reserves,susde)
    print(f"USDe reserve income (annual): ${usde['reserve_income']/1e6:,.2f}M")
    print(f"  Retained by Ethena: ${usde['ethena_share']/1e6:,.2f}M")
    print(f"  Distributed to holders: ${usde['passed_to_holders']/1e6:,.2f}M")
    print(f"  sUSDe staked: ${usde['susde_staked']/1e9:,.2f}B ({usde['staked_share_of_supply']:.1%} of supply), APY {usde['apy_used']:.2%} [{usde['apy_source']}]")

    save_revenue(supply, rate, reserves, susde, usdt, usdc, usde)

if __name__ == "__main__":
    main()