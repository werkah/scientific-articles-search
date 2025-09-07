import json
import logging
from collections import Counter
from backend.config import ELASTICSEARCH_URL
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class AffiliationsAnalyzer:
    def __init__(self, es_url=ELASTICSEARCH_URL):
        self.es_url = es_url.rstrip("/")
        self.author_cache = {}
        self.analysis_cache = {}

        self.check_denormalization()

    def check_denormalization(self):

        try:
            r = requests.get(f"{self.es_url}/scientific_articles/_mapping")
            if r.status_code != 200:
                logger.warning("Cannot check mapping")
                self.has_denormalization = False
                return

            mapping = (
                r.json()
                .get("scientific_articles", {})
                .get("mappings", {})
                .get("properties", {})
            )
            self.has_denormalization = "author_units" in mapping

            if self.has_denormalization:
                r = requests.post(
                    f"{self.es_url}/scientific_articles/_count",
                    json={"query": {"exists": {"field": "author_units"}}},
                )

                if r.status_code == 200:
                    denorm_count = r.json().get("count", 0)

                    r = requests.get(f"{self.es_url}/scientific_articles/_count")
                    if r.status_code == 200:
                        total_count = r.json().get("count", 0)

                        if total_count > 0:
                            self.denorm_ratio = denorm_count / total_count
                            logger.info(
                                f"Denormalization ratio: {self.denorm_ratio:.2f} ({denorm_count}/{total_count})"
                            )
                            self.use_hybrid = self.denorm_ratio < 0.8
                        else:
                            self.denorm_ratio = 0
                            self.use_hybrid = True
            else:
                logger.info("No denormalization detected")
                self.use_hybrid = True

        except Exception as e:
            logger.warning(f"Error checking denormalization: {e}")
            self.has_denormalization = False
            self.use_hybrid = True

    def get_author_info(self, author_id):
        if author_id in self.author_cache:
            return self.author_cache[author_id]

        try:
            r = requests.get(f"{self.es_url}/authors/_doc/{author_id}", timeout=5)
            if r.status_code == 200:
                src = r.json().get("_source", {})
                self.author_cache[author_id] = src
                return src
        except Exception as exc:
            logger.error("get_author_info(%s): %s", author_id, exc)

        self.author_cache[author_id] = {}
        return {}

    def get_affiliation_for_author(self, author_id):
        a = self.get_author_info(author_id)
        return a.get("unit"), a.get("subunit")

    def analyze_topic_by_affiliation(
        self, search_results=None, query=None, level="unit", use_cache=True
    ):

        if use_cache and search_results:
            cache_key = (
                f"{level}_{hash(json.dumps([a.get('id', '') for a in search_results]))}"
            )
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]

        if (
            self.has_denormalization
            and query
            and not search_results
            and not self.use_hybrid
        ):
            try:
                field = "author_units" if level == "unit" else "author_subunits"
                body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "abstract^2", "keywords"],
                        }
                    },
                    "size": 0,
                    "aggs": {"affiliations": {"terms": {"field": field, "size": 100}}},
                }

                r = requests.post(
                    f"{self.es_url}/scientific_articles/_search", json=body
                )
                if r.status_code != 200:
                    logger.warning(f"Aggregation query failed: {r.status_code}")
                else:
                    total = r.json().get("hits", {}).get("total", {}).get("value", 0)
                    buckets = (
                        r.json()
                        .get("aggregations", {})
                        .get("affiliations", {})
                        .get("buckets", [])
                    )

                    result = {
                        "total_articles": total,
                        "affiliations": [
                            {
                                "name": b["key"],
                                "count": b["doc_count"],
                                "percentage": (
                                    round(b["doc_count"] / total * 100, 2)
                                    if total > 0
                                    else 0
                                ),
                            }
                            for b in buckets
                        ],
                    }

                    if use_cache:
                        self.analysis_cache[f"{level}_{hash(query)}"] = result
                    return result
            except Exception as e:
                logger.error(f"Error during aggregation analysis: {e}")

        if not search_results and query:
            try:
                if isinstance(query, dict) and "ids" in query:

                    body = {"query": query, "size": 200}
                else:
                    body = {
                        "query": {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "abstract^2", "keywords"],
                            }
                        },
                        "size": 200,
                    }
                r = requests.post(
                    f"{self.es_url}/scientific_articles/_search", json=body
                )
                if r.status_code == 200:
                    search_results = [
                        hit["_source"] for hit in r.json()["hits"]["hits"]
                    ]
                else:
                    return {"total_articles": 0, "affiliations": []}
            except Exception as e:
                logger.error(f"Error searching articles: {e}")
                return {"total_articles": 0, "affiliations": []}

        if not search_results:
            return {"total_articles": 0, "affiliations": []}

        if self.has_denormalization and not self.use_hybrid:
            field = "author_units" if level == "unit" else "author_subunits"
            counts = Counter()

            for art in search_results:
                affiliations = art.get(field, [])
                if affiliations:
                    counts.update(affiliations)
        else:

            counts = Counter()

            for art in search_results:

                field = "author_units" if level == "unit" else "author_subunits"
                if self.has_denormalization and field in art and art[field]:

                    counts.update(art[field])
                else:
                    seen = set()
                    for aid in art.get("authors", []):
                        unit, sub = self.get_affiliation_for_author(aid)
                        aff = unit if level == "unit" else sub
                        if aff:
                            seen.add(aff)
                    counts.update(seen)

        total = len(search_results)
        ranked = [
            {
                "name": aff,
                "count": c,
                "percentage": round(c / total * 100, 2) if total > 0 else 0,
            }
            for aff, c in counts.most_common()
        ]

        result = {"total_articles": total, "affiliations": ranked}

        if use_cache:
            self.analysis_cache[
                f"{level}_{hash(json.dumps([a.get('id', '') for a in search_results]))}"
            ] = result

        return result
    
    def _scroll_query(self, index: str, body: dict, batch: int = 1000) -> list[dict]:

        session = requests.Session()

        body = {**body, "size": batch, "sort": ["_doc"], "_source": True}
        r = session.post(f"{self.es_url}/{index}/_search?scroll=2m", json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        scroll_id = data.get("_scroll_id")
        hits = [h["_source"] for h in data["hits"]["hits"]]

        while data["hits"]["hits"]:
            r = session.post(
                f"{self.es_url}/_search/scroll",
                json={"scroll": "2m", "scroll_id": scroll_id},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            scroll_id = data.get("_scroll_id")
            hits.extend(h["_source"] for h in data["hits"]["hits"])


        try:
            session.delete(f"{self.es_url}/_search/scroll",
                           json={"scroll_id": scroll_id}, timeout=10)
        except Exception:
            pass
        return hits

    def analyze_unit_collaboration(
        self, unit_name, *, top_n: int = 100, lite: bool = False
    ):

        if self.has_denormalization and not self.use_hybrid:
            try:
                body = {
                    "query": {"term": {"author_units": unit_name}},
                    "size": 0,
                    "aggs": {
                        "collaborating_units": {
                            "terms": {"field": "author_units", "size": top_n}
                        }
                    },
                }
                r = requests.post(
                    f"{self.es_url}/scientific_articles/_search", json=body
                )
                r.raise_for_status()
                data = r.json()
                pub_count = data["hits"]["total"]["value"]
                buckets = data["aggregations"]["collaborating_units"]["buckets"]

                collab = [
                    {"unit": b["key"], "joint_publications": b["doc_count"]}
                    for b in buckets
                    if b["key"] != unit_name
                ]

                a_resp = requests.post(
                    f"{self.es_url}/authors/_search?size=0",
                    json={"query": {"term": {"unit": unit_name}}},
                )
                author_cnt = (
                    a_resp.json()["hits"]["total"]["value"]
                    if a_resp.status_code == 200
                    else 0
                )

                return {
                    "unit": unit_name,
                    "authors_count": author_cnt,
                    "publications_count": pub_count,
                    "collaborations": collab,
                    "method": "aggregation",
                }
            except Exception as exc:
                logger.warning("Aggregation path failed (%s) – falling back", exc)

        try:
            pubs: list[dict] = []

            if self.has_denormalization:
                scroll_body = {
                    "query": {"term": {"author_units": unit_name}},
                    "_source": ["author_units"] if lite else True,
                }
                pubs = self._scroll_query(
                    "scientific_articles", scroll_body, batch=1000
                )
                logger.info(
                    "Fallback: downloaded %d publications via author_units", len(pubs)
                )

            if not pubs:

                a_resp = requests.post(
                    f"{self.es_url}/authors/_search",
                    json={
                        "size": 5000,
                        "_source": ["id"],
                        "query": {"term": {"unit": unit_name}},
                    },
                    timeout=30,
                )
                author_ids = [h["_source"]["id"] for h in a_resp.json()["hits"]["hits"]]

                for i in range(0, len(author_ids), 500):
                    batch = author_ids[i : i + 500]
                    p_resp = requests.post(
                        f"{self.es_url}/scientific_articles/_search",
                        json={"query": {"terms": {"authors": batch}}, "size": 1000},
                        timeout=30,
                    )
                    pubs.extend([h["_source"] for h in p_resp.json()["hits"]["hits"]])

            if lite:
                for p in pubs:
                    for heavy in ("abstract", "references"):
                        p.pop(heavy, None)

            coll_counter = Counter()
            for p in pubs:
                if self.has_denormalization and "author_units" in p:
                    units = set(u for u in p["author_units"] if u != unit_name)
                else:
                    units = set()
                    for aid in p.get("authors", []):
                        u, _ = self.get_affiliation_for_author(aid)
                        if u and u != unit_name:
                            units.add(u)
                coll_counter.update(units)

            collaborations = [
                {"unit": u, "joint_publications": c}
                for u, c in coll_counter.most_common()
            ]

            return {
                "unit": unit_name,
                "authors_count": len(
                    {aid for p in pubs for aid in p.get("authors", [])}
                ),
                "publications_count": len(pubs),
                "collaborations": collaborations,
                "method": "fallback",
            }
        except Exception as exc:
            logger.error("Unit collaboration fallback failed: %s", exc, exc_info=True)
            return {"error": f"Error analysing collaboration for '{unit_name}': {exc}"}
