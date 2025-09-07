import time
import logging
import json
from selenium import webdriver
from bs4 import BeautifulSoup
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class WebDriver:
    def __init__(self, driver_type="chrome"):
        if driver_type == "chrome":
            self.driver = webdriver.Chrome()
        elif driver_type == "firefox":
            self.driver = webdriver.Firefox()
        else:
            raise ValueError(f"Unsupported browser type: {driver_type}")

    def open_page(self, url, retries=5):
        for _ in range(retries):
            try:
                self.driver.get(url)
                return
            except Exception as e:
                logger.warning(f"Error opening page {url}: {e}")
                self.refresh()
        raise Exception(f"Failed to open page {url}")

    def refresh(self):
        self.driver.quit()
        self.__init__()

    def scroll_down(self, delay=1):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(delay)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height


class Downloader:
    def __init__(self, web_driver, base_url="https://badap.agh.edu.pl"):
        self.WD = web_driver
        self.base_url = base_url
        self.authors = []
        self.author_ids = set()

    def get_users(self):
        self.WD.open_page(self.base_url + "/autorzy")
        self.WD.scroll_down()

        soup = BeautifulSoup(self.WD.driver.page_source, "lxml")
        rows = soup.find_all("a", class_="flex flex-row hover:bg-gray-100")

        for row in rows:
            divs = row.find_all("div")
            full_name = divs[0].text.strip()
            unit_raw = divs[1].text.strip() if len(divs) > 1 else "Unknown unit"
            num1 = divs[2].text.strip() if len(divs) > 2 else "0"
            num2 = divs[3].text.strip() if len(divs) > 3 else "0"

            if "-" in unit_raw:
                unit_main, unit_extra = unit_raw.split("-", 1)
            else:
                unit_main, unit_extra = unit_raw, None

            def parse_art_num(num):
                try:
                    return int(num.split(" ")[0])
                except (ValueError, IndexError):
                    return 0

            href = row["href"]
            match = re.search(r"/autor/.+?-([0-9]+)$", href)
            extracted_id = match.group(1) if match else None

            if extracted_id and extracted_id not in self.author_ids:
                self.author_ids.add(extracted_id)
                self.authors.append(
                    {
                        "id": extracted_id,
                        "full_name": full_name,
                        "unit": unit_main,
                        "subunit": unit_extra,
                        "link": self.base_url + href,
                        "art_num": parse_art_num(num1) + parse_art_num(num2),
                    }
                )

    def save_to_json(self, authors_file_path):
        with open(authors_file_path, "w", encoding="utf-8") as f:
            json.dump(self.authors, f, ensure_ascii=False, indent=4)

    def main(self):
        self.get_users()
        logger.info(f"Downloaded {len(self.authors)} authors.")
        self.save_to_json("data/raw/authors.json")
        logger.info("Data has been saved.")


def main():
    driver = WebDriver(driver_type="chrome")
    downloader = Downloader(web_driver=driver)
    try:
        downloader.main()
    finally:
        driver.driver.quit()


if __name__ == "__main__":
    main()
