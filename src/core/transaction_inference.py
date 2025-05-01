from typing import Dict

class TransactionInference:
    """Infers the transaction type (buy/sell/hold) based on share differences."""

    def infer_transaction(self, previous_data: Dict, current_data: Dict) -> str:
        """
        Infers the transaction type based on the change in shares from previous to current quarter.

        Args:
            previous_data (Dict): The stock data from the previous quarter.
            current_data (Dict): The stock data from the current quarter.

        Returns:
            str: The inferred transaction type ('buy', 'sell', or 'hold').
        """
        previous_shares = previous_data["shares"]
        current_shares = current_data["shares"]

        if current_shares > previous_shares:
            return "buy"
        elif current_shares < previous_shares:
            return "sell"
        else:
            return "hold"
