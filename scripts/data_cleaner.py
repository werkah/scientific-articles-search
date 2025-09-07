import json
import re
import logging
import os
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class DataCleaner:
    INVALID_ABSTRACTS = {"Brak abstraktu"}

    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        logger.info(f"Loaded {len(articles)} articles from {path}")
        return articles

    def clean_text(self, txt, field=""):
        if not isinstance(txt, str):
            return ""
        t = txt.strip()
        if field == "abstract" and t.lower() in {
            x.lower() for x in self.INVALID_ABSTRACTS
        }:
            return ""
        return re.sub(r"\s+", " ", t)
        
    def normalize_latex(self, text):
        if not isinstance(text, str):
            return text
            
        pattern = r"\${1,2}(.*?)\${1,2}"

        def repl(match):
            expr = match.group(1)
            normalized = expr.replace("_", "")
            normalized = re.sub(r"[{}]", "", normalized)
            normalized = re.sub(r"([A-Za-z])_(\d+)", r"\1\2", normalized)
            return normalized

        normalized_text = re.sub(pattern, repl, text)
        normalized_text = normalized_text.replace("$", "")
        return normalized_text

    def process_chemical_data(self, articles):
        logger.info("Processing chemical formulas in articles...")
        processed_count = 0
        
        for article in tqdm(articles, desc="Processing chemical data"):
            modified = False
            
            if "title" in article and isinstance(article["title"], str):
                normalized_title = self.normalize_latex(article["title"])
                if normalized_title != article["title"]:
                    article["title"] = normalized_title
                    modified = True
                    
            if "abstract" in article and isinstance(article["abstract"], str):
                normalized_abstract = self.normalize_latex(article["abstract"])
                if normalized_abstract != article["abstract"]:
                    article["abstract"] = normalized_abstract
                    modified = True
                    
            if "keywords" in article and isinstance(article["keywords"], list):
                normalized_keywords = [self.normalize_latex(kw) for kw in article["keywords"]]
                if normalized_keywords != article["keywords"]:
                    article["keywords"] = normalized_keywords
                    modified = True
                    
            if modified:
                processed_count += 1
                
        logger.info(f"Processed chemical formulas in {processed_count} articles")
        return articles

    def clean(self, raws):
        cleaned = []
        skipped = 0
        for art in tqdm(raws, desc="Cleaning data"):
            if not art.get("id") or not art.get("title"):
                skipped += 1
                continue

            title = self.clean_text(art["title"], field="title")
            abstract = self.clean_text(art.get("abstract", ""), field="abstract")
            keywords = [self.clean_text(k) for k in art.get("keywords", []) if k]

            cleaned.append(
                {
                    "id": art["id"],
                    "url": art.get("url", ""),
                    "title": title,
                    "abstract": abstract,
                    "keywords": keywords,
                    "authors": art.get("authors", []),
                    "publication_year": art.get("publication_year", ""),
                    "publication_type": art.get("publication_type", ""),
                }
            )

        logger.info(f"Cleaned {len(cleaned)} articles, skipped {skipped}")
        
        cleaned = self.process_chemical_data(cleaned)
        
        return cleaned

    def save(self, articles, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote cleaned data to {path}")