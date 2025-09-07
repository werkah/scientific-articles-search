import logging
import time
import os
import zipfile
import json
import requests
from backend.config import HOST, PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ElasticsearchService:
    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        article_index="scientific_articles",
        author_index="authors",
        timeout=30,
    ):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.article_index = article_index
        self.author_index = author_index
        self.timeout = timeout
        self.es_version = self._detect_es_version()
        logger.info(f"Detected Elasticsearch version: {self.es_version}")
        self.session = requests.Session()
        try:
            self.session.get(self.url, timeout=5).raise_for_status()
            logger.info(f"Connected to Elasticsearch at {self.url}")
        except Exception as exc:
            logger.error(f"Cannot connect to Elasticsearch: {exc}")
            raise ConnectionError(f"Cannot connect to Elasticsearch: {exc}")

    def _detect_es_version(self):
        try:
            response = requests.get(self.url, timeout=5)
            if response.status_code == 200:
                return response.json().get("version", {}).get("number")
        except Exception as e:
            logger.warning(f"Could not detect Elasticsearch version: {e}")
        return None

    def wait_for_elasticsearch(self, timeout=60, interval=5):
        start = time.time()
        while time.time() - start < timeout:
            try:
                if requests.get(self.url, timeout=interval).status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(interval)
        return False

    def refresh_index(self, index_name):
        try:
            resp = self.session.post(f"{self.url}/{index_name}/_refresh")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning(f"Could not refresh index '{index_name}': {exc}")
            return False

    def search_sync(self, index, body):

        try:
            url = f"{self.url}/{index}/_search"
            response = self.session.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in search_sync: {e}")
            return {"error": str(e)}

    def scroll_search(self, index, body, batch_size=1000):

        results = []

        scroll_body = {**body, "size": batch_size, "sort": ["_doc"]}

        try:

            scroll_resp = self.session.post(
                f"{self.url}/{index}/_search?scroll=2m",
                json=scroll_body,
                timeout=self.timeout,
            )
            scroll_resp.raise_for_status()

            response_data = scroll_resp.json()
            scroll_id = response_data.get("_scroll_id")
            hits = response_data.get("hits", {}).get("hits", [])

            results.extend([hit["_source"] for hit in hits])

            while hits:
                scroll_resp = self.session.post(
                    f"{self.url}/_search/scroll",
                    json={"scroll": "2m", "scroll_id": scroll_id},
                    timeout=self.timeout,
                )
                scroll_resp.raise_for_status()

                response_data = scroll_resp.json()
                scroll_id = response_data.get("_scroll_id")
                hits = response_data.get("hits", {}).get("hits", [])

                results.extend([hit["_source"] for hit in hits])

            try:
                self.session.delete(
                    f"{self.url}/_search/scroll",
                    json={"scroll_id": [scroll_id]},
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"Error cleaning up scroll: {e}")

            return results

        except Exception as e:
            logger.error(f"Error in scroll_search: {e}")
            return []

    def create_article_index(self, name=None, dim=384, recreate=False):

        index_name = name or self.article_index
        idx_url = f"{self.url}/{index_name}"
        try:
            exists = self.session.head(idx_url).status_code == 200
        except Exception as e:
            logger.error(f"Error checking if index exists: {e}")
            return False
        if exists and recreate:
            try:
                del_resp = self.session.delete(idx_url)
                if del_resp.status_code not in (200, 404):
                    return False
            except Exception:
                return False
        elif exists:
            return True
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "multilingual": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    }
                }
            },
        }
        mappings = {
            "properties": {
                "id": {"type": "keyword"},
                "url": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "multilingual",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "abstract": {"type": "text", "analyzer": "multilingual"},
                "authors": {"type": "keyword"},
                "author_units": {"type": "keyword"},
                "author_subunits": {"type": "keyword"},
                "author_names": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "keywords": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "publication_year": {"type": "integer"},
                "publication_type": {"type": "keyword"},
                "title_embedding": {
                    "type": "dense_vector",
                    "dims": dim,
                    "index": True,
                    "similarity": "cosine",
                },
                "abstract_embedding": {
                    "type": "dense_vector",
                    "dims": dim,
                    "index": True,
                    "similarity": "cosine",
                },
                "keywords_embedding": {
                    "type": "dense_vector",
                    "dims": dim,
                    "index": True,
                    "similarity": "cosine",
                },
                "combined_embedding": {
                    "type": "dense_vector",
                    "dims": dim,
                    "index": True,
                    "similarity": "cosine",
                },
                "combined_content": {
                    "type": "text",
                    "analyzer": "multilingual",
                },
            }
        }
        data = {"settings": settings, "mappings": mappings}
        try:
            resp = self.session.put(
                idx_url, json=data, headers={"Content-Type": "application/json"}
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False

    def create_author_index(self, name=None, recreate=False):

        index_name = name or self.author_index
        idx_url = f"{self.url}/{index_name}"
        try:
            exists = self.session.head(idx_url).status_code == 200
        except Exception as e:
            logger.error(f"Error checking if index exists: {e}")
            return False
        if exists and recreate:
            try:
                del_resp = self.session.delete(idx_url)
                if del_resp.status_code not in (200, 404):
                    return False
            except Exception:
                return False
        elif exists:
            return True
        settings = {"number_of_shards": 1, "number_of_replicas": 0}
        mappings = {
            "properties": {
                "id": {"type": "keyword"},
                "full_name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "unit": {"type": "keyword"},
                "subunit": {"type": "keyword"},
                "link": {"type": "keyword"},
                "art_num": {"type": "integer"},
                "publications": {"type": "keyword"},
            }
        }
        data = {"settings": settings, "mappings": mappings}
        try:
            resp = self.session.put(
                idx_url, json=data, headers={"Content-Type": "application/json"}
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False

    def setup_all_indices(self, recreate=False):

        if not self.wait_for_elasticsearch():
            return False
        return self.create_article_index(
            recreate=recreate
        ) and self.create_author_index(recreate=recreate)

    def index_authors(self, authors_file, batch_size=500):

        try:
            authors = json.load(open(authors_file, encoding="utf-8"))
        except Exception as exc:
            logger.error(f"Error loading file {authors_file}: {exc}")
            return 0
        seen, unique = set(), []
        for author in authors:
            aid = author.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                unique.append(author)
        total, success = len(unique), 0
        for i in range(0, total, batch_size):
            batch = unique[i : i + batch_size]
            ndjson = ""
            for author in batch:
                aid = author["id"]
                ndjson += (
                    json.dumps({"index": {"_index": self.author_index, "_id": aid}})
                    + "\n"
                )
                ndjson += json.dumps(author) + "\n"
            resp = self.session.post(
                f"{self.url}/_bulk?refresh=wait_for",
                data=ndjson,
                headers={"Content-Type": "application/x-ndjson"},
            )
            if resp.status_code in (200, 201):
                items = resp.json().get("items", [])
                success += sum(
                    1 for it in items if it.get("index", {}).get("status", 0) < 300
                )
        self.refresh_index(self.author_index)
        return success

    def enrich_authors_with_publications(self):

        try:

            auth_resp = self.session.get(f"{self.url}/{self.author_index}/_count")
            art_resp = self.session.get(f"{self.url}/{self.article_index}/_count")

            if auth_resp.status_code != 200 or art_resp.status_code != 200:
                logger.error("Index check failed")
                return 0

            auth_count = auth_resp.json().get("count", 0)
            art_count = art_resp.json().get("count", 0)

            if auth_count == 0 or art_count == 0:
                logger.error(
                    f"No data in indices: authors={auth_count}, articles={art_count}"
                )
                return 0

            self.refresh_index(self.author_index)
            self.refresh_index(self.article_index)

            author_data = self.scroll_search(
                self.author_index, {"query": {"match_all": {}}}
            )

            if not author_data:
                logger.error("No authors found")
                return 0

            updated = 0
            batch_size = 100
            total_authors = len(author_data)

            for i in range(0, total_authors, batch_size):
                batch = author_data[i : i + batch_size]
                bulk_data = ""
                batch_updated = 0

                for author in batch:
                    aid = author.get("id")
                    if not aid:
                        continue

                    pubs_resp = self.session.post(
                        f"{self.url}/{self.article_index}/_search",
                        json={
                            "query": {"term": {"authors": aid}},
                            "_source": ["id"],
                            "size": 1000,
                        },
                        timeout=30,
                    )

                    if pubs_resp.status_code != 200:
                        continue

                    pub_ids = [
                        hit["_source"]["id"]
                        for hit in pubs_resp.json().get("hits", {}).get("hits", [])
                    ]

                    if not pub_ids:
                        continue

                    bulk_data += (
                        json.dumps(
                            {"update": {"_index": self.author_index, "_id": aid}}
                        )
                        + "\n"
                    )
                    bulk_data += json.dumps({"doc": {"publications": pub_ids}}) + "\n"
                    batch_updated += 1

                if bulk_data:
                    bulk_resp = self.session.post(
                        f"{self.url}/_bulk?refresh=true",
                        data=bulk_data,
                        headers={"Content-Type": "application/x-ndjson"},
                        timeout=60,
                    )

                    if bulk_resp.status_code in (200, 201):
                        success_count = sum(
                            1
                            for item in bulk_resp.json().get("items", [])
                            if item.get("update", {}).get("status", 500) < 300
                        )
                        updated += success_count
                        logger.info(
                            f"Batch {i//batch_size + 1}: Updated {success_count}/{batch_updated} authors"
                        )

            logger.info(f"Total authors updated: {updated}")
            return updated

        except Exception as e:
            logger.error(f"Error during author enrichment: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return 0

    def index_articles_from_zip(self, zip_file, batch_size=500):

        if not os.path.exists(zip_file):
            logger.error(f"Zip file does not exist: {zip_file}")
            return 0

        temp_dir = "data/temp_articles"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file, "r") as zipf:
                jsons = [f for f in zipf.namelist() if f.endswith(".json")]
                logger.info(f"Found {len(jsons)} JSON files in {zip_file}")

                if not jsons:
                    logger.error(f"No JSON files found in {zip_file}")
                    return 0

                jf = jsons[0]
                path = os.path.join(temp_dir, os.path.basename(jf))

                with zipf.open(jf) as src, open(path, "wb") as tgt:
                    tgt.write(src.read())

            try:
                with open(path, encoding="utf-8") as f:
                    articles = json.load(f)

                if not isinstance(articles, list):
                    logger.error(
                        f"Expected a list of articles in {jf}, got {type(articles)}"
                    )
                    return 0

                logger.info(f"Loaded {len(articles)} articles from {jf}")

                if not articles:
                    logger.warning(f"No articles found in {jf}")
                    return 0

                if len(articles) > 0:
                    sample = articles[0]
                    if not isinstance(sample, dict) or "id" not in sample:
                        logger.error(
                            f"Articles in {jf} are missing required 'id' field"
                        )
                        return 0
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {path}: {e}")
                return 0

            total = len(articles)
            success = 0
            seen_ids = set()
            duplicates = 0

            for i in range(0, total, batch_size):
                batch = articles[i : i + batch_size]
                ndjson = ""
                batch_size_actual = 0
                batch_duplicates = 0

                for art in batch:
                    aid = art.get("id")
                    if not aid:
                        logger.warning("Skipping article without ID")
                        continue

                    if aid in seen_ids:
                        batch_duplicates += 1
                        continue

                    seen_ids.add(aid)
                    ndjson += (
                        json.dumps(
                            {"index": {"_index": self.article_index, "_id": aid}}
                        )
                        + "\n"
                    )
                    ndjson += json.dumps(art) + "\n"
                    batch_size_actual += 1

                duplicates += batch_duplicates
                if batch_duplicates > 0:
                    logger.info(
                        f"Skipped {batch_duplicates} duplicate articles in current batch"
                    )

                if not ndjson:
                    logger.warning(f"No valid articles in batch {i//batch_size + 1}")
                    continue

                try:
                    resp = self.session.post(
                        f"{self.url}/_bulk?refresh=wait_for",
                        data=ndjson,
                        headers={"Content-Type": "application/x-ndjson"},
                        timeout=self.timeout,
                    )

                    if resp.status_code in (200, 201):
                        batch_success = 0
                        for item in resp.json().get("items", []):
                            st = item.get("index", {}).get("status", 0)
                            if 200 <= st < 300:
                                batch_success += 1
                            else:
                                error = item.get("index", {}).get("error")
                                if error:
                                    logger.warning(
                                        f"Indexing error: {error.get('type')}: {error.get('reason')}"
                                    )

                        success += batch_success
                        logger.info(
                            f"Indexed {batch_success}/{batch_size_actual} articles in batch {i//batch_size + 1}"
                        )
                    else:
                        logger.error(
                            f"Bulk request failed with status {resp.status_code}: {resp.text}"
                        )
                except Exception as e:
                    logger.error(f"Error during bulk indexing: {str(e)}")

            logger.info(f"Indexing complete for {zip_file}")
            logger.info(
                f"Total articles: {total}, Successfully indexed: {success}, Duplicates: {duplicates}"
            )

            self.refresh_index(self.article_index)

            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Could not remove temporary file {path}: {str(e)}")

            return success

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file {zip_file}: {str(e)}")
            return 0
        except Exception:
            logger.exception(f"Error processing {zip_file}")
            return 0
        finally:
            try:
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(
                    f"Could not remove temporary directory {temp_dir}: {str(e)}"
                )

    def get_index_stats(self, index_name):
        try:
            stats = self.session.get(f"{self.url}/{index_name}/_stats").json()
            prim = stats["_all"]["primaries"]
            size = prim["store"]["size_in_bytes"]
            resp_map = self.session.get(f"{self.url}/{index_name}/_mapping").json()
            props = (
                resp_map.get(index_name, {}).get("mappings", {}).get("properties", {})
            )
            fields = len(props)
            count = (
                self.session.get(f"{self.url}/{index_name}/_count")
                .json()
                .get("count", 0)
            )
            return {
                "doc_count": count,
                "deleted": prim["docs"]["deleted"],
                "size_bytes": size,
                "field_count": fields,
                "shards": len(stats.get(index_name, {}).get("shards", {})),
                "index_name": index_name,
            }
        except Exception:
            return {}

    def denormalize_author_data_in_articles(self):

        logger.info("Starting denormalization of author data in articles")
        try:

            author_data = {}

            author_resp = self.scroll_search(
                "authors", {"_source": ["id", "full_name", "unit", "subunit"]}
            )

            for author in author_resp:
                aid = author.get("id")
                if aid:
                    author_data[aid] = {
                        "full_name": author.get("full_name"),
                        "unit": author.get("unit"),
                        "subunit": author.get("subunit"),
                    }

            logger.info(f"Loaded data for {len(author_data)} authors")

            query = {"bool": {"must_not": {"exists": {"field": "author_units"}}}}

            count_resp = self.session.post(
                f"{self.url}/{self.article_index}/_count", json={"query": query}
            )

            if count_resp.status_code != 200:
                return {"error": f"Error counting articles: {count_resp.status_code}"}

            articles_to_update = count_resp.json().get("count", 0)
            logger.info(f"Found {articles_to_update} articles to update")

            if articles_to_update == 0:
                return {"message": "No articles need updating", "updated": 0}

            updated = 0

            articles_to_process = self.scroll_search(
                self.article_index, {"query": query, "_source": ["id", "authors"]}
            )

            logger.info(f"Retrieved {len(articles_to_process)} articles to process")

            batch_size = 200
            for i in range(0, len(articles_to_process), batch_size):
                batch = articles_to_process[i : i + batch_size]
                bulk_data = ""

                for article in batch:
                    article_id = article.get("id")
                    authors = article.get("authors", [])

                    author_units = []
                    author_subunits = []
                    author_names = []

                    for aid in authors:
                        if aid in author_data:
                            if author_data[aid].get("unit"):
                                author_units.append(author_data[aid]["unit"])
                            if author_data[aid].get("subunit"):
                                author_subunits.append(author_data[aid]["subunit"])
                            if author_data[aid].get("full_name"):
                                author_names.append(author_data[aid]["full_name"])

                    update_doc = {}
                    if author_units:
                        update_doc["author_units"] = list(set(author_units))
                    if author_subunits:
                        update_doc["author_subunits"] = list(set(author_subunits))
                    if author_names:
                        update_doc["author_names"] = list(set(author_names))

                    if update_doc:
                        bulk_data += (
                            json.dumps(
                                {
                                    "update": {
                                        "_index": self.article_index,
                                        "_id": article_id,
                                    }
                                }
                            )
                            + "\n"
                        )
                        bulk_data += json.dumps({"doc": update_doc}) + "\n"

                if bulk_data:
                    bulk_resp = self.session.post(
                        f"{self.url}/_bulk",
                        headers={"Content-Type": "application/x-ndjson"},
                        data=bulk_data,
                    )

                    if bulk_resp.status_code in (200, 201):
                        batch_updated = sum(
                            1
                            for item in bulk_resp.json().get("items", [])
                            if item.get("update", {}).get("status", 0) in (200, 201)
                        )
                        updated += batch_updated
                        logger.info(
                            f"Batch {i//batch_size + 1}: Updated {batch_updated}/{len(batch)} articles"
                        )
                    else:
                        logger.warning(f"Bulk update failed: {bulk_resp.status_code}")

            self.refresh_index(self.article_index)

            logger.info(f"Denormalization completed. Updated {updated} articles.")

            return {
                "processed": len(articles_to_process),
                "updated": updated,
                "total_to_update": articles_to_update,
            }

        except Exception as e:
            logger.error(f"Error during denormalization: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {"error": str(e)}

    def update_mapping_for_combined_embeddings(self):

        try:

            map_resp = self.session.get(f"{self.url}/{self.article_index}/_mapping")
            if map_resp.status_code != 200:
                logger.error(f"Failed to get mapping: {map_resp.status_code}")
                return False

            properties = (
                map_resp.json()
                .get(self.article_index, {})
                .get("mappings", {})
                .get("properties", {})
            )

            if "combined_embedding" in properties:
                logger.info("Combined embedding field already exists in mapping")
                return True

            mapping = {
                "properties": {
                    "combined_embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "combined_content": {"type": "text", "analyzer": "multilingual"},
                }
            }

            update_resp = self.session.put(
                f"{self.url}/{self.article_index}/_mapping", json=mapping
            )

            if update_resp.status_code >= 400:
                logger.error(
                    f"Failed to update mapping: {update_resp.status_code} - {update_resp.text}"
                )
                return False

            logger.info(
                "Successfully updated mapping to include combined embedding fields"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating mapping for combined embeddings: {e}")
            return False

    def index_combined_embeddings(
        self, combined_dir="data/combined_embeddings", batch_size=200
    ):
        from pathlib import Path
        import traceback

        combined_path = Path(combined_dir)
        if not combined_path.exists():
            logger.info(f"Combined embeddings directory {combined_dir} does not exist")
            return 0

        if not self.update_mapping_for_combined_embeddings():
            logger.error("Failed to update mapping for combined embeddings")
            return 0

        processed_ids = set()
        try:
            query = {
                "query": {"exists": {"field": "combined_embedding"}},
                "_source": ["id"],
                "size": 10000,
            }

            response = self.session.post(
                f"{self.url}/{self.article_index}/_search?scroll=1m", json=query
            )

            if response.status_code == 200:
                result = response.json()
                scroll_id = result.get("_scroll_id")
                hits = result.get("hits", {}).get("hits", [])

                while hits:
                    for hit in hits:
                        processed_ids.add(hit["_source"]["id"])

                    scroll_response = self.session.post(
                        f"{self.url}/_search/scroll",
                        json={"scroll": "1m", "scroll_id": scroll_id},
                    )

                    if scroll_response.status_code != 200:
                        break

                    result = scroll_response.json()
                    scroll_id = result.get("_scroll_id")
                    hits = result.get("hits", {}).get("hits", [])

                if scroll_id:
                    self.session.delete(
                        f"{self.url}/_search/scroll", json={"scroll_id": [scroll_id]}
                    )

                logger.info(
                    f"Found {len(processed_ids)} articles already with combined embeddings"
                )

        except Exception as e:
            logger.warning(f"Error checking for existing combined embeddings: {e}")
            logger.warning(traceback.format_exc())

        combined_files = list(combined_path.glob("combined_*.zip"))
        if not combined_files:
            logger.info(f"No combined embedding files found in {combined_dir}")
            return 0

        logger.info(f"Found {len(combined_files)} combined embedding files")

        total_updated = 0

        for zip_file in combined_files:
            logger.info(f"Processing {zip_file}")

            try:

                try:
                    with zipfile.ZipFile(zip_file, "r") as test_zipf:
                        json_files = [f for f in test_zipf.namelist() if f.endswith(".json")]
                        if not json_files:
                            logger.error(f"No JSON files found in {zip_file}")
                            continue
                except zipfile.BadZipFile:
                    logger.error(f"Invalid zip file: {zip_file}")
                    continue
                

                articles = []
                with zipfile.ZipFile(zip_file, "r") as zipf:
                    json_file = [f for f in zipf.namelist() if f.endswith(".json")][0]
                    
                    try:
                        with zipf.open(json_file) as f:
                            articles = json.load(f)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in {zip_file}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error reading JSON from {zip_file}: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue

                logger.info(f"Loaded {len(articles)} articles from {zip_file}")


                if not isinstance(articles, list):
                    logger.error(f"Expected list of articles in {zip_file}, got {type(articles)}")
                    continue
                    
                if not articles:
                    logger.warning(f"No articles found in {zip_file}")
                    continue
                    

                sample = articles[0]
                if not isinstance(sample, dict):
                    logger.error(f"Articles in {zip_file} are not dictionaries")
                    continue
                    
                if "id" not in sample or "combined_embedding" not in sample:
                    logger.error(f"Articles in {zip_file} missing required fields")
                    continue

                articles_to_update = [
                    a
                    for a in articles
                    if a.get("id") not in processed_ids and a.get("combined_embedding")
                ]
                logger.info(
                    f"Updating {len(articles_to_update)} articles after filtering"
                )

                if not articles_to_update:
                    continue

                file_updated = 0
                for i in range(0, len(articles_to_update), batch_size):
                    batch = articles_to_update[i : i + batch_size]

                    bulk_data = ""
                    for article in batch:
                        doc_id = article["id"]
                        bulk_data += (
                            json.dumps(
                                {
                                    "update": {
                                        "_index": self.article_index,
                                        "_id": doc_id,
                                    }
                                }
                            )
                            + "\n"
                        )
                        bulk_data += (
                            json.dumps(
                                {
                                    "doc": {
                                        "combined_embedding": article[
                                            "combined_embedding"
                                        ],
                                        "combined_content": article.get(
                                            "combined_content", ""
                                        ),
                                    }
                                }
                            )
                            + "\n"
                        )

                    try:
                        bulk_resp = self.session.post(
                            f"{self.url}/_bulk",
                            data=bulk_data,
                            headers={"Content-Type": "application/x-ndjson"},
                        )

                        if bulk_resp.status_code >= 400:
                            logger.error(f"Bulk update failed: {bulk_resp.status_code} - {bulk_resp.text[:200]}")
                            continue

                        result = bulk_resp.json()
                        errors = result.get("errors", False)
                        if errors:
                            error_items = [
                                item 
                                for item in result.get("items", [])
                                if item.get("update", {}).get("status", 0) >= 400
                            ]
                            if error_items:
                                logger.error(f"Bulk update had errors: {error_items[0]}")
                        
                        batch_updated = sum(
                            1
                            for item in result.get("items", [])
                            if item.get("update", {}).get("status", 0) < 400
                        )

                        file_updated += batch_updated
                        logger.info(
                            f"Updated {batch_updated}/{len(batch)} articles in batch"
                        )

                        for article in batch:
                            processed_ids.add(article["id"])
                    except Exception as e:
                        logger.error(f"Error in bulk update: {str(e)}")
                        logger.error(traceback.format_exc())

                total_updated += file_updated
                logger.info(f"Updated {file_updated} articles from {zip_file}")

            except Exception as e:
                logger.error(f"Error processing {zip_file}: {str(e)}")
                logger.error(traceback.format_exc())

        logger.info(
            f"Finished processing all files. Updated {total_updated} articles with combined embeddings"
        )
        return total_updated