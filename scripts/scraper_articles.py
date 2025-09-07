import time
import logging
import json
import random
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, NavigableString
import xml.etree.ElementTree as ET
import os


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class BADAPDownloader:
    def __init__(self, web_driver=None, base_url="https://badap.agh.edu.pl", output_file="data/raw/articles.json"):
        if web_driver is None:
            options = Options()
            self.WD = webdriver.Chrome(options=options)
            self.should_close_driver = True
        else:
            self.WD = web_driver
            self.should_close_driver = False
            
        self.base_url = base_url
        self.output_file = output_file

        self.articles = []
        self.article_ids = set()

        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    self.articles = json.load(f)
                    self.article_ids = {str(item["id"]) for item in self.articles if "id" in item}
                logger.info(f"Loaded {len(self.articles)} existing articles from {output_file}")
            except Exception as e:
                logger.error(f"Error loading existing articles: {e}")
        
    def __del__(self):
        if hasattr(self, 'WD') and self.should_close_driver:
            try:
                self.WD.quit()
                logger.info("WebDriver closed")
            except:
                pass
                
    def save_to_json(self):
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved {len(self.articles)} articles to {self.output_file}")
        
    def get_article_details(self, article_url):
        try:
            self.WD.get(article_url)
            time.sleep(random.uniform(0.3, 0.7))
            
            soup = BeautifulSoup(self.WD.page_source, "lxml")

            match = re.search(r'/publikacja/([0-9]+)$', article_url)
            article_id = match.group(1) if match else None
            
            if not article_id:
                logger.warning(f"Failed to extract ID from {article_url}")
                return None

            title_span = soup.find("span", {"title": "tytuł równoległy"}) or soup.find("span", {"title": "tytuł"})
            title = title_span.get_text(strip=True) if title_span else "No title"
            
            abstract_section = soup.find('h2', string='Abstract')
            abstract = abstract_section.find_next("blockquote").get_text(strip=True) if abstract_section else "No abstract"
            
            authors_section = None
            for h2_tag in soup.find_all('h2'):
                h2_text = h2_tag.get_text(strip=True)
                if re.search(r'\bAutor(?:zy)?\b', h2_text):
                    authors_section = h2_tag
                    break
                    
            authors_ids = []
            if authors_section:
                authors_list = authors_section.find_next_sibling("ul")
                if authors_list:
                    authors_li = authors_list.find_all("li")
                    for author_li in authors_li:
                        author_link_element = author_li.find("a")
                        if author_link_element:
                            author_link = author_link_element["href"]
                            match = re.search(r'/autor/.+?-([0-9]+)$', author_link)
                            author_id = match.group(1) if match else None
                            if author_id:
                                authors_ids.append(author_id)
                else:
                    logger.warning(f"Authors list not found in {article_url}")
            else:
                logger.warning(f"Author section not found in {article_url}")
                
            keywords_section = soup.find('h2', string='Słowa kluczowe')
            keywords = []
            
            if keywords_section:
                keywords_div = keywords_section.find_next("div")
                if keywords_div:
                    en_label = keywords_div.find(string='EN:')
                    if en_label:
                        current = en_label.next_sibling
                        while current:
                            if isinstance(current, NavigableString):
                                current = current.next_sibling
                                continue
                            elif current.name == 'a':
                                keyword_text = current.get_text(strip=True)
                                keywords.append(keyword_text)
                            elif current.name == 'div':
                                pl_label = current.find('span', string=re.compile('PL'))
                                if pl_label:
                                    break
                                else:
                                    current = current.next_sibling
                                    continue
                            else:
                                current = current.next_sibling
                    else:
                        for child in keywords_div.children:
                            if isinstance(child, NavigableString):
                                continue
                            elif child.name == 'a':
                                keywords.append(child.get_text(strip=True))
                            elif child.name == 'div':
                                pl_label = child.find('span', string=re.compile('PL'))
                                if pl_label:
                                    break
                            else:
                                continue
                else:
                    logger.warning(f"Keywords section not found in {article_url}")
            else:
                logger.warning(f"Keywords header not found in {article_url}")
                
            publication_year = None
            publication_type = None
            bibliometric_section = soup.find('h2', string='Dane bibliometryczne')
            
            if bibliometric_section:
                table = bibliometric_section.find_next("table")
                if table:
                    rows = table.find_all("tr")
                    for row in rows:
                        th = row.find("th")
                        td = row.find("td")
                        if th and td:
                            header = th.get_text(strip=True)
                            value = td.get_text(strip=True)
                            if header == "Rok publikacji":
                                publication_year = value
                            elif header == "Typ publikacji":
                                publication_type = value
                else:
                    logger.warning(f"Bibliometric data not found in {article_url}")
            else:
                logger.warning(f"Bibliometric section not found in {article_url}")
                
            return {
                "id": article_id,
                "url": article_url,
                "title": title,
                "abstract": abstract,
                "authors": authors_ids,
                "keywords": keywords,
                "publication_year": publication_year,
                "publication_type": publication_type,
            }
            
        except Exception as e:
            logger.error(f"Error parsing article {article_url}: {e}")
            return None
            
    def get_urls_from_sitemap(self):
        sitemap_index_url = f"{self.base_url}/bpp_sitemap.xml"
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        
        try:
            response = requests.get(sitemap_index_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error retrieving sitemap index: {response.status_code}")
                return []
                
            root = ET.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            sitemap_urls = [elem.text for elem in root.findall('ns:sitemap/ns:loc', namespace)]
            logger.info(f"Retrieved {len(sitemap_urls)} sitemap files.")
            
            publication_urls = []
            for sitemap_url in sitemap_urls:
                if 'publication_pages' in sitemap_url:
                    logger.info(f"Getting URLs from sitemap: {sitemap_url}")
                    response = requests.get(sitemap_url, headers=headers)
                    if response.status_code != 200:
                        logger.warning(f"Error retrieving {sitemap_url}: {response.status_code}")
                        continue
                        
                    sitemap_root = ET.fromstring(response.content)
                    urls = [elem.text for elem in sitemap_root.findall('ns:url/ns:loc', namespace)]
                    publication_urls.extend(urls)
                    logger.info(f"Retrieved {len(urls)} URLs from {sitemap_url}")
                    
            logger.info(f"Retrieved a total of {len(publication_urls)} publication URLs.")
            return publication_urls
            
        except Exception as e:
            logger.error(f"Error retrieving URLs from sitemap: {e}")
            return []
            
    def get_urls_by_dynamic_scrolling(self):
        publication_urls = []
        try:
            self.WD.get(f"{self.base_url}/publikacje")
            time.sleep(2) 
            
            previous_height = self.WD.execute_script("return document.body.scrollHeight")
            stop_attempts = 0
            
            while stop_attempts < 10:
                logger.info(f"Scrolling page... Articles found: {len(publication_urls)}")
                self.WD.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                soup = BeautifulSoup(self.WD.page_source, "lxml")
                articles = soup.find_all("a", href=re.compile(r'/publikacja/\d+'))
                
                new_articles = 0
                for article in articles:
                    article_url = article['href']
                    full_url = f"{self.base_url}{article_url}" if article_url.startswith('/') else article_url
                    
                    if full_url not in publication_urls:
                        publication_urls.append(full_url)
                        new_articles += 1
                        
                logger.info(f"Added {new_articles} new articles")

                new_height = self.WD.execute_script("return document.body.scrollHeight")
                if new_height == previous_height:
                    if new_articles == 0:
                        stop_attempts += 1
                        logger.warning(f"No new articles in this iteration. Attempt {stop_attempts}/10")
                    else:
                        stop_attempts = 0
                else:
                    stop_attempts = 0
                    
                previous_height = new_height
                
            logger.info(f"Dynamic scrolling completed. Found articles: {len(publication_urls)}")
            return publication_urls
            
        except Exception as e:
            logger.error(f"Error retrieving URLs by dynamic scrolling: {e}")
            return publication_urls
            
    def download_articles_from_sitemap(self):
        publication_urls = self.get_urls_from_sitemap()
        
        if not publication_urls:
            logger.error("Failed to retrieve publication URLs from sitemap.")
            return 0
            
        return self._download_articles(publication_urls)
    
    def download_articles_by_scrolling(self):
        publication_urls = self.get_urls_by_dynamic_scrolling()
        
        if not publication_urls:
            logger.error("Failed to retrieve publication URLs by scrolling.")
            return 0
            
        return self._download_articles(publication_urls)
    
    def download_articles_by_id_range(self, max_id=150000, batch_size=1000, save_interval=50):

        total_processed = 0
        total_saved = 0
        failed_consecutive = 0
        max_consecutive_failures = 100  
        logger.info(f"Starting download of articles with IDs up to {max_id}")
        
        current_id = max_id
        
        while current_id > 0:
            batch_start = max(1, current_id - batch_size + 1)
            batch_end = current_id
            
            logger.info(f"Processing batch of IDs from {batch_start} to {batch_end}")
            
            for article_id in range(batch_end, batch_start - 1, -1):
                try:
                    if str(article_id) in self.article_ids:
                        logger.info(f"Article ID {article_id} already processed, skipping")
                        continue
                    
                    article_url = f"{self.base_url}/publikacja/{article_id}"
                    logger.info(f"Checking article ID {article_id}: {article_url}")

                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    response = requests.get(article_url, headers=headers)
                    
                    if response.status_code == 404:
                        logger.info(f"Article ID {article_id} not found (404)")
                        failed_consecutive += 1
                        if failed_consecutive > max_consecutive_failures:
                            logger.warning(f"Encountered {max_consecutive_failures} consecutive failures. Stopping.")
                            break
                        continue
                    elif response.status_code != 200:
                        logger.warning(f"Unexpected status code {response.status_code} for ID {article_id}")
                        failed_consecutive += 1
                        if failed_consecutive > max_consecutive_failures:
                            logger.warning(f"Encountered {max_consecutive_failures} consecutive failures. Stopping.")
                            break
                        continue

                    failed_consecutive = 0
                    article_details = self.get_article_details(article_url)
                    
                    if article_details:
                        self.articles.append(article_details)
                        self.article_ids.add(str(article_id))
                        total_saved += 1
                        
                        if total_saved % save_interval == 0:
                            self.save_to_json()
                            logger.info(f"Progress: Saved {total_saved} articles so far")
                    else:
                        logger.warning(f"Failed to extract details for article ID {article_id}")
                    
                    total_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing article ID {article_id}: {e}")
                    failed_consecutive += 1
                    if failed_consecutive > max_consecutive_failures:
                        logger.warning(f"Encountered {max_consecutive_failures} consecutive failures. Stopping.")
                        break
            
            current_id = batch_start - 1

            if self.articles:
                self.save_to_json()
                
            if failed_consecutive > max_consecutive_failures:
                logger.warning("Too many failures")
                break
                
        logger.info(f"Processed: {total_processed}, saved: {total_saved} articles")
        return total_saved
    
    def download_missing_articles_from_json(self, missing_urls_file, save_interval=10):

        try:

            with open(missing_urls_file, "r", encoding="utf-8") as f:
                missing_urls = json.load(f)
            
            logger.info(f"Loaded {len(missing_urls)} missing URLs from {missing_urls_file}")
            
            total_processed = 0
            total_saved = 0
            
            for idx, url_item in enumerate(missing_urls):
                try:
                    article_id = url_item.get("id")
                    article_url = url_item.get("url")
                    
                    if not article_id or not article_url:
                        logger.warning(f"Missing ID or URL in item: {url_item}")
                        continue
                    
                    if article_id in self.article_ids:
                        logger.info(f"Article ID {article_id} already processed, skipping")
                        continue
                    
                    logger.info(f"Processing article {idx+1}/{len(missing_urls)}: {article_url}")
                    
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    response = requests.get(article_url, headers=headers)
                    
                    if response.status_code == 404:
                        logger.info(f"Article ID {article_id} not found (404)")
                        continue
                    elif response.status_code != 200:
                        logger.warning(f"Unexpected status code {response.status_code} for ID {article_id}")
                        continue

                    article_details = self.get_article_details(article_url)
                    
                    if article_details:
                        self.articles.append(article_details)
                        self.article_ids.add(article_id)
                        total_saved += 1
                        
                        if total_saved % save_interval == 0:
                            self.save_to_json()
                            logger.info(f"Progress: Saved {total_saved}/{len(missing_urls)} articles")
                    
                    total_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing URL {article_url}: {e}")

            if self.articles:
                self.save_to_json()
                
            logger.info(f"Processed: {total_processed}, saved: {total_saved} articles")
            return total_saved
            
        except Exception as e:
            logger.error(f"Error processing missing URLs file: {e}")
            return 0
        
    def _download_articles(self, publication_urls):
        total_processed = 0
        total_saved = 0
        
        logger.info(f"Starting download of {len(publication_urls)} articles")
        
        for idx, article_url in enumerate(publication_urls):
            try:
                match = re.search(r'/publikacja/([0-9]+)$', article_url)
                if not match:
                    logger.warning(f"Failed to extract ID from URL: {article_url}")
                    continue
                
                article_id = match.group(1)
                
                if article_id in self.article_ids:
                    logger.info(f"Article ID {article_id} already processed, skipping")
                    continue

                logger.info(f"Getting article details {idx+1}/{len(publication_urls)}: {article_url}")
                article_details = self.get_article_details(article_url)
                
                if article_details:
                    self.articles.append(article_details)
                    self.article_ids.add(article_id)
                    total_saved += 1
                    
                total_processed += 1

                if total_processed % 10 == 0:
                    self.save_to_json()
                    logger.info(f"Progress: {total_processed}/{len(publication_urls)} articles processed")
                    
            except Exception as e:
                logger.error(f"Error processing {article_url}: {e}")

        if self.articles:
            self.save_to_json()
            
        logger.info(f"Download completed. Processed: {total_processed}, saved: {total_saved} articles")
        return total_saved
        
    def download_all_articles(self, method="sitemap", max_id=None, missing_urls_file=None):
        if method == "sitemap":
            return self.download_articles_from_sitemap()
        elif method == "scrolling":
            return self.download_articles_by_scrolling()
        elif method == "id_range" and max_id is not None:
            return self.download_articles_by_id_range(max_id=max_id)
        elif method == "missing_urls" and missing_urls_file is not None:
            return self.download_missing_articles_from_json(missing_urls_file)
        else:
            return 0

def main():
    output_file = "data/raw/articles.json"
    download_method = "sitemap" 
    max_id = 150000  
    missing_urls_file = "data/raw/missing_urls.json" 

    try:
        options = Options()
        driver = webdriver.Chrome(options=options)
        
        downloader = BADAPDownloader(
            web_driver=driver,
            output_file=output_file
        )
        
        if download_method == "sitemap":
            total_articles = downloader.download_articles_from_sitemap()
        elif download_method == "scrolling":
            total_articles = downloader.download_articles_by_scrolling()
        elif download_method == "id_range":
            total_articles = downloader.download_articles_by_id_range(max_id=max_id)
        elif download_method == "missing_urls":
            total_articles = downloader.download_missing_articles_from_json(missing_urls_file)
        else:
            total_articles = 0
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        total_articles = 0
    finally:
        driver.quit()
        logger.info(f"Total articles downloaded: {total_articles}")