import fetch_supply
import fetch_yield
import calculate_revenue
import append_history

def main():
    print("1/4 Fetching supply...")
    fetch_supply.main()

    print("2/4 Fetching T-Bill yield...")
    fetch_yield.main()

    print("3/4 Calculating revenue estimates...")
    calculate_revenue.main()

    print("4/4 Appending to history...")
    append_history.main()

    print("Pipeline complete.")

if __name__ == "__main__":
    main()

