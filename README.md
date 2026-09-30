# Amsig Labs · Signal pipeline

The data pipeline behind [Signal](https://www.amsiglabs.com/signal), the live instruments section of Amsig Labs.

Each Amsig report is dated and fixed. A Signal instrument reruns that report's model every morning on fresh data and keeps the original analysis beside it, so readers can see whether the thesis still holds. This repository fetches the data, runs the model and commits the results. The website reads them from here.

**Live instrument:** [No. 01 · Stablecoin Revenue](https://www.amsiglabs.com/signal/stablecoin-revenue), which asks who keeps the yield on USDT, USDC and USDe.

## What it does

Every day at 05:17 UTC, a GitHub Actions workflow runs five steps:

| Step | Script | Output |
| --- | --- | --- |
| 1. Circulating supply, total and by chain | `pipeline/fetch_supply.py` | `data/supply.json`, `data/supply_by_chain.json` |
| 2. 3-month Treasury bill rate | `pipeline/fetch_yield.py` | `data/yield.json` |
| 3. sUSDe staked supply and exchange rate, read on-chain | `pipeline/fetch_susde.py` | `data/susde.json` |
| 4. Annualized revenue estimates per issuer | `pipeline/calculate_revenue.py` | `data/revenue_calculation.json` |
| 5. One row appended to the daily history | `pipeline/append_history.py` | `data/history/daily.csv` |

`pipeline/run_all.py` runs them in order and stops at the first failure, so a broken source never produces a partial update.

## Sources

- **DefiLlama** stablecoin API: circulating supply, total and per chain.
- **FRED**, series DTB3: 3-month Treasury bill rate.
- **Ethereum**, sUSDe contract `0x9D39A5DE30e57443BfF2A8307A4256c8797A3497`: `totalAssets()` and `convertToAssets()`.
- **Quarterly disclosures**, hand-entered with source and date in `config/reserves.json`: Tether attestations (BDO Italia), Circle quarterly results, Coinbase 10-Q, DeFiLlama protocol revenue for Ethena.

## Method

- **Tether.** The earning base is Treasury bills plus overnight and term repo from the latest attestation, scaled to live supply. It assumes the reserve mix holds between attestations. Gold, bitcoin, equities and loans are excluded. The rate is a trailing 30-day average of the 3-month bill, which runs above what Tether actually realizes.
- **Circle.** Live supply times Circle's disclosed reserve return rate. Coinbase's share is its reported stablecoin revenue divided by Circle's reserve income for the same quarter. It is approximate, because the two figures come from different filers. Retained income is before Circle's operating costs.
- **Ethena.** DeFiLlama separates fees (gross yield on all backing) from revenue (what Ethena keeps). Ethena's share uses revenue. Holder payout is staked USDe read on-chain times the realized 7-day APY, derived from the sUSDe exchange rate. Until seven days of rate history exist, the APY falls back to the rate in the config.

All revenue figures are model estimates, not disclosed results.

## Data

`data/history/daily.csv` holds one row per day from January 2025.

- **Rows marked `backfill`** were reconstructed once from DefiLlama and FRED history. Only the supply and rate columns are filled.
- **Rows marked `daily`** were recorded by the pipeline and have every column.

Revenue is not backfilled. Doing so would mean applying today's disclosures to past quarters.

## Editorial files

- `config/reserves.json`: quarterly disclosures, each with its source and `as_of` date. Updated by hand when a new filing lands.
- `config/headlines.json`: optional hand-written headlines for the instrument page, each with an expiry date. When an entry expires or is absent, the page generates its own headline from the data.

## Running it locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "FRED_API_KEY=your_key" > .env
python pipeline/run_all.py
```

A free FRED key is available at fred.stlouisfed.org. The Ethereum read uses a public RPC; set `ETH_RPC_URL` to use your own.

## Limits

- Scaling reserves to live supply assumes the reserve mix is unchanged since the last attestation.
- A single model rate stands in for the rates each issuer actually earns.
- Supply on a chain shows where tokens sit, not why. Incentive programs can move it quickly.

---

Built and maintained by [Andrés Márquez](https://www.amsiglabs.com/about) · Amsig Labs · Independent research, not investment advice.