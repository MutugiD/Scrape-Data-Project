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

# heavy imports delayed until after scraping
from src.core.data_processor import DataProcessor
from src.core.transaction_inference import TransactionInference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scraper:
    """Scrapes every manager page under /managers/[A–Z,0–9], then each manager's filings."""

    BASE_URL = "https://13f.info"

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

        # headless + disable all GPU/webgl
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--disable-webgl")
        opts.add_argument("--disable-accelerated-2d-canvas")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opts
        )

        # delay these until after we know we'll need them
        self.data_processor = None
        self.transaction_inference = None

    def scrape_fund_managers(self) -> list[tuple[str, str]]:
        """Iterate /managers/{a–z,0–9} pages and collect every <a href='/manager/...'>."""
        letters = [*"abcdefghijklmnopqrstuvwxyz", *"0123456789"]
        managers = {}
        for ch in letters:
            page = f"{self.BASE_URL}/managers/{ch}"
            logger.info(f"Loading manager list page: {page}")
            try:
                self.driver.get(page)
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/manager/']"))
                )
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[href^='/manager/']")
                for link in links:
                    name = link.text.strip()
                    href = link.get_attribute("href")
                    managers[href] = name
            except (TimeoutException, WebDriverException) as e:
                logger.error(f"Failed to load {page}: {e}")
                continue

        result = [(name, url) for url, name in managers.items()]
        logger.info(f"Collected {len(result)} managers across all letter pages.")
        return result

    def scrape_filings(self, manager_name: str, manager_url: str) -> list[str]:
        """Scrape the `#managerFilings` table of a single manager page."""
        # only instantiate these once we start scraping filings
        if self.data_processor is None:
            self.data_processor = DataProcessor()
            self.transaction_inference = TransactionInference()

        for attempt in range(1, self.max_retries + 1):
            try:
                self.driver.get(manager_url)
                WebDriverWait(self.driver, 30).until(
                    EC.visibility_of_element_located((By.ID, "managerFilings"))
                )
                table = self.driver.find_element(By.ID, "managerFilings")
                rows = table.find_elements(By.TAG_NAME, "tr")
                filings = []
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if cols:
                        # grab the “Date Filed” column (last <td>)
                        filings.append(cols[-1].text.strip())
                return filings

            except (TimeoutException, WebDriverException, socket.error) as e:
                logger.error(f"[{manager_name}] Attempt {attempt}/{self.max_retries} failed: {e}")
                time.sleep(2 ** (attempt - 1))
            except Exception as e:
                logger.error(f"[{manager_name}] Unexpected error: {e}")
                break

        logger.warning(f"[{manager_name}] All {self.max_retries} attempts failed.")
        return []

    def close(self):
        self.driver.quit()

