import fetch_supply
import fetch_yield
import calculate_revenue

def main():
    print("1/3 Fetching supply...")
    fetch_supply.main()

    print("2/3 Fetching T-Bill yield...")
    fetch_yield.main()

    print("3/3 Calculating revenue estimates...")
    calculate_revenue.main()

    print("Pipeline complete.")

if __name__ == "__main__":
    main()

