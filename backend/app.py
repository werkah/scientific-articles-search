import logging
from fastapi import FastAPI, HTTPException, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Dict, List, Any, Optional, Union
import requests
import time
from backend.config import HOST, PORT


try:
    from backend.elasticsearch_service import ElasticsearchService
    from backend.article_search_service import ArticleSearchService
    from backend.search_and_cluster_service import SearchAndClusterService
    from backend.utils import convert_numpy_types
except ImportError:
    from elasticsearch_service import ElasticsearchService
    from article_search_service import ArticleSearchService
    from search_and_cluster_service import SearchAndClusterService
    from utils import convert_numpy_types

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class CustomJSONResponse(JSONResponse):
    def render(self, content):
        return super().render(convert_numpy_types(content))


app = FastAPI(
    title="Scientific Article Search & Clustering API",
    description="API for searching and clustering scientific articles",
    version="1.0.0",
    default_response_class=CustomJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

es_service = ElasticsearchService(host=HOST, port=PORT)
search_service = ArticleSearchService(host=HOST, port=PORT)
search_cluster_service = SearchAndClusterService(host=HOST, port=PORT)


class SearchFilter(BaseModel):
    publication_year: Optional[Dict] = None
    keywords: Optional[List] = None
    publication_type: Optional[Union[str, List[str]]] = None
    
    @field_validator('publication_year')
    @classmethod  
    def validate_year_range(cls, v):
        if v and ('gte' in v or 'lte' in v):
            if 'gte' in v and v['gte'] < 0:
                raise ValueError("Publication year cannot be negative")
            if 'lte' in v and v['lte'] < 0:
                raise ValueError("Publication year cannot be negative")
        return v


class ClusteringParams(BaseModel):
    method: str = "auto"
    max_clusters: int = 10
    min_cluster_size: int = 3


@app.get("/", tags=["System"])
async def root():
    return {
        "status": "ok",
        "system": "Scientific Article Search & Clustering API",
        "version": "1.0.0",
    }


@app.post("/api/unit_publications", tags=["Academic Units"])
async def get_unit_publications(
    unit=Body(..., embed=True),
    size=Body(None, embed=True),
    from_: int = Body(0, embed=True),
    cluster_results=Body(True, embed=True),
    lite: bool = Body(True, embed=True),               
    filters: SearchFilter = Body(None, embed=True),
):
    try:
        filt = filters.model_dump(exclude_none=True) if filters else None
        result = search_cluster_service.get_publications_by_unit(
            unit=unit,
            size=size,
            from_=from_,
            filters=filt,
            cluster_results=cluster_results,
            lite=lite,
        )

        if "error" in result:
            return JSONResponse(status_code=400, content={"detail": result["error"]})

        return convert_numpy_types(result)

    except Exception as e:
        logger.error("Unit publications error: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/unit_collaborations", tags=["Academic Units"])
async def unit_collaborations(unit: str = Body(..., embed=True)):

    try:

        res = search_cluster_service.affiliation_analyzer.analyze_unit_collaboration(
            unit
        )

        if "error" not in res:
            return res

        logger.warning("Affiliation analyzer failed → fallback with author_units")
        pubs_resp = es_service.session.post(
            f"{es_service.url}/scientific_articles/_search",
            json={
                "query": {"term": {"author_units": unit}},
                "_source": ["author_units"],
                "size": 10_000,
            },
            timeout=30,
        )

        if pubs_resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Fallback search failed: HTTP {pubs_resp.status_code}",
            )

        pubs = [h["_source"] for h in pubs_resp.json()["hits"]["hits"]]

        from collections import Counter

        co_units = Counter()
        for pub in pubs:
            for u in set(pub.get("author_units", [])):
                if u != unit:
                    co_units[u] += 1

        collaborations = [
            {"unit": u, "joint_publications": c} for u, c in co_units.most_common()
        ]

        auth_cnt_resp = es_service.session.post(
            f"{es_service.url}/authors/_count",
            json={"query": {"term": {"unit": unit}}},
            timeout=10,
        )
        author_count = (
            auth_cnt_resp.json().get("count", 0)
            if auth_cnt_resp.status_code == 200
            else 0
        )

        return {
            "unit": unit,
            "authors_count": author_count,
            "publications_count": len(pubs),
            "collaborations": collaborations,
            "method": "author_units_fallback",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unit collaborations error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/publications/{publication_id}", tags=["Publications"])
async def get_publication(publication_id):

    try:
        query = {"query": {"term": {"id": publication_id}}}
        response = es_service.search_sync(index=es_service.article_index, body=query)
        hits = response.get("hits", {}).get("hits", [])
        if not hits:
            raise HTTPException(
                status_code=404, detail=f"Publication {publication_id} not found"
            )
        return hits[0]["_source"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving publication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/authors/{author_id}", tags=["Authors"])
async def get_author(author_id):

    try:
        response = es_service.session.get(
            f"{es_service.url}/{es_service.author_index}/_doc/{author_id}"
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Author {author_id} not found")
        response.raise_for_status()
        return response.json().get("_source", {})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving author: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/index_stats", tags=["System"])
async def get_index_stats():

    try:
        article_stats = es_service.get_index_stats(es_service.article_index)
        author_stats = es_service.get_index_stats(es_service.author_index)
        return {"article_index": article_stats, "author_index": author_stats}
    except Exception as e:
        logger.error(f"Index stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", tags=["Search"])
async def search_articles(
    query=Body(..., embed=True),
    size=Body(20, ge=1, le=10000, embed=True),  
    from_=Body(0, ge=0, embed=True),
    search_method=Body("hybrid", embed=True),
    filters: SearchFilter = Body(None, embed=True),
    include_facets=Body(True, embed=True),
):

    try:
        filter_dict = filters.model_dump(exclude_none=True) if filters else None
        if search_method == "text":
            results = search_service.text_search(
                query=query,
                size=size,
                from_=from_,
                filters=filter_dict,
                include_facets=include_facets,
            )
        elif search_method == "semantic":
            results = search_service.semantic_search(
                query=query,
                size=size,
                filters=filter_dict,
                include_facets=include_facets,
            )
        else:
            results = search_service.hybrid_search(
                query=query,
                size=size,
                from_=from_,
                filters=filter_dict,
                include_facets=include_facets,
            )
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        if "parameter cannot be negative" in str(e):
            raise HTTPException(status_code=422, detail="Size or from parameter cannot be negative")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search_authors", tags=["Authors"])
async def search_authors(query=Body(..., embed=True), size=Body(20, embed=True)):

    try:
        es_query = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["full_name^3", "unit", "subunit"],
                    "type": "best_fields",
                    "operator": "or",
                    "fuzziness": "AUTO",
                }
            },
        }

        response = es_service.search_sync(index=es_service.author_index, body=es_query)
        hits = response.get("hits", {}).get("hits", [])

        authors = []
        for hit in hits:
            author = hit["_source"]
            author["_score"] = hit["_score"]
            authors.append(author)

        return {"authors": authors, "total": len(authors), "query": query}
    except Exception as e:
        logger.error(f"Author search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cluster", tags=["Clustering"])
async def cluster_articles(
    query=Body(..., embed=True),
    size=Body(50, embed=True),
    search_method=Body("hybrid", embed=True),
    clustering_params: ClusteringParams = Body(..., embed=True),
    filters: SearchFilter = Body(None, embed=True),
):

    try:
        filter_dict = filters.model_dump(exclude_none=True) if filters else None
        results = search_cluster_service.search_and_cluster(
            query=query,
            size=size,
            search_method=search_method,
            clustering_method=clustering_params.method,
            max_clusters=clustering_params.max_clusters,
            min_cluster_size=clustering_params.min_cluster_size,
            filters=filter_dict,
        )
        results = convert_numpy_types(results)
        return results
    except Exception as e:
        logger.error(f"Clustering error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/topic_analysis", tags=["Analysis"])
async def analyze_topic(
    query=Body(..., embed=True), 
    top_n=Body(10, embed=True),
    size=Body(1000, embed=True)
):
    try:
        results = search_cluster_service.analyze_topic_by_unit(
            query=query, top_n=top_n, size=size
        )
        
        if "error" in results:
            return JSONResponse(status_code=400, content={"detail": results["error"]})
        return results
    except Exception as e:
        logger.error(f"Topic analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/author_publications", tags=["Authors"])
async def get_author_publications(
    author_id=Body(..., embed=True),
    size: int = Body(100, embed=True),
    from_: int = Body(0, embed=True),
    filters: Optional[Dict[str, Any]] = Body(None, embed=True),
):

    try:

        start_time = time.time()

        fetch_all = size == 0
        actual_size = None if fetch_all else size

        logger.info(
            f"Author publications request: id={author_id}, size={size}, fetch_all={fetch_all}, from_={from_}"
        )

        publications = search_service.get_author_publications(
            author_id=author_id, size=actual_size, from_=from_, filters=filters
        )

        execution_time = time.time() - start_time

        logger.info(
            f"Retrieved {len(publications)} publications for author {author_id} in {execution_time:.2f}s"
        )

        return {
            "publications": publications,
            "total": len(publications),
            "author_id": author_id,
            "execution_time": f"{execution_time:.2f}s",
        }

    except Exception as e:
        logger.error(f"Error retrieving author publications: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving author publications: {str(e)}",
        )


@app.post("/api/author_coauthors", tags=["Authors"])
async def get_author_coauthors(author_id=Body(..., embed=True)):

    try:
        publications = search_service.get_author_publications(
            author_id=author_id, size=100
        )
        coauthors = set()
        for pub in publications:
            for aid in pub.get("authors", []):
                if aid != author_id:
                    coauthors.add(aid)
        if not coauthors:
            return {"coauthors": [], "total": 0, "author_id": author_id}
        coauthor_details = []
        for caid in coauthors:
            try:
                response = es_service.session.get(
                    f"{es_service.url}/{es_service.author_index}/_doc/{caid}"
                )
                if response.status_code == 200:
                    coauthor_details.append(response.json().get("_source", {}))
            except:
                continue
        return {
            "coauthors": coauthor_details,
            "total": len(coauthor_details),
            "author_id": author_id,
        }
    except Exception as e:
        logger.error(f"Co-authors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/publications_by_ids", tags=["Publications"])
async def get_publications_by_ids(
    ids: List[str] = Body(..., embed=True),
    filters: Optional[Dict[str, Any]] = Body(None, embed=True),
):

    try:
        if not ids:
            return {"publications": [], "total": 0}

        max_ids_per_request = 500
        all_publications = []

        for i in range(0, len(ids), max_ids_per_request):
            batch_ids = ids[i : i + max_ids_per_request]

            query_body = {"query": {"terms": {"id": batch_ids}}, "size": len(batch_ids)}

            if filters:
                filter_clauses = []
                for field, conditions in filters.items():
                    if isinstance(conditions, dict):
                        filter_clauses.append({"range": {field: conditions}})
                    elif isinstance(conditions, list):
                        filter_clauses.append(
                            {"terms": {f"{field}.keyword": conditions}}
                        )
                    else:
                        filter_clauses.append(
                            {"term": {f"{field}.keyword": conditions}}
                        )

                query_body["query"] = {
                    "bool": {"must": [query_body["query"]], "filter": filter_clauses}
                }

            resp = es_service.session.post(
                f"{es_service.url}/scientific_articles/_search",
                json=query_body,
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"Error fetching batch of publications: {resp.status_code}"
                )
                continue

            batch_publications = [h["_source"] for h in resp.json()["hits"]["hits"]]
            all_publications.extend(batch_publications)

        return {"publications": all_publications, "total": len(all_publications)}

    except Exception as e:
        logger.error(f"Error retrieving publications by IDs: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving publications by IDs: {str(e)}",
        )


@app.post("/api/authors_bulk", tags=["Authors"])
async def get_authors_bulk(
    ids: List[str] = Body(..., embed=True), fields: List[str] = Body(None, embed=True)
):

    try:
        if not ids:
            return {"authors": []}

        if len(ids) > 100:
            ids = ids[:100]
            logger.warning(
                f"Limited authors_bulk request to 100 IDs (requested {len(ids)})"
            )

        authors = []

        body = {"docs": [{"_id": aid} for aid in ids]}

        if fields:
            for doc in body["docs"]:
                doc["_source"] = fields

        resp = es_service.session.post(
            f"{es_service.url}/authors/_mget", json=body, timeout=10
        )

        if resp.status_code != 200:
            return JSONResponse(
                status_code=resp.status_code,
                content={"detail": f"Error fetching authors: {resp.text}"},
            )

        docs = resp.json().get("docs", [])

        for doc in docs:
            if doc.get("found", False):
                authors.append(doc.get("_source", {}))
            else:

                aid = doc.get("_id")
                authors.append({"id": aid, "full_name": f"ID: {aid}"})

        return {"authors": authors}

    except Exception as e:
        logger.error(f"Error fetching authors in bulk: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching authors in bulk: {str(e)}",
        )


@app.post("/api/unit_publications_count", tags=["Academic Units"])
async def get_unit_publication_count(unit=Body(..., embed=True)):

    try:

        direct_query = {"term": {"author_units": unit}}
        probe = requests.post(
            f"{es_service.url}/scientific_articles/_search",
            json={"query": direct_query, "size": 0},
            timeout=10,
        )

        if probe.status_code == 200:
            count = probe.json()["hits"]["total"]["value"]
            if count > 0:
                return {"unit": unit, "count": count}

        authors_resp = requests.post(
            f"{es_service.url}/authors/_search",
            json={
                "size": 5000,
                "query": {
                    "match": {"unit": {"query": unit, "fuzziness": "AUTO"}},
                },
                "_source": ["id"],
            },
            timeout=30,
        )

        if authors_resp.status_code != 200:
            return {"unit": unit, "count": 0}

        author_ids = [
            hit["_source"]["id"] for hit in authors_resp.json()["hits"]["hits"]
        ]

        if not author_ids:
            return {"unit": unit, "count": 0}

        query = {"terms": {"authors": author_ids}}
        count_resp = requests.post(
            f"{es_service.url}/scientific_articles/_search?size=0",
            json={"query": query},
            timeout=30,
        )

        if count_resp.status_code != 200:
            return {"unit": unit, "count": 0}

        count = count_resp.json()["hits"]["total"]["value"]
        return {"unit": unit, "count": count}

    except Exception as e:
        logger.error(f"Error counting unit publications: {e}")
        return {"unit": unit, "count": 0}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
