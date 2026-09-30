import csv
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
HISTORY_PATH = os.path.join(HISTORY_DIR, "daily.csv")

COLUMNS = [
    "date", "source", "calculated_at",
    "usdt_supply", "usdc_supply", "usde_supply",
    "tbill_rate_pct", "tbill_date",
    "usdt_gross_interest",
    "usdc_reserve_income", "usdc_coinbase_share", "usdc_circle_retained",
    "usde_reserve_income", "usde_ethena_share", "usde_passed_to_holders",
]


def load_json(name):
    with open(os.path.join(DATA_DIR, name), "r") as f:
        return json.load(f)


def build_row():
    supply = load_json("supply.json")
    rate = load_json("yield.json")
    rev = load_json("revenue_calculation.json")
    return {
        "date": rev["calculated_at"][:10],
        "source": "daily",
        "calculated_at": rev["calculated_at"],
        "usdt_supply": supply["supply"]["USDT"],
        "usdc_supply": supply["supply"]["USDC"],
        "usde_supply": supply["supply"]["USDe"],
        "tbill_rate_pct": rate["yield"]["value"],
        "tbill_date": rate["yield"]["date"],
        "usdt_gross_interest": rev["USDT"]["gross_interest"],
        "usdc_reserve_income": rev["USDC"]["reserve_income"],
        "usdc_coinbase_share": rev["USDC"]["coinbase_share"],
        "usdc_circle_retained": rev["USDC"]["circle_retained"],
        "usde_reserve_income": rev["USDe"]["reserve_income"],
        "usde_ethena_share": rev["USDe"]["ethena_share"],
        "usde_passed_to_holders": rev["USDe"]["passed_to_holders"],
    }


def read_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", newline="") as f:
        return list(csv.DictReader(f))


def write_history(rows):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    new_row = build_row()
    rows = read_history()
    # Drop any existing row for the same date, so reruns replace instead of duplicate.
    rows = [r for r in rows if r["date"] != new_row["date"]]
    rows.append(new_row)
    rows.sort(key=lambda r: r["date"])
    write_history(rows)
    print(f"History: {len(rows)} rows, latest {new_row['date']}")


if __name__ == "__main__":
    main()