# Scrape-Data-Project

## Overview

This framework is designed to scrape quarterly 13F-HR filings for fund managers from the website [13f.info](https://13f.info). It processes the filings to infer stock transaction types (buy, sell, or hold) based on changes in shares between consecutive quarters. The system generates a final CSV that summarizes the data, including the inferred transaction type, stock symbols, shares, value, and more.

## Features

* **Scrapes Fund Manager Data**: Fetches data on fund managers from the 13f.info website.
* **Processes Filings**: Scrapes and processes quarterly 13F-HR filings, comparing share changes between quarters.
* **Infers Transaction Types**: Based on share changes (buy, sell, or hold).
* **Generates CSV**: Outputs the processed data as a structured CSV file with the required columns.

## Structure

The project is structured as a Python package with the following components:

1. **`src/`**: Contains core logic, including data processing and transaction inference.
2. **`sdk/`**: The main client interface for interacting with the scraper functionality.
3. **`data_cleaning/`**: Contains logic for cleaning and saving scraped data.
4. **`tests/`**: Unit tests for the various modules of the framework.
5. **`common/`**: Utilities like logging.

## Installation

### Requirements

* Python 3.7 or above
* The following Python libraries:

  * `requests`
  * `beautifulsoup4`
  * `selenium`
  * `webdriver-manager`
  * `pandas`

### Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/mutugid/scrape-data-project.git
   cd scrape-data-project
   ```

2. **Install dependencies**:

   **Use a virtual environment** to manage dependencies:

   ```bash
   python -m venv gomans
   source venv/bin/activate
   #Windows
   .\gomans\Scripts\activate
   # use setup.py
   pip install .
   ```

3. **Running the Scraper**:

   To scrape data, simply run:

   ```bash
   python main.py
   ```

## Configuration

You can customize certain parts of the scraping process by editing the `scraper.py` file located in the `src/client/` directory.

### Base URL

The base URL for scraping fund managers is set to `https://13f.info`.

### Logging

The project uses Python’s built-in `logging` module. Logs appear in the console by default; adjust settings in `src/common/logging.py` to log elsewhere or change levels.

## Data Processing

### Data Processor

The `DataProcessor` class (`src/core/data_processor.py`) calculates share changes and percentage changes for each stock between quarters.

### Transaction Inference

The `TransactionInference` class (`src/core/transaction_inference.py`) infers “buy”, “sell”, or “hold” based on those share changes.

## Final Output

The final CSV contains:

* `fund_name`
* `filing_date`
* `quarter`
* `stock_symbol`
* `cl` (stock class, e.g., `COM`)
* `value_($000)`
* `shares`
* `change`
* `pct_change`
* `inferred_transaction_type` (`buy`, `sell`, `hold`)

## Microservice Architecture

* **Web Scraping Service**
* **Data Comparison & Inference Service**
* **Data Storage Service**
* **CSV Export Service**
* **Logging & Monitoring Service**

## Error Handling

The scraper retries failed pages (up to 3 times) and logs detailed errors for debugging.

## Tests

Run unit tests with:

```bash
pytest tests/
```

## Docker

Build and run with Docker:

```bash
docker build -t scrape-data-project .
docker run -it scrape-data-project
```

## CI/CD Integration

GitHub Actions pipeline (`.github/workflows/ci.yml`) includes:

* `flake8` linting
* `mypy` type checking
* `pytest` test runs

## License

MIT License

## Contributions

Feel free to open issues and submit pull requests!

---

### Acknowledgements

* Uses **BeautifulSoup** for HTML parsing
* Uses **Selenium** for dynamic content
* Thanks to the open-source community for their contributions
