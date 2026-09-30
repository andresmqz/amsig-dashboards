import fetch_supply
import fetch_yield
import fetch_susde
import calculate_revenue
import append_history

def main():
    print("1/5 Fetching supply...")
    fetch_supply.main()

    print("2/5 Fetching T-Bill yield...")
    fetch_yield.main()

    print("3/5 Reading sUSDe on-chain...")
    fetch_susde.main()

    print("4/5 Calculating revenue estimates...")
    calculate_revenue.main()

    print("5/5 Appending to history...")
    append_history.main()

    print("Pipeline complete.")

if __name__ == "__main__":
    main()

