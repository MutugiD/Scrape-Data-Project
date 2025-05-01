from typing import Dict

class DataProcessor:
    """Processes scraped data and prepares it for analysis."""

    def process_data(self, data: Dict) -> Dict:
        """
        Processes the stock data to calculate the change in shares and percentage change.

        Args:
            data (Dict): A dictionary containing stock data from different quarters.

        Returns:
            Dict: A dictionary with the calculated change and percentage change.
        """
        processed_data = []

        for stock_symbol, stock_data in data.items():
            # Extract previous and current quarter data
            previous_quarter = stock_data.get("previous_quarter")
            current_quarter = stock_data.get("current_quarter")

            if previous_quarter and current_quarter:
                # Calculate the change in shares and the percentage change
                change = current_quarter["shares"] - previous_quarter["shares"]
                pct_change = (change / previous_quarter["shares"]) * 100 if previous_quarter["shares"] > 0 else 0

                # Append processed data
                processed_data.append({
                    "stock_symbol": stock_symbol,
                    "previous_shares": previous_quarter["shares"],
                    "current_shares": current_quarter["shares"],
                    "change": change,
                    "pct_change": pct_change,
                })

        return processed_data
