import logging

import requests

from backend.article_search_service import ArticleSearchService
from backend.publication_clustering import PublicationClustering
from backend.affiliations_analyzer import AffiliationsAnalyzer
from backend.utils import convert_numpy_types, build_analytics, strip_heavy
from backend.config import HOST, PORT


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class SearchAndClusterService:
    def __init__(
        self,
        host=HOST,
        port=PORT,
        index_name="scientific_articles",
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        device=None,
    ):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"

        self.search_service = ArticleSearchService(
            host=host,
            port=port,
            index_name=index_name,
            model_name=model_name,
            device=device,
        )

        self.clustering_service = PublicationClustering(es_url=self.url)
        self.affiliation_analyzer = AffiliationsAnalyzer(es_url=self.url)

        logger.info(f"SearchAndClusterService initialized, connected to {self.url}")

    def _scroll_query(self, index: str, body: dict, batch: int = 1000) -> list:

        session = requests.Session()

        body = {
            **body,
            "size": batch,
            "sort": ["_doc"],
            "_source": ["id", "publication_year", "publication_type", "title", "keywords", "author_units", "authors"],
        }

        r = session.post(f"{self.url}/{index}/_search?scroll=2m", json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        sid = data.get("_scroll_id")
        hits = [h["_source"] for h in data["hits"]["hits"]]

        while data["hits"]["hits"]:
            r = session.post(
                f"{self.url}/_search/scroll",
                json={"scroll": "2m", "scroll_id": sid},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            sid = data.get("_scroll_id")
            hits.extend(h["_source"] for h in data["hits"]["hits"])

        try:
            session.delete(
                f"{self.url}/_search/scroll", json={"scroll_id": sid}, timeout=10
            )
        except Exception:
            pass
        return hits

    def get_publications_by_unit(
        self,
        unit: str,
        size=None,
        from_: int = 0,
        filters=None,
        cluster_results: bool = True,
        lite: bool = False,
    ):

        try:
            direct_query: dict = {"term": {"author_units": unit}}

            if filters:
                extra = [
                    {"terms": {k: v}} if isinstance(v, list) else {"term": {k: v}}
                    for k, v in filters.items()
                ]
                direct_query = {"bool": {"must": [direct_query], "filter": extra}}

            probe = requests.post(
                f"{self.url}/scientific_articles/_search",
                json={"query": direct_query, "size": 0},
                timeout=10,
            ).json()

            if probe["hits"]["total"]["value"] > 0:
                logger.info("Using optimized query with author_units for '%s'", unit)

                if size is None or size <= 0:
                    pubs = self._scroll_query(
                        "scientific_articles",
                        {"query": direct_query},
                    )
                else:
                    resp = requests.post(
                        f"{self.url}/scientific_articles/_search",
                        json={
                            "query": direct_query,
                            "size": size,
                            "from": from_,
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    pubs = [h["_source"] for h in resp.json()["hits"]["hits"]]

                author_total = requests.post(
                    f"{self.url}/authors/_search?size=0",
                    json={"query": {"term": {"unit": unit}}},
                    timeout=10,
                ).json()["hits"]["total"]["value"]

                result = {
                    "unit": unit,
                    "author_count": author_total,
                    "publication_count": len(pubs),
                    "publications": pubs,
                    "analytics": build_analytics(pubs),
                    "used_optimized_query": True,
                }
                if cluster_results and len(pubs) >= 3:
                    result["clustering_results"] = (
                        self.clustering_service.cluster_publications(
                            publications=pubs, method="auto"
                        )
                    )

                if lite:
                    for pub in pubs:
                        strip_heavy(pub, keep_keywords=True)

                return convert_numpy_types(result)

        except Exception as exc:
            logger.info(
                "Optimized path failed – switching to traditional. Reason: %s", exc
            )

        authors_resp = requests.post(
            f"{self.url}/authors/_search",
            json={
                "size": 5000,
                "query": {"match": {"unit": {"query": unit, "fuzziness": "AUTO"}}},
                "_source": ["id"],
            },
            timeout=30,
        )
        authors_resp.raise_for_status()
        author_ids = [h["_source"]["id"] for h in authors_resp.json()["hits"]["hits"]]

        if not author_ids:
            return {"error": f"No authors found for unit '{unit}'"}

        base_query: dict = {"terms": {"authors": author_ids}}
        if filters:
            extra = [
                {"terms": {k: v}} if isinstance(v, list) else {"term": {k: v}}
                for k, v in filters.items()
            ]
            es_query = {"bool": {"must": [base_query], "filter": extra}}
        else:
            es_query = base_query

        if size is None or size <= 0:
            pubs = self._scroll_query("scientific_articles", {"query": es_query})
        else:
            body = {"size": size, "from": from_, "query": es_query}
            resp = requests.post(
                f"{self.url}/scientific_articles/_search",
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            pubs = [h["_source"] for h in resp.json()["hits"]["hits"]]

        if not pubs:
            return {"error": f"No publications found for unit '{unit}'"}

        result = {
            "unit": unit,
            "author_count": len(author_ids),
            "publication_count": len(pubs),
            "publications": pubs,
            "analytics": build_analytics(pubs),
            "used_optimized_query": False,
        }
        if cluster_results and len(pubs) >= 3:
            result["clustering_results"] = self.clustering_service.cluster_publications(
                publications=pubs, method="auto"
            )

        if lite:
            for pub in pubs:
                strip_heavy(pub, keep_keywords=True)

        if "collaborations" not in result:
            result["collaborations"] = (
                self.affiliation_analyzer
                    .analyze_unit_collaboration(unit_name=unit,
                                                top_n=50,
                                                lite=False)
                    .get("collaborations", [])
            )

        return convert_numpy_types(result)

    def search_and_cluster(
        self,
        query,
        size=100,
        search_method="hybrid",
        clustering_method="auto",
        max_clusters=10,
        min_cluster_size=3,
        text_weight=0.3,
        sem_weight=0.7,
        filters=None,
        include_facets=True,
    ):

        if search_method == "text":
            results = self.search_service.text_search(
                query=query, size=size, filters=filters, include_facets=include_facets
            )
        elif search_method == "semantic":
            results = self.search_service.semantic_search(
                query=query,
                size=size,
                filters=filters,
                include_facets=include_facets,
                method="auto",
            )
        else:
            results = self.search_service.hybrid_search(
                query=query,
                size=size,
                text_weight=text_weight,
                sem_weight=sem_weight,
                filters=filters,
                include_facets=include_facets,
            )

        hits = results.get("hits", [])
        if not hits:
            return {
                "search_results": results,
                "clustering_results": {"error": "No search results to cluster"},
            }

        clustering = self.clustering_service.cluster_publications(
            publications=hits,
            method=clustering_method,
            k_max=max_clusters,
            min_cluster_size=min_cluster_size,
        )

        mapping = clustering.get("publication_to_cluster", {})
        for h in hits:
            pid = h.get("id")
            h["cluster"] = mapping.get(pid, -1)

        if len(hits) > 100:
            affiliation = self.affiliation_analyzer.analyze_topic_by_affiliation(
                query=query
            )
        else:
            affiliation = self.affiliation_analyzer.analyze_topic_by_affiliation(hits)

        return {
            "search_results": results,
            "clustering_results": clustering,
            "affiliation_analysis": affiliation,
        }

    def analyze_topic_by_unit(self, query, top_n=10, size=200):

        results = self.search_service.hybrid_search(query=query, size=size)
        hits = results.get("hits", [])
        
        if not hits:
            return {"error": f"No publications found for topic '{query}'"}

        affiliation = self.affiliation_analyzer.analyze_topic_by_affiliation(
            query=query, level="unit"
        )
        
        return {
            "topic": query,
            "total_publications": len(hits),
            "affiliation_analysis": affiliation,
            "publications": hits,
            "results_count": len(hits)
        }
