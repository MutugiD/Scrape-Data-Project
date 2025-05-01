import logging
import time
import socket

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Postpone heavy imports until needed
from src.core.data_processor import DataProcessor
from src.core.transaction_inference import TransactionInference

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scraper:
    """Handles scraping of fund managers and their quarterly filings."""

    BASE_URL = "https://13f.info"

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

        # Configure headless Chrome with all GPU features disabled
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-webgl")
        chrome_options.add_argument("--disable-accelerated-2d-canvas")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        # Delay instantiating heavy inference objects until after scraping
        self.data_processor = None
        self.transaction_inference = None

    def scrape_fund_managers(self) -> list[tuple[str, str]]:
        """Scrapes the list of fund managers from the homepage."""
        try:
            self.driver.get(self.BASE_URL)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/manager/']"))
            )
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href^='/manager/']")
            managers = []
            for link in links:
                name = link.text.strip()
                href = link.get_attribute("href")
                managers.append((name, href))
            return managers

        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Failed to load manager list: {e}")
            return []

    def scrape_filings(self, manager_name: str, manager_url: str) -> list[str]:
        """Scrapes the quarterly filings table for a given manager."""
        # Only instantiate heavy objects here once we know we need them
        if self.data_processor is None:
            self.data_processor = DataProcessor()
            self.transaction_inference = TransactionInference()

        for attempt in range(self.max_retries):
            try:
                self.driver.get(manager_url)

                # Ensure the page and the correct table ID are present
                WebDriverWait(self.driver, 30).until(
                    EC.visibility_of_element_located((By.ID, "managerFilings"))
                )

                table = self.driver.find_element(By.ID, "managerFilings")
                rows = table.find_elements(By.TAG_NAME, "tr")

                filings = []
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if cols:
                        filings.append(cols[-1].text)  # e.g. Date Filed column

                return filings

            except (TimeoutException, WebDriverException, socket.error) as e:
                logger.error(f"[{manager_name}] Attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)  # exponential backoff
            except Exception as e:
                logger.error(f"[{manager_name}] Unexpected error: {e}")
                break

        logger.warning(f"[{manager_name}] All {self.max_retries} attempts failed.")
        return []

    def close(self):
        self.driver.quit()

