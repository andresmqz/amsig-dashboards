import json
import os

from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUPPLY_PATH = os.path.join(SCRIPT_DIR, "..", "data", "supply.json")
YIELD_PATH = os.path.join(SCRIPT_DIR, "..", "data", "yield.json")
RESERVES_PATH = os.path.join(SCRIPT_DIR, "..", "config", "reserves.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "data", "revenue_calculation.json")

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
    return_rate = usdc["reserve_return_rate_pct"]
    reserve_income = live_supply * usdc["reserve_return_rate_pct"]
    coinbase_ratio = usdc["of_which_paid_to_coinbase_usd"]/usdc["reserve_income_usd"]
    coinbase_share = reserve_income * coinbase_ratio
    return {
        "reserve_income": reserve_income,
        "coinbase_share":coinbase_share,
        "circle_retained": reserve_income - coinbase_share,
    }

def estimate_usde_revenue(supply,rate,reserves):
    usde = reserves["USDe"]
    """
    live_supply = supply["supply"]["USDe"]
    estimated_yield = usde["trailing_30d_fees_annualized_usd"]/usde["reference_supply_usd"]
    gross_revenue = live_supply * estimated_yield
    ethena_share = gross_revenue * usde["issuer_retained_share_pct"]
    """
    # Retained by Ethena: DeFiLlama's "Revenue" metric is mint fees + the
    # staking-rewards portion routed to the Reserve Fund. This IS the
    # retained figure directly — no derivation needed. Hand-entered
    # snapshot since it needs DeFiLlama Pro to export/fetch live.
    ethena_share = usde["revenue_30d_usd"] * (365 / 30)

    # Distributed to holders: staked sUSDe supply x current staking APY.
    # NOT derived from "Fees", which is gross yield across all backing,
    # not staker payout specifically (confirmed via DeFiLlama methodology).
    passed_to_holders = usde["susde_staked_usd"] * usde["susde_apy_pct"]

    gross_revenue = ethena_share + passed_to_holders
    return {
        "reserve_income": gross_revenue,
        "ethena_share": ethena_share,
        "passed_to_holders": passed_to_holders,
    }

def save_revenue(supply, rate, reserves, usdt, usdc, usde):
    record = {
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "supply_fetched_at": supply["fetched_at"],
            "yield_fetched_at": rate["fetched_at"],
            "yield_observation_date": rate["yield"]["date"],
            "USDT_reserves_as_of": reserves["USDT"]["as_of"],
            "USDC_reserves_as_of": reserves["USDC"]["as_of"],
            "USDe_reserves_as_of": reserves["USDe"]["as_of"],
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
    
    usdt = estimate_usdt_revenue(supply,rate,reserves)
    print(f"USDT estimated annual gross interest: ${usdt/1e9:,.2f}B")
    usdc = estimate_usdc_revenue(supply,rate,reserves)
    print(f"USDC reserve income (annual): ${usdc['reserve_income']/1e9:,.2f}B")
    print(f"  to Coinbase: ${usdc['coinbase_share']/1e9:,.2f}B")
    print(f"  retained by Circle: ${usdc['circle_retained']/1e9:,.2f}B")
    usde = estimate_usde_revenue(supply,rate,reserves)
    print(f"USDe reserve income (annual): ${usde['reserve_income']/1e6:,.2f}M")
    print(f"  Retained by Ethena: ${usde['ethena_share']/1e6:,.2f}M")
    print(f"  Distributed to holders: ${usde['passed_to_holders']/1e6:,.2f}M")
    
    save_revenue(supply, rate, reserves, usdt, usdc, usde)

if __name__ == "__main__":
    main()