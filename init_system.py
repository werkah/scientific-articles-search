import os
import json
import time
import logging
import requests
import subprocess
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")


def setup_directories():
    data_dirs = [
        DATA_DIR,
        DATA_DIR / "raw",
        DATA_DIR / "cleaned",
        DATA_DIR / "enriched",
        DATA_DIR / "combined_embeddings",
    ]

    for directory in data_dirs:
        directory.mkdir(exist_ok=True, parents=True)

    logger.info("Required directories have been created")
    return True


def check_elasticsearch():
    try:
        response = requests.get(ES_URL, timeout=5)
        if response.status_code == 200:
            logger.info("Elasticsearch is working properly")
            return True
        logger.error(f"Elasticsearch returned error code: {response.status_code}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Cannot connect to Elasticsearch: {e}")
        return False


def scrape_authors():
    authors_file = DATA_DIR / "raw" / "authors.json"

    if authors_file.exists():
        logger.info(f"File {authors_file} already exists, skipping download")
        return True

    logger.info("Downloading author data...")

    try:
        from scripts.scraper_authors import main as scrape_authors_main

        scrape_authors_main()

        if authors_file.exists():
            logger.info(f"Successfully downloaded author data to {authors_file}")
            return True
        else:
            logger.error(f"File {authors_file} not found after download attempt")
            return False
    except Exception as e:
        logger.error(f"Error while downloading authors: {e}")
        return False


def scrape_articles():
    articles_file = DATA_DIR / "raw" / "articles.json"

    if articles_file.exists():
        logger.info(f"File {articles_file} already exists, skipping download")
        return True

    logger.info("Downloading article data...")

    try:
        from scripts.scraper_articles import main as scrape_articles_main

        scrape_articles_main()

        if articles_file.exists():
            logger.info(f"Successfully downloaded article data to {articles_file}")
            return True
        else:
            logger.error(f"File {articles_file} not found after download attempt")
            return False
    except Exception as e:
        logger.error(f"Error while downloading articles: {e}")
        return False


def clean_authors():
    raw_authors = DATA_DIR / "raw" / "authors.json"
    cleaned_authors = DATA_DIR / "cleaned" / "authors_cleaned.json"

    if cleaned_authors.exists():
        logger.info(f"File {cleaned_authors} already exists, skipping cleaning")
        return True

    if not raw_authors.exists():
        logger.error(f"Source file {raw_authors} not found")
        return False

    logger.info("Cleaning author data...")

    try:
        with open(raw_authors, encoding="utf-8") as f:
            authors = json.load(f)

        cleaned = [a for a in authors if a.get("art_num", 0) > 0]

        cleaned_authors.parent.mkdir(exist_ok=True)

        with open(cleaned_authors, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(cleaned)} cleaned authors to {cleaned_authors}")
        return True
    except Exception as e:
        logger.error(f"Error while cleaning author data: {e}")
        return False


def clean_articles():
    raw_articles = DATA_DIR / "raw" / "articles.json"
    cleaned_articles = DATA_DIR / "cleaned" / "cleaned_articles.json"

    if cleaned_articles.exists():
        logger.info(f"File {cleaned_articles} already exists, skipping cleaning")
        return True

    if not raw_articles.exists():
        logger.error(f"Source file {raw_articles} not found")
        return False

    logger.info("Cleaning article data...")

    try:
        from scripts.data_cleaner import DataCleaner

        cleaner = DataCleaner()
        articles = cleaner.load(str(raw_articles))
        cleaned_articles_data = cleaner.clean(articles)

        cleaned_articles.parent.mkdir(exist_ok=True)

        cleaner.save(cleaned_articles_data, str(cleaned_articles))

        logger.info(
            f"Saved {len(cleaned_articles_data)} cleaned articles to {cleaned_articles}"
        )
        return True
    except Exception as e:
        logger.error(f"Error while cleaning article data: {e}")
        return False


def generate_embeddings():
    cleaned_articles = DATA_DIR / "cleaned" / "cleaned_articles.json"
    enriched_dir = DATA_DIR / "enriched"

    existing_embeddings = list(enriched_dir.glob("enriched_part_*.zip"))
    if existing_embeddings:
        logger.info(
            f"Embedding vectors already exist ({len(existing_embeddings)} files)"
        )
        return True

    if not cleaned_articles.exists():
        logger.error(f"File {cleaned_articles} not found")
        return False

    logger.info("Generating embedding vectors...")

    try:
        from scripts.embedding_generator import EmbeddingGenerator

        enriched_dir.mkdir(exist_ok=True)

        with open(cleaned_articles, "r", encoding="utf-8") as f:
            articles = json.load(f)

        logger.info(f"Generating embeddings for {len(articles)} articles...")

        generator = EmbeddingGenerator(output_dir=str(enriched_dir))
        embedding_files = generator.process_in_parts(
            articles, parts=5, base_path=str(enriched_dir / "enriched")
        )

        logger.info(f"Generated {len(embedding_files)} files with embedding vectors")
        return True
    except Exception as e:
        logger.error(f"Error while generating embeddings: {e}")
        return False


def generate_combined_embeddings():
    enriched_dir = DATA_DIR / "enriched"
    combined_dir = DATA_DIR / "combined_embeddings"
    

    existing_combined = list(combined_dir.glob("combined_*.zip"))
    if existing_combined:
        logger.info(f"Combined embeddings already exist ({len(existing_combined)} files)")
        return True
    

    enriched_files = list(enriched_dir.glob("enriched_part_*.zip"))
    if not enriched_files:
        logger.error("No enriched files found, can't generate combined embeddings")
        return False
    
    logger.info("Generating combined embeddings...")
    
    try:
        from scripts.embedding_generator import EmbeddingGenerator
        
        combined_dir.mkdir(exist_ok=True)
        
        generator = EmbeddingGenerator(output_dir=str(enriched_dir))
        combined_files = generator.generate_combined_embeddings(parts=5, batch_size=64)
        
        logger.info(f"Generated {len(combined_files)} files with combined embeddings")
        return True
    except Exception as e:
        logger.error(f"Error while generating combined embeddings: {e}")
        return False


def setup_elasticsearch_indices():
    logger.info("Checking Elasticsearch indices...")

    try:
        from backend.elasticsearch_service import ElasticsearchService

        host = ES_URL.replace("http://", "").split(":")[0]
        port = ES_URL.split(":")[-1]

        es = ElasticsearchService(host=host, port=port)

        article_exists = (
            es.session.head(f"{es.url}/{es.article_index}").status_code == 200
        )
        author_exists = (
            es.session.head(f"{es.url}/{es.author_index}").status_code == 200
        )

        if article_exists and author_exists:
            logger.info(
                "All Elasticsearch indices already exist, no need to create them"
            )
            return True

        if not article_exists:
            logger.info(f"Creating article index '{es.article_index}'...")
            ok_articles = es.create_article_index(recreate=False)
            if not ok_articles:
                logger.error(f"Failed to create article index '{es.article_index}'")
                return False
        else:
            logger.info(f"Article index '{es.article_index}' already exists")

        if not author_exists:
            logger.info(f"Creating author index '{es.author_index}'...")
            ok_authors = es.create_author_index(recreate=False)
            if not ok_authors:
                logger.error(f"Failed to create author index '{es.author_index}'")
                return False
        else:
            logger.info(f"Author index '{es.author_index}' already exists")

        logger.info("Elasticsearch indices are ready")
        return True
    except Exception as e:
        logger.error(f"Error while configuring indices: {e}")
        return False


def index_data():
    cleaned_authors = DATA_DIR / "cleaned" / "authors_cleaned.json"
    enriched_dir = DATA_DIR / "enriched"

    if not cleaned_authors.exists():
        logger.error(f"File {cleaned_authors} not found")
        return False

    enriched_files = list(enriched_dir.glob("enriched_part_*.zip"))
    if not enriched_files:
        logger.error("No embedding files found")
        return False

    logger.info("Indexing data...")

    try:
        from backend.elasticsearch_service import ElasticsearchService

        host = ES_URL.replace("http://", "").split(":")[0]
        port = ES_URL.split(":")[-1]

        es_service = ElasticsearchService(host=host, port=port)

        article_count_resp = es_service.session.get(
            f"{es_service.url}/{es_service.article_index}/_count"
        )
        if article_count_resp.status_code == 200:
            article_count = article_count_resp.json().get("count", 0)
            if article_count > 0:
                logger.info(
                    f"{article_count} articles already indexed, skipping article indexing"
                )
            else:
                for enriched_file in enriched_files:
                    logger.info(f"Indexing articles from {enriched_file}...")
                    count = es_service.index_articles_from_zip(str(enriched_file))
                    logger.info(f"Indexed {count} articles from file {enriched_file}")
        else:
            for enriched_file in enriched_files:
                logger.info(f"Indexing articles from {enriched_file}...")
                count = es_service.index_articles_from_zip(str(enriched_file))
                logger.info(f"Indexed {count} articles from file {enriched_file}")

        author_count_resp = es_service.session.get(
            f"{es_service.url}/{es_service.author_index}/_count"
        )
        if author_count_resp.status_code == 200:
            author_count = author_count_resp.json().get("count", 0)
            if author_count > 0:
                logger.info(
                    f"{author_count} authors already indexed, skipping author indexing"
                )
            else:
                logger.info("Indexing authors...")
                count = es_service.index_authors(str(cleaned_authors))
                logger.info(f"Indexed {count} authors")
        else:
            logger.info("Indexing authors...")
            count = es_service.index_authors(str(cleaned_authors))
            logger.info(f"Indexed {count} authors")

        logger.info("Checking if author enrichment is needed...")
        sample_resp = es_service.session.post(
            f"{es_service.url}/{es_service.author_index}/_search",
            json={"query": {"exists": {"field": "publications"}}, "size": 1},
        )

        if (
            sample_resp.status_code == 200
            and sample_resp.json().get("hits", {}).get("total", {}).get("value", 0) > 0
        ):
            count_resp = es_service.session.post(
                f"{es_service.url}/{es_service.author_index}/_count",
                json={"query": {"exists": {"field": "publications"}}},
            )
            if count_resp.status_code == 200:
                enriched_count = count_resp.json().get("count", 0)
                logger.info(
                    f"{enriched_count} authors already have publications, skipping enrichment"
                )
            else:
                logger.info("Authors already have publications, skipping enrichment")
        else:
            logger.info("Enriching authors with publications...")
            count = es_service.enrich_authors_with_publications()
            logger.info(f"Updated {count} authors with publications")

        logger.info("Checking if article denormalization is needed...")

        total_articles = 0
        total_resp = es_service.session.get(f"{es_service.url}/{es_service.article_index}/_count")
        if total_resp.status_code == 200:
            total_articles = total_resp.json().get("count", 0)

        denormalized_count = 0
        denorm_resp = es_service.session.post(
            f"{es_service.url}/{es_service.article_index}/_count",
            json={"query": {"exists": {"field": "author_units"}}}
        )
        if denorm_resp.status_code == 200:
            denormalized_count = denorm_resp.json().get("count", 0)

        if total_articles > 0 and denormalized_count >= total_articles:
            logger.info(f"All articles ({total_articles}) already have denormalized author data, skipping denormalization")
        else:
            if denormalized_count > 0:
                logger.info(f"Denormalizing remaining articles ({total_articles - denormalized_count} of {total_articles})...")
            else:
                logger.info("Starting denormalization of all articles...")
            
            updated = es_service.denormalize_author_data_in_articles()
            logger.info(f"Denormalized {updated} articles with author data")
            

        combined_dir = DATA_DIR / "combined_embeddings"
        if combined_dir.exists() and list(combined_dir.glob("combined_*.zip")):
            logger.info("Checking if combined embeddings indexing is needed...")
            

            combined_count = 0
            combined_resp = es_service.session.post(
                f"{es_service.url}/{es_service.article_index}/_count",
                json={"query": {"exists": {"field": "combined_embedding"}}}
            )
            if combined_resp.status_code == 200:
                combined_count = combined_resp.json().get("count", 0)
            
            if combined_count >= total_articles:
                logger.info(f"All articles ({total_articles}) already have combined embeddings, skipping indexing")
            else:
                logger.info(f"Indexing combined embeddings ({combined_count}/{total_articles} already processed)...")

                es_service.update_mapping_for_combined_embeddings()

                updated = es_service.index_combined_embeddings()
                logger.info(f"Added combined embeddings to {updated} articles")
        else:
            logger.info("No combined embeddings found, skipping this step")

        return True
    except Exception as e:
        logger.error(f"Error while indexing data: {e}")
        return False


def start_backend():
    try:
        response = requests.get("http://localhost:8000", timeout=2)
        if response.status_code == 200:
            logger.info("Backend is already running")
            return True
    except:
        pass

    logger.info("Starting backend...")

    try:
        subprocess.Popen(
            ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        for i in range(10):
            try:
                time.sleep(2)
                response = requests.get("http://localhost:8000", timeout=1)
                if response.status_code == 200:
                    logger.info("Backend started successfully")
                    return True
            except:
                logger.info(f"Waiting for backend... ({i+1}/10)")

        logger.warning("Could not confirm backend startup")
        return False
    except Exception as e:
        logger.error(f"Error while starting backend: {e}")
        return False


def start_frontend():
    try:
        response = requests.get("http://localhost:8050", timeout=2)
        if response.status_code == 200:
            logger.info("Frontend is already running")
            return True
    except:
        pass
    
    logger.info("Starting frontend...")
    
    try:
        env = os.environ.copy()
        env["API_URL"] = "http://localhost:8000"
        env["PYTHONUNBUFFERED"] = "1"  

        subprocess.Popen(
            ["python", "frontend/app.py"],
            env=env
        )
        
        logger.info("Waiting for frontend to start (this may take a moment)...")
        for i in range(15):  
            try:
                time.sleep(2)  
                response = requests.get("http://localhost:8050", timeout=2)
                if response.status_code == 200:
                    logger.info("Frontend started successfully")
                    return True
            except:
                if i % 3 == 0: 
                    logger.info(f"Still waiting for frontend... ({i+1}/15)")
        
        logger.warning("Could not confirm frontend startup, but it may still be starting")
        return True 
    except Exception as e:
        logger.error(f"Error while starting frontend: {e}")
        return False


def init_full():
    logger.info("=== Starting full system initialization ===")

    setup_directories()

    if not check_elasticsearch():
        logger.error("Elasticsearch is necessary for system operation")
        return False

    scrape_authors()
    scrape_articles()

    clean_authors()
    clean_articles()

    generate_embeddings()
    

    generate_combined_embeddings()

    if not setup_elasticsearch_indices():
        logger.error("Cannot continue without created indices")
        return False

    if not index_data():
        logger.error("Cannot continue without indexed data")
        return False

    start_backend()
    start_frontend()

    logger.info("=== System initialization completed ===")
    logger.info("Backend: http://localhost:8000")
    logger.info("Frontend: http://localhost:8050")
    return True


def init_services_only():
    logger.info("=== Starting services without data processing ===")

    if not check_elasticsearch():
        logger.error("Elasticsearch is necessary for system operation")
        return False

    start_backend()
    start_frontend()

    logger.info("=== Services started ===")
    logger.info("Backend: http://localhost:8000")
    logger.info("Frontend: http://localhost:8050")
    return True


def init_process_data_only():
    logger.info("=== Starting data processing ===")

    setup_directories()

    if not check_elasticsearch():
        logger.error("Elasticsearch is necessary for system operation")
        return False

    scrape_authors()
    scrape_articles()

    clean_authors()
    clean_articles()

    generate_embeddings()
    
    generate_combined_embeddings()

    if not setup_elasticsearch_indices():
        logger.error("Cannot continue without created indices")
        return False

    if not index_data():
        logger.error("Cannot continue without indexed data")
        return False

    logger.info("=== Data processing completed ===")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        param = sys.argv[1].lower()

        if param == "services":
            init_services_only()
        elif param == "data":
            init_process_data_only()
        else:
            print(f"Unknown parameter: {param}")
            print("Available parameters:")
            print("  services - run only services")
            print("  data - process only data")
            print("  No parameter - full initialization")
    else:
        init_full()