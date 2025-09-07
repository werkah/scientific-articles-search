import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import requests

from backend.app import app

client = TestClient(app)


@pytest.fixture
def mock_es_service():
    es_service = MagicMock()
    es_service.article_index = "scientific_articles"
    es_service.author_index = "authors"
    es_service.url = "http://localhost:9200"

    es_service.get_index_stats.return_value = {
        "doc_count": 1500,
        "size_bytes": 1024000,
        "field_count": 15,
    }

    es_service.search_sync.return_value = {
        "hits": {
            "total": {"value": 5},
            "hits": [
                {
                    "_id": "001106",
                    "_source": {
                        "id": "001106",
                        "full_name": "Szwed Piotr",
                        "unit": "WEAIiIB",
                    },
                    "_score": 2.0,
                },
                {
                    "_id": "002707",
                    "_source": {
                        "id": "002707",
                        "full_name": "Szwed Henryk",
                        "unit": "WIMiR",
                    },
                    "_score": 1.5,
                },
            ],
        }
    }

    session_mock = MagicMock()
    response_mock = MagicMock()
    response_mock.status_code = 200
    response_mock.json.return_value = {
        "_source": {"id": "001106", "full_name": "Szwed Piotr", "unit": "WEAIiIB"}
    }
    session_mock.get.return_value = response_mock

    post_response_mock = MagicMock()
    post_response_mock.status_code = 200
    post_response_mock.json.return_value = {
        "hits": {
            "total": {"value": 5},
            "hits": [{"_source": {"id": "art1", "title": "Machine Learning Basics"}}],
        }
    }
    session_mock.post.return_value = post_response_mock

    es_service.session = session_mock

    return es_service


@pytest.fixture
def mock_search_service():
    search_service = MagicMock()

    search_service.text_search.return_value = {
        "hits": [
            {
                "id": "art1",
                "title": "Machine Learning Basics",
                "keywords": ["machine learning", "AI"],
                "_score": 0.95,
            },
            {
                "id": "art2",
                "title": "Deep Learning Applications",
                "abstract": "Overview of applications",
                "_score": 0.85,
            },
        ],
        "facets": {
            "publication_years": [
                {"year": 2020, "count": 5},
                {"year": 2021, "count": 7},
            ],
            "keywords": [
                {"value": "machine learning", "count": 10},
                {"value": "neural networks", "count": 8},
            ],
        },
    }

    search_service.semantic_search.return_value = {
        "hits": [
            {
                "id": "art3",
                "title": "Neural Network Architectures",
                "abstract": "Modern architectures",
                "_score": 0.92,
            },
            {
                "id": "art4",
                "title": "Transformer Models",
                "keywords": ["transformers", "NLP"],
                "_score": 0.88,
            },
        ],
        "facets": {
            "publication_years": [
                {"year": 2020, "count": 3},
                {"year": 2022, "count": 4},
            ],
            "keywords": [
                {"value": "transformers", "count": 8},
                {"value": "attention mechanism", "count": 6},
            ],
        },
    }

    search_service.hybrid_search.return_value = {
        "hits": [
            {
                "id": "art1",
                "title": "Machine Learning Basics",
                "authors": ["001106", "002707"],
                "_score": 0.96,
            },
            {
                "id": "art3",
                "title": "Neural Network Architectures",
                "authors": ["001106"],
                "_score": 0.92,
            },
        ],
        "facets": {
            "publication_years": [
                {"year": 2020, "count": 6},
                {"year": 2021, "count": 5},
            ],
            "keywords": [
                {"value": "machine learning", "count": 10},
                {"value": "transformers", "count": 8},
            ],
        },
    }

    search_service.get_author_publications.return_value = [
        {"id": "art1", "title": "Machine Learning Basics", "publication_year": 2021},
        {
            "id": "art3",
            "title": "Neural Network Architectures",
            "publication_year": 2020,
        },
    ]

    return search_service


@pytest.fixture
def mock_affiliation_analyzer():
    affiliation_analyzer = MagicMock()

    affiliation_analyzer.analyze_topic_by_affiliation.return_value = {
        "total_articles": 10,
        "affiliations": [
            {"name": "WEAIiIB", "count": 5, "percentage": 50.0},
            {"name": "WIMiR", "count": 3, "percentage": 30.0},
            {"name": "WI", "count": 2, "percentage": 20.0},
        ],
    }

    affiliation_analyzer.analyze_unit_collaboration.return_value = {
        "unit": "WEAIiIB",
        "authors_count": 10,
        "publications_count": 25,
        "collaborations": [
            {"unit": "WIMiR", "joint_publications": 15},
            {"unit": "WI", "joint_publications": 8},
        ],
        "method": "direct",
    }

    return affiliation_analyzer


@pytest.fixture
def mock_search_cluster_service(mock_search_service, mock_affiliation_analyzer):
    service = MagicMock()

    service.search_service = mock_search_service
    service.affiliation_analyzer = mock_affiliation_analyzer

    service.search_and_cluster.return_value = {
        "search_results": {
            "hits": [
                {"id": "art1", "title": "Machine Learning Basics"},
                {"id": "art2", "title": "Deep Learning Applications"},
            ]
        },
        "clustering_results": {
            "clusters": [
                {
                    "id": 0,
                    "publications": ["art1", "art2"],
                    "size": 2,
                    "keywords": [("machine learning", 5), ("neural networks", 3)],
                    "points": [[0.1, 0.2], [0.3, 0.4]],
                },
                {
                    "id": 1,
                    "publications": ["art3", "art4"],
                    "size": 2,
                    "keywords": [("transformers", 6), ("attention", 4)],
                    "points": [[0.5, 0.6], [0.7, 0.8]],
                },
            ],
            "n_clusters": 2,
            "method": "kmeans",
            "quality": {"silhouette": 0.75, "share_noise": 0.0},
        },
    }

    service.analyze_topic_by_unit.return_value = {
        "topic": "machine learning",
        "total_publications": 15,
        "affiliation_analysis": {
            "total_articles": 15,
            "affiliations": [
                {"name": "WEAIiIB", "count": 8, "percentage": 53.3},
                {"name": "WIMiR", "count": 4, "percentage": 26.7},
                {"name": "WI", "count": 3, "percentage": 20.0},
            ],
        },
        "publications": [
            {"id": "art1", "title": "Machine Learning Basics"},
            {"id": "art2", "title": "Neural Networks"},
        ],
        "results_count": 15,
    }

    service.get_publications_by_unit.return_value = {
        "unit": "WEAIiIB",
        "author_count": 10,
        "publication_count": 25,
        "publications": [
            {"id": "art1", "title": "Machine Learning Basics"},
            {"id": "art2", "title": "Neural Networks"},
        ],
    }

    return service


@pytest.mark.api
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"
    assert "Scientific Article Search & Clustering API" in response.json()["system"]


@pytest.mark.api
@patch("backend.app.es_service")
def test_index_stats(mock_es, mock_es_service):
    mock_es.get_index_stats.return_value = mock_es_service.get_index_stats.return_value

    response = client.get("/api/index_stats")
    assert response.status_code == 200
    data = response.json()
    assert "article_index" in data
    assert "author_index" in data
    assert data["article_index"]["doc_count"] > 0


@pytest.mark.api
@patch("backend.app.es_service")
def test_get_publication(mock_es, mock_es_service):
    mock_es.search_sync.return_value = mock_es_service.search_sync.return_value

    response = client.get("/api/publications/art1")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data


@pytest.mark.api
@patch("backend.app.es_service")
def test_get_publication_not_found(mock_es):

    mock_es.search_sync.return_value = {"hits": {"hits": []}}

    response = client.get("/api/publications/nonexistent_id")
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.api
@patch("backend.app.es_service")
def test_publications_by_ids(mock_es, mock_es_service):
    mock_es.session = mock_es_service.session

    response = client.post(
        "/api/publications_by_ids", json={"ids": ["art1", "art2"], "filters": None}
    )

    assert response.status_code == 200
    data = response.json()
    assert "publications" in data
    assert "total" in data


@pytest.mark.api
@patch("backend.app.search_service")
def test_search_text(mock_search, mock_search_service):
    mock_search.text_search.return_value = mock_search_service.text_search.return_value

    response = client.post(
        "/api/search",
        json={
            "query": "machine learning",
            "size": 20,
            "from_": 0,
            "search_method": "text",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert len(data["hits"]) > 0


@pytest.mark.api
@patch("backend.app.search_service")
def test_search_semantic(mock_search, mock_search_service):
    mock_search.semantic_search.return_value = (
        mock_search_service.semantic_search.return_value
    )

    response = client.post(
        "/api/search",
        json={
            "query": "neural networks",
            "size": 10,
            "from_": 0,
            "search_method": "semantic",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert len(data["hits"]) > 0


@pytest.mark.api
@patch("backend.app.search_service")
def test_search_hybrid(mock_search, mock_search_service):
    mock_search.hybrid_search.return_value = (
        mock_search_service.hybrid_search.return_value
    )

    response = client.post(
        "/api/search",
        json={
            "query": "deep learning",
            "size": 15,
            "from_": 0,
            "search_method": "hybrid",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert len(data["hits"]) > 0


@pytest.mark.api
@patch("backend.app.search_service")
def test_search_with_filters(mock_search, mock_search_service):

    filtered_results = {
        "hits": [
            {
                "id": "art1",
                "title": "Machine Learning Basics",
                "keywords": ["machine learning", "AI"],
                "publication_year": 2021,
                "publication_type": "artykuł w czasopiśmie",
                "_score": 0.95,
            }
        ],
        "facets": {
            "publication_years": [{"year": 2021, "count": 1}],
            "keywords": [
                {"value": "machine learning", "count": 1},
                {"value": "AI", "count": 1},
            ],
        },
    }

    mock_search.hybrid_search.return_value = filtered_results

    response = client.post(
        "/api/search",
        json={
            "query": "machine learning",
            "size": 20,
            "from_": 0,
            "search_method": "hybrid",
            "filters": {
                "publication_year": {"gte": 2020, "lte": 2022},
                "publication_type": [
                    "artykuł w czasopiśmie",
                    "materiały konferencyjne (aut.)",
                ],
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert len(data["hits"]) > 0

    mock_search.hybrid_search.assert_called_with(
        query="machine learning",
        size=20,
        from_=0,
        filters={
            "publication_year": {"gte": 2020, "lte": 2022},
            "publication_type": [
                "artykuł w czasopiśmie",
                "materiały konferencyjne (aut.)",
            ],
        },
        include_facets=True,
    )


@pytest.mark.api
@patch("backend.app.search_service")
def test_search_error_handling(mock_search):
    mock_search.hybrid_search.side_effect = Exception("Search error")

    response = client.post("/api/search", json={"query": "machine learning"})

    assert response.status_code == 500
    assert "detail" in response.json()


@pytest.mark.api
@patch("backend.app.search_service")
def test_search_timeout_error(mock_search):

    mock_search.hybrid_search.side_effect = requests.exceptions.Timeout(
        "Request timed out"
    )

    response = client.post("/api/search", json={"query": "machine learning"})

    assert response.status_code == 500
    assert "detail" in response.json()
    assert "timed out" in response.json()["detail"].lower()


@pytest.mark.api
def test_search_validation_error():
    response = client.post(
        "/api/search", json={"size": 10, "from_": 0, "search_method": "hybrid"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.api
def test_boundary_size_values():
    response = client.post(
        "/api/search",
        json={
            "query": "machine learning",
            "size": 10000,
            "from_": 0,
            "search_method": "hybrid",
        },
    )
    
    assert response.status_code in [200, 400, 422]
    

    response = client.post(
        "/api/search",
        json={
            "query": "machine learning",
            "size": -10,
            "from_": -5,
            "search_method": "hybrid",
        },
    )
    

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.api
@patch("backend.app.es_service")
def test_get_author(mock_es, mock_es_service):
    mock_es.session = mock_es_service.session

    response = client.get("/api/authors/001106")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] == "001106"


@pytest.mark.api
@patch("backend.app.es_service")
def test_get_author_not_found(mock_es):

    session_mock = MagicMock()
    response_mock = MagicMock()
    response_mock.status_code = 404
    session_mock.get.return_value = response_mock
    mock_es.session = session_mock

    response = client.get("/api/authors/nonexistent_id")
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.api
@patch("backend.app.es_service")
def test_search_authors(mock_es, mock_es_service):
    mock_es.search_sync.return_value = mock_es_service.search_sync.return_value

    response = client.post("/api/search_authors", json={"query": "Piotr", "size": 5})

    assert response.status_code == 200
    data = response.json()
    assert "authors" in data
    assert len(data["authors"]) > 0


@pytest.mark.api
@patch("backend.app.search_service")
def test_author_publications(mock_search, mock_search_service):
    mock_search.get_author_publications.return_value = (
        mock_search_service.get_author_publications.return_value
    )

    response = client.post(
        "/api/author_publications", json={"author_id": "001106", "size": 50, "from_": 0}
    )

    assert response.status_code == 200
    data = response.json()
    assert "publications" in data
    assert "author_id" in data
    assert len(data["publications"]) > 0


@pytest.mark.api
@patch("backend.app.search_service")
@patch("backend.app.es_service")
def test_author_coauthors(mock_es, mock_search, mock_search_service, mock_es_service):
    mock_search.get_author_publications.return_value = [
        {"id": "art1", "authors": ["001106", "002707"]},
        {"id": "art2", "authors": ["001106", "003301"]},
    ]

    mock_es.session = mock_es_service.session

    response = client.post("/api/author_coauthors", json={"author_id": "001106"})

    assert response.status_code == 200
    data = response.json()
    assert "coauthors" in data
    assert "author_id" in data


@pytest.mark.api
@patch("backend.app.es_service")
def test_authors_bulk(mock_es, mock_es_service):
    mock_es.session = mock_es_service.session

    response = client.post(
        "/api/authors_bulk",
        json={"ids": ["001106", "002707"], "fields": ["id", "full_name", "unit"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "authors" in data


@pytest.mark.api
@patch("backend.app.es_service")
def test_authors_bulk_empty_list(mock_es):

    response = client.post("/api/authors_bulk", json={"ids": []})

    assert response.status_code == 200
    data = response.json()
    assert "authors" in data
    assert data["authors"] == []


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_cluster(mock_service, mock_search_cluster_service):
    mock_service.search_and_cluster.return_value = (
        mock_search_cluster_service.search_and_cluster.return_value
    )

    response = client.post(
        "/api/cluster",
        json={
            "query": "machine learning",
            "size": 50,
            "search_method": "hybrid",
            "clustering_params": {
                "method": "kmeans",
                "max_clusters": 10,
                "min_cluster_size": 3,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "search_results" in data
    assert "clustering_results" in data
    assert "n_clusters" in data["clustering_results"]


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_cluster_algorithm_failure(mock_service):

    mock_service.search_and_cluster.side_effect = ValueError(
        "Clustering failed: insufficient data"
    )

    response = client.post(
        "/api/cluster",
        json={
            "query": "machine learning",
            "size": 50,
            "search_method": "hybrid",
            "clustering_params": {
                "method": "kmeans",
                "max_clusters": 10,
                "min_cluster_size": 3,
            },
        },
    )

    assert response.status_code == 500
    assert "detail" in response.json()
    assert "clustering failed" in response.json()["detail"].lower()


@pytest.mark.api
def test_cluster_validation_error():
    response = client.post(
        "/api/cluster",
        json={"query": "machine learning", "size": 50, "search_method": "hybrid"},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_topic_analysis(mock_service, mock_search_cluster_service):
    mock_service.analyze_topic_by_unit.return_value = (
        mock_search_cluster_service.analyze_topic_by_unit.return_value
    )

    response = client.post(
        "/api/topic_analysis",
        json={"query": "neural networks", "top_n": 10, "size": 500},
    )

    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert "affiliation_analysis" in data
    assert "publications" in data
    assert "results_count" in data
    assert data["topic"] == "machine learning"


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_topic_analysis_empty_result(mock_service):

    mock_service.analyze_topic_by_unit.return_value = {
        "error": "No publications found for topic 'obscure topic'"
    }

    response = client.post(
        "/api/topic_analysis", json={"query": "obscure topic", "top_n": 10, "size": 500}
    )

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "no publications found" in response.json()["detail"].lower()


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_unit_publications(mock_service, mock_search_cluster_service):
    mock_service.get_publications_by_unit.return_value = (
        mock_search_cluster_service.get_publications_by_unit.return_value
    )

    response = client.post(
        "/api/unit_publications",
        json={
            "unit": "WEAIiIB",
            "size": 100,
            "from_": 0,
            "cluster_results": True,
            "lite": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "unit" in data
    assert "publications" in data


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_unit_publications_with_filters(mock_service, mock_search_cluster_service):

    filtered_result = {
        "unit": "WEAIiIB",
        "author_count": 5,
        "publication_count": 10,
        "publications": [
            {
                "id": "art1",
                "title": "Machine Learning Basics",
                "publication_year": 2021,
                "publication_type": "artykuł w czasopiśmie",
            }
        ],
    }

    mock_service.get_publications_by_unit.return_value = filtered_result

    response = client.post(
        "/api/unit_publications",
        json={
            "unit": "WEAIiIB",
            "size": 100,
            "from_": 0,
            "cluster_results": True,
            "lite": True,
            "filters": {
                "publication_year": {"gte": 2020, "lte": 2022},
                "publication_type": ["artykuł w czasopiśmie"],
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "unit" in data
    assert "publications" in data
    assert len(data["publications"]) > 0

    mock_service.get_publications_by_unit.assert_called_with(
        unit="WEAIiIB",
        size=100,
        from_=0,
        filters={
            "publication_year": {"gte": 2020, "lte": 2022},
            "publication_type": ["artykuł w czasopiśmie"],
        },
        cluster_results=True,
        lite=True,
    )


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_unit_publications_error(mock_service):
    mock_service.get_publications_by_unit.return_value = {}

    response = client.post(
        "/api/unit_publications",
        json={
            "unit": "Nonexistent Unit",
            "size": None,
            "from_": 0,
            "cluster_results": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {}


@pytest.mark.api
@patch("backend.app.es_service")
def test_unit_publications_count(mock_es, mock_es_service):
    mock_es.session = mock_es_service.session

    response = client.post("/api/unit_publications_count", json={"unit": "WEAIiIB"})

    assert response.status_code == 200
    data = response.json()
    assert "unit" in data
    assert "count" in data


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_unit_collaborations(mock_service, mock_search_cluster_service):
    mock_service.affiliation_analyzer = mock_search_cluster_service.affiliation_analyzer

    response = client.post("/api/unit_collaborations", json={"unit": "WEAIiIB"})

    assert response.status_code == 200
    data = response.json()
    assert "unit" in data
    assert "collaborations" in data


@pytest.mark.api
@patch("backend.app.search_cluster_service")
def test_unit_collaborations_error(mock_service):

    mock_service.affiliation_analyzer.analyze_unit_collaboration.return_value = {
        "error": "Error analyzing collaboration for 'Nonexistent Unit': Unit not found"
    }

    mock_service.es_service = MagicMock()
    es_session_mock = MagicMock()
    response_mock = MagicMock()

    response_mock.status_code = 500
    response_mock.json.return_value = {"error": "Internal error"}
    response_mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Internal error"
    )
    es_session_mock.post.return_value = response_mock
    mock_service.es_service.session = es_session_mock
    mock_service.es_service.url = "http://localhost:9200"

    response = client.post(
        "/api/unit_collaborations", json={"unit": "Nonexistent Unit"}
    )

    if response.status_code == 200:

        assert "collaborations" in response.json()
        assert len(response.json()["collaborations"]) == 0
    else:
        assert response.status_code in [400, 500]
