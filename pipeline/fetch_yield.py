import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

import requests

load_dotenv()
API_KEY = os.getenv("FRED_API_KEY")

URL = "https://api.stlouisfed.org/fred/series/observations"

query_parameters = {
    'series_id': 'DTB3', 
    'api_key': API_KEY,
    'file_type': 'json',
    'sort_order': 'desc',
    'limit': 1
}

def fetch_yield():
    response = requests.get(URL, params=query_parameters, timeout=30)
    response.raise_for_status()
    return response.json()

def extract_yield(data):
    observation = data["observations"][0]
    rate_data = {
        "date": observation["date"],
        "value": observation["value"],
    }
    return rate_data

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "yield.json")

def save_yield(rate_data):
    record = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "yield": rate_data,
    }
    with open(DATA_PATH,"w") as f:
        json.dump(record,f,indent=2)

def main():
    data = fetch_yield()
    rate = extract_yield(data)
    save_yield(rate)

if __name__ == "__main__":
    main()