import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logging

import logging
import pandas as pd
from src.scraper.scraper import Scraper
from src.core.data_processor import DataProcessor
from src.core.transaction_inference import TransactionInference
from src.data_cleaning.data_cleaner import DataCleaner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize Scraper, DataProcessor, TransactionInference, and DataCleaner
    scraper = Scraper()
    data_processor = DataProcessor()
    transaction_inference = TransactionInference()
    data_cleaner = DataCleaner()

    # Step 1: Scrape fund managers
    base_url = "https://13f.info"
    logger.info(f"Starting to scrape fund managers from {base_url}")
    managers = scraper.scrape_fund_managers(base_url)
    logger.info(f"Found {len(managers)} fund managers.")

    all_data = []

    # Step 2: Scrape filings and holdings
    for manager_name, manager_url in managers:
        logger.info(f"Processing manager: {manager_name}")
        filings = scraper.scrape_filings(manager_url)
        logger.info(f"Found {len(filings)} filings for {manager_name}.")

        for filing in filings:
            logger.info(f"Scraping holdings for filing {filing}")
            holdings = scraper.scrape_holdings(filing)
            logger.info(f"Found {len(holdings)} holdings for {filing}")

            # Process and infer transaction types
            data = {}
            for stock_symbol, shares in holdings:
                previous_data = {"shares": 797683307}  # Example for previous quarter
                current_data = {"shares": shares}     # Current quarter data

                # Process data and infer transaction
                data[stock_symbol] = {
                    "previous_quarter": previous_data,
                    "current_quarter": current_data,
                }

            # Use DataProcessor to process data
            processed_data = data_processor.process_data(data)

            # Use TransactionInference to infer transaction types and clean data
            for entry in processed_data:
                previous_data = data[entry["stock_symbol"]]["previous_quarter"]
                current_data = data[entry["stock_symbol"]]["current_quarter"]
                transaction_type = transaction_inference.infer_transaction(previous_data, current_data)

                entry["inferred_transaction_type"] = transaction_type

            all_data.extend(processed_data)

    # Step 3: Convert the data to a DataFrame for cleaning and saving
    df = pd.DataFrame(all_data)

    # Step 4: Clean the data
    logger.info("Cleaning data...")
    cleaned_data = data_cleaner.clean_data(df)

    # Step 5: Save cleaned data to CSV
    data_cleaner.save_to_csv(cleaned_data, "data/scraped_and_cleaned_data.csv")

if __name__ == "__main__":
    main()
