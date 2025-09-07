import logging
import re
import requests
from sentence_transformers import SentenceTransformer
from backend.config import HOST, PORT
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ArticleSearchService:
    def __init__(
        self,
        host=HOST,
        port=PORT,
        index_name="scientific_articles",
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        device=None,
    ):
        import torch

        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.index = index_name
        self.embedding_dim = 384
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code != 200:
                raise ConnectionError(
                    f"Elasticsearch unavailable: HTTP code {response.status_code}"
                )
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Elasticsearch: {e}")
        self.model = SentenceTransformer(
            model_name,
            device=device or ("cuda" if torch.cuda.is_available() else "cpu"),
        )
        logger.info(f"Search service ready (index={self.index})")
        self.knn_available = self._check_index_config()
        self._collection_size = self._get_collection_size()
        logger.info(f"Collection size: {self._collection_size} documents")

    def _get_collection_size(self):

        try:
            response = requests.get(f"{self.base_url}/{self.index}/_count")
            if response.status_code == 200:
                return response.json().get("count", 0)
            return 0
        except Exception as e:
            logger.warning(f"Error getting collection size: {e}")
            return 0

    def _is_large_search(self, size):

        return self._collection_size > 1000000 or size > 1000

    def _get_knn_params(self, size, filters=None):

        k = size * 2
        num_candidates = size * 5

        if filters:

            filter_complexity = 0
            for field, conditions in filters.items():
                if isinstance(conditions, dict):
                    filter_complexity += len(conditions)
                elif isinstance(conditions, list):
                    filter_complexity += min(len(conditions) / 5, 3)
                else:
                    filter_complexity += 1

            k = int(k * (1 + 0.15 * filter_complexity))

            num_candidates = int(num_candidates * (1 + 0.1 * filter_complexity))

        if self._collection_size > 1000000:

            k = max(k, int(size * 3))
            num_candidates = max(num_candidates, int(size * 10))
        elif self._collection_size > 100000:
            k = max(k, int(size * 2.5))
            num_candidates = max(num_candidates, int(size * 7))
        elif self._collection_size > 10000:
            k = max(k, int(size * 2))
            num_candidates = max(num_candidates, int(size * 5))
        else:
            k = max(k, int(size * 1.5))
            num_candidates = max(num_candidates, int(size * 3))

        if size > 100:

            k = int(k * 0.8)
            num_candidates = int(num_candidates * 0.9)
        elif size < 10:
            k = max(k, 20)
            num_candidates = max(num_candidates, 50)

        k = min(k, 1000)
        num_candidates = min(num_candidates, 10000)

        if k >= num_candidates:
            num_candidates = min(k * 2, 10000)

        logger.debug(f"KNN parameters: k={k}, num_candidates={num_candidates}")
        return k, num_candidates

    def _check_index_config(self):

        knn_available = True
        try:
            url = f"{self.base_url}/{self.index}/_mapping"
            response = requests.get(url)
            if response.status_code != 200:
                logger.warning(
                    f"Cannot retrieve index configuration: {response.status_code}"
                )
                return False
            mapping = (
                response.json()
                .get(self.index, {})
                .get("mappings", {})
                .get("properties", {})
            )
            embedding_fields = [
                "title_embedding",
                "abstract_embedding",
                "keywords_embedding",
            ]
            for field in embedding_fields:
                if field not in mapping:
                    logger.warning(f"Field {field} does not exist in the index")
                    knn_available = False
                    continue
                field_config = mapping[field]
                if field_config.get("type") != "dense_vector":
                    logger.warning(f"Field {field} is not of type dense_vector")
                    knn_available = False
                if not field_config.get("index", False):
                    logger.warning(f"Field {field} is not indexed (index: false)")
                    knn_available = False
            return knn_available
        except Exception as e:
            logger.warning(f"Error while checking index configuration: {e}")
            return False

    def _build_filters(self, filters) -> list[dict]:

        if not filters:
            return []

        filter_clauses: list[dict] = []

        for field, conditions in filters.items():

            if field == "publication_type":
                if isinstance(conditions, list):
                    filter_clauses.append({"terms": {field: conditions}})
                else:
                    filter_clauses.append({"term": {field: conditions}})
                continue

            if isinstance(conditions, dict):

                if field == "publication_year":
                    rng = {op: int(v) for op, v in conditions.items()}
                    filter_clauses.append({"range": {field: rng}})
                else:
                    filter_clauses.append({"range": {field: conditions}})
                continue

            if isinstance(conditions, list):

                if field.endswith(".keyword") or field in ("keywords.keyword",):
                    filter_clauses.append({"terms": {field: conditions}})
                else:

                    filter_clauses.append({"terms": {f"{field}.keyword": conditions}})
                continue

            if isinstance(conditions, (int, float, bool)):
                filter_clauses.append({"term": {field: conditions}})
            else:
                if field.endswith(".keyword"):
                    filter_clauses.append({"term": {field: conditions}})
                else:
                    filter_clauses.append({"term": {f"{field}.keyword": conditions}})

        return filter_clauses

    def _embed_query(self, q):

        try:
            vec = self.model.encode(
                [f"query: {q}"], convert_to_numpy=True, normalize_embeddings=True
            )[0]
            return vec.tolist()
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return [0.0] * self.embedding_dim

    def _process_facets(self, aggregations):
        facets = {}
        if "publication_years" in aggregations:
            years = []
            for bucket in aggregations["publication_years"]["buckets"]:
                years.append({"year": bucket["key"], "count": bucket["doc_count"]})
            facets["publication_years"] = sorted(years, key=lambda x: x["year"])
        for facet_name in ["publication_types", "keywords"]:
            if facet_name in aggregations:
                items = []
                for bucket in aggregations[facet_name]["buckets"]:
                    items.append({"value": bucket["key"], "count": bucket["doc_count"]})
                facets[facet_name] = items
        return facets

    def _get_facets_query(self, query_obj):
        return {
            "size": 0,
            "query": query_obj,
            "aggs": {
                "publication_years": {
                    "histogram": {
                        "field": "publication_year",
                        "interval": 1,
                        "min_doc_count": 1,
                    }
                },
                "publication_types": {
                    "terms": {"field": "publication_type.keyword", "size": 20}
                },
                "keywords": {"terms": {"field": "keywords.keyword", "size": 30}},
            },
        }

    def text_search(self, query, size=10, from_=0, filters=None, include_facets=True):

        quoted_parts = []
        normal_parts = []

        quoted_parts = re.findall(r'"([^"]+)"', query)
        normal_parts = re.sub(r'"[^"]+"', " ", query).split()

        should_clauses = []
        must_clauses = []

        for phrase in quoted_parts:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": phrase,
                        "fields": ["title^3", "abstract^2", "keywords"],
                        "type": "phrase",
                        "slop": 0,
                    }
                }
            )

        for term in normal_parts:
            should_clauses.append(
                {
                    "multi_match": {
                        "query": term,
                        "fields": ["title^3", "abstract^2", "keywords"],
                        "operator": "or",
                        "fuzziness": "AUTO",
                    }
                }
            )

        bool_query = {"bool": {}}
        if must_clauses:
            bool_query["bool"]["must"] = must_clauses
        if should_clauses:
            bool_query["bool"]["should"] = should_clauses
            if not must_clauses:
                bool_query["bool"]["minimum_should_match"] = 1

        if not must_clauses and not should_clauses:
            bool_query = {"match_all": {}}

        filter_clauses = self._build_filters(filters)
        if filter_clauses:
            if "bool" not in bool_query:
                bool_query = {"bool": {"must": [{"match_all": {}}]}}
            bool_query["bool"]["filter"] = filter_clauses

        body = {"size": size, "from": from_, "query": bool_query}
        facets_body = self._get_facets_query(bool_query) if include_facets else None
        search_url = f"{self.base_url}/{self.index}/_search"

        try:
            response = requests.post(
                search_url, json=body, headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logger.error(
                    f"Text search error: {response.status_code} - {response.text}"
                )
                return {"hits": [], "facets": {}}

            result = response.json()
            hits = [
                {**hit["_source"], "_score": hit["_score"]}
                for hit in result["hits"]["hits"]
            ]

            facets = {}
            if include_facets and facets_body:
                facets_response = requests.post(
                    search_url,
                    json=facets_body,
                    headers={"Content-Type": "application/json"},
                )
                if facets_response.status_code == 200:
                    facets = self._process_facets(
                        facets_response.json().get("aggregations", {})
                    )

            return {"hits": hits, "facets": facets}

        except Exception as e:
            logger.error(f"Error during text search: {e}")
            return {"hits": [], "facets": {}}

    def _optimized_semantic_search(
        self, query, size=10, min_score=0.5, filters=None, include_facets=True
    ):

        qv = self._embed_query(query)
        title_weight = 0.3
        abstract_weight = 0.5
        keywords_weight = 0.2
        total_weight = title_weight + abstract_weight + keywords_weight
        min_es_score = (min_score * total_weight) + 1.0
        functions = [
            {
                "weight": title_weight,
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.v, 'title_embedding') + 1.0",
                        "params": {"v": qv},
                    }
                },
            },
            {
                "weight": abstract_weight,
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.v, 'abstract_embedding') + 1.0",
                        "params": {"v": qv},
                    }
                },
            },
            {
                "weight": keywords_weight,
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.v, 'keywords_embedding') + 1.0",
                        "params": {"v": qv},
                    }
                },
            },
        ]
        base_query = {
            "bool": {
                "should": [
                    {"exists": {"field": "title_embedding"}},
                    {"exists": {"field": "abstract_embedding"}},
                    {"exists": {"field": "keywords_embedding"}},
                ],
                "minimum_should_match": 1,
            }
        }
        filter_clauses = self._build_filters(filters)
        if filter_clauses:
            base_query["bool"]["filter"] = filter_clauses
        body = {
            "size": size,
            "query": {
                "function_score": {
                    "query": base_query,
                    "functions": functions,
                    "score_mode": "sum",
                    "boost_mode": "replace",
                    "min_score": min_es_score,
                }
            },
        }
        search_url = f"{self.base_url}/{self.index}/_search"
        try:
            response = requests.post(
                search_url, json=body, headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logger.error(
                    f"Optimized semantic search error: {response.status_code} - {response.text}"
                )
                return {"hits": [], "facets": {}}
            result = response.json()
            hits = []
            for hit in result["hits"]["hits"]:
                original_score = hit["_score"]
                normalized_score = (original_score - 1.0) / total_weight
                hits.append({**hit["_source"], "_score": normalized_score})
            facets = {}
            if include_facets:
                facets_body = self._get_facets_query(base_query)
                facets_response = requests.post(
                    search_url,
                    json=facets_body,
                    headers={"Content-Type": "application/json"},
                )
                if facets_response.status_code == 200:
                    facets = self._process_facets(
                        facets_response.json().get("aggregations", {})
                    )
            return {"hits": hits, "facets": facets}
        except Exception as e:
            logger.error(f"Error during optimized semantic search: {e}")
            return {"hits": [], "facets": {}}

    def _knn_semantic_search(self, query, size=10, filters=None, include_facets=True):

        if not self.knn_available:
            logger.warning(
                "KNN unavailable - index configuration does not allow native KNN"
            )
            return self._optimized_semantic_search(
                query, size, 0.5, filters, include_facets
            )

        qv = self._embed_query(query)

        k, num_candidates = self._get_knn_params(size, filters)
        logger.info(f"Using KNN search with k={k}, num_candidates={num_candidates}")

        body = {
            "size": size,
            "knn": {
                "field": "title_embedding",
                "query_vector": qv,
                "k": k,
                "num_candidates": num_candidates,
            },
        }

        filter_clauses = self._build_filters(filters)
        if filter_clauses:
            if len(filter_clauses) == 1:
                body["knn"]["filter"] = filter_clauses[0]
            else:
                body["knn"]["filter"] = {"bool": {"filter": filter_clauses}}

        search_url = f"{self.base_url}/{self.index}/_search"
        try:
            response = requests.post(
                search_url, json=body, headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logger.error(
                    f"KNN search error: {response.status_code} - {response.text}"
                )
                return {"hits": [], "facets": {}}

            result = response.json()
            hits = [
                {**hit["_source"], "_score": hit.get("_score", 0)}
                for hit in result["hits"]["hits"]
            ]

            facets = {}
            if include_facets and hits:
                doc_ids = [hit["id"] for hit in hits if "id" in hit]
                if doc_ids:
                    facets_body = {
                        "size": 0,
                        "query": {"terms": {"id": doc_ids}},
                        "aggs": {
                            "publication_years": {
                                "histogram": {
                                    "field": "publication_year",
                                    "interval": 1,
                                    "min_doc_count": 1,
                                }
                            },
                            "publication_types": {
                                "terms": {
                                    "field": "publication_type.keyword",
                                    "size": 20,
                                }
                            },
                            "keywords": {
                                "terms": {"field": "keywords.keyword", "size": 30}
                            },
                        },
                    }
                    facets_response = requests.post(
                        search_url,
                        json=facets_body,
                        headers={"Content-Type": "application/json"},
                    )
                    if facets_response.status_code == 200:
                        facets = self._process_facets(
                            facets_response.json().get("aggregations", {})
                        )

            return {"hits": hits, "facets": facets}
        except Exception as e:
            logger.error(f"Error during KNN search: {e}")
            return {"hits": [], "facets": {}}

    def semantic_search(
        self,
        query,
        size=10,
        min_score=0.5,
        filters=None,
        include_facets=True,
        method="auto",
    ):

        if method == "auto":

            if self.knn_available and self._is_large_search(size):

                logger.info("Using KNN search for large dataset/query")
                method = "knn"
            else:

                logger.info("Using optimized semantic search for better accuracy")
                method = "optimized"

        if method == "knn":
            return self._knn_semantic_search(query, size, filters, include_facets)
        else:
            return self._optimized_semantic_search(
                query, size, min_score, filters, include_facets
            )

    def hybrid_search(
        self,
        query,
        size=10,
        from_=0,
        text_weight=0.3,
        sem_weight=0.7,
        filters=None,
        include_facets=True,
    ):

        query_vector = self._embed_query(query)
        text_query = {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "abstract^2", "keywords"],
                "operator": "or",
                "fuzziness": "AUTO",
            }
        }
        query_obj = text_query
        filter_clauses = self._build_filters(filters)
        if filter_clauses:
            query_obj = {"bool": {"must": [text_query], "filter": filter_clauses}}
        functions = [
            {
                "weight": sem_weight * 0.3,
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.v, 'title_embedding') + 1.0",
                        "params": {"v": query_vector},
                    }
                },
            },
            {
                "weight": sem_weight * 0.5,
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.v, 'abstract_embedding') + 1.0",
                        "params": {"v": query_vector},
                    }
                },
            },
            {
                "weight": sem_weight * 0.2,
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.v, 'keywords_embedding') + 1.0",
                        "params": {"v": query_vector},
                    }
                },
            },
        ]
        body = {
            "size": size,
            "from": from_,
            "query": {
                "function_score": {
                    "query": query_obj,
                    "functions": functions,
                    "score_mode": "sum",
                    "boost_mode": "multiply",
                    "boost": text_weight,
                }
            },
        }
        search_url = f"{self.base_url}/{self.index}/_search"
        try:
            response = requests.post(
                search_url, json=body, headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logger.error(
                    f"Hybrid search error: {response.status_code} - {response.text}"
                )
                return {"hits": [], "facets": {}}
            result = response.json()
            hits = [
                {**hit["_source"], "_score": hit.get("_score", 0)}
                for hit in result["hits"]["hits"]
            ]
            facets = {}
            if include_facets:
                facets_body = self._get_facets_query(query_obj)
                facets_response = requests.post(
                    search_url,
                    json=facets_body,
                    headers={"Content-Type": "application/json"},
                )
                if facets_response.status_code == 200:
                    facets = self._process_facets(
                        facets_response.json().get("aggregations", {})
                    )
            return {"hits": hits, "facets": facets}
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}")
            return {"hits": [], "facets": {}}

    def get_author_publications(
        self,
        author_id: str,
        size: Optional[int] = None,
        from_: int = 0,
        filters: Optional[dict] = None,
    ) -> List[dict]:

        try:

            meta = requests.get(f"{self.base_url}/authors/_doc/{author_id}", timeout=30)
            if meta.status_code != 200:
                logger.error("Author not found: %s – %s", author_id, meta.status_code)
                return []
            src = meta.json().get("_source", {})
            publication_ids: List[str] = src.get("publications", []) or []
            has_id_list = bool(publication_ids)
            expected = src.get("art_num", 0)
            logger.info(
                "Author %s – expected %d, ID‑list: %d",
                author_id,
                expected,
                len(publication_ids),
            )

            fetch_all = size is None or size <= 0

            if (
                not fetch_all
                and from_ == 0
                and has_id_list
                and size >= len(publication_ids)
                and expected > len(publication_ids)
            ):
                logger.info(
                    "Request size=%s >= ID-list (%s) – scroll",
                    size,
                    len(publication_ids),
                )
                return self._scroll_by_author(author_id, filters)

            if fetch_all:
                return self._scroll_by_author(author_id, filters)

            if has_id_list:
                return self._fetch_subset_by_ids(publication_ids, size, from_, filters)

            return self._paged_search(author_id, size, from_, filters)
        except Exception as exc:
            logger.error("get_author_publications failed: %s", exc, exc_info=True)
            return []

    def _fetch_subset_by_ids(
        self,
        id_list: List[str],
        size: int,
        offset: int,
        filters: Optional[dict],
    ) -> List[dict]:
        start, end = max(0, offset), offset + size
        batch_ids = id_list[start:end]
        query: Dict[str, Any] = {"terms": {"id": batch_ids}}
        if filters:
            query = {"bool": {"must": [query], "filter": self._build_filters(filters)}}
        body = {"size": len(batch_ids), "query": query}
        r = requests.post(
            f"{self.base_url}/{self.index}/_search", json=body, timeout=60
        )
        if r.status_code != 200:
            logger.error("ID subset lookup failed: %s", r.text)
            return []
        return [h["_source"] for h in r.json().get("hits", {}).get("hits", [])]

    def _paged_search(
        self,
        author_id: str,
        size: int,
        offset: int,
        filters: Optional[dict],
    ) -> List[dict]:
        q: Dict[str, Any] = {"term": {"authors": author_id}}
        if filters:
            q = {"bool": {"must": [q], "filter": self._build_filters(filters)}}
        body = {
            "size": size,
            "from": offset,
            "query": q,
            "sort": [{"publication_year": {"order": "desc"}}],
        }
        r = requests.post(
            f"{self.base_url}/{self.index}/_search", json=body, timeout=60
        )
        if r.status_code != 200:
            logger.error("paged search failed: %s", r.text)
            return []
        return [h["_source"] for h in r.json().get("hits", {}).get("hits", [])]

    def _scroll_by_author(self, author_id: str, filters: Optional[dict]) -> List[dict]:
        all_pubs: List[dict] = []
        query: Dict[str, Any] = {"term": {"authors": author_id}}
        if filters:
            query = {"bool": {"must": [query], "filter": self._build_filters(filters)}}
        body = {"size": 1000, "query": query, "sort": ["_doc"]}
        try:
            init = requests.post(
                f"{self.base_url}/{self.index}/_search?scroll=2m", json=body, timeout=60
            )
            if init.status_code != 200:
                logger.error("scroll init failed: %s", init.text)
                return []
            data = init.json()
            scroll_id = data.get("_scroll_id")
            hits = data.get("hits", {}).get("hits", [])
            all_pubs.extend(h["_source"] for h in hits)
            while hits and scroll_id:
                nxt = requests.post(
                    f"{self.base_url}/_search/scroll",
                    json={"scroll": "2m", "scroll_id": scroll_id},
                    timeout=60,
                )
                if nxt.status_code != 200:
                    logger.error("scroll continue failed: %s", nxt.text)
                    break
                data = nxt.json()
                scroll_id = data.get("_scroll_id")
                hits = data.get("hits", {}).get("hits", [])
                all_pubs.extend(h["_source"] for h in hits)
        finally:
            if scroll_id:
                try:
                    requests.delete(
                        f"{self.base_url}/_search/scroll",
                        json={"scroll_id": [scroll_id]},
                        timeout=10,
                    )
                except Exception:
                    pass
        logger.info("scroll finished – %d publications", len(all_pubs))
        return all_pubs
