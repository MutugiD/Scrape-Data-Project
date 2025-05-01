import pandas as pd
import numpy as np

class DataCleaner:
    """DataCleaner class for cleaning and saving scraped datasets."""

    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the scraped data by handling missing values, duplicates, and incorrect data.

        Args:
            data (pd.DataFrame): The scraped data to be cleaned.

        Returns:
            pd.DataFrame: The cleaned data.
        """
        # Drop duplicates
        data = data.drop_duplicates()

        # Fill missing values (or drop rows/columns depending on the requirement)
        data = data.fillna(method='ffill')  # forward fill for missing data

        # Remove or replace any invalid data (e.g., negative share values)
        data = data[data['shares'] >= 0]

        # Optionally, convert data types for consistency (e.g., converting to int)
        data['shares'] = data['shares'].astype(int)

        return data

    def save_to_csv(self, data: pd.DataFrame, filename: str):
        """
        Saves the cleaned data to a CSV file.

        Args:
            data (pd.DataFrame): The cleaned data.
            filename (str): The name of the output CSV file.
        """
        data.to_csv(filename, index=False)
        print(f"Data saved to {filename}")

