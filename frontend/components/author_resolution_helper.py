from __future__ import annotations
from typing import List, Dict, Any
import os
import time
import requests

API_URL: str = os.environ.get("API_URL", "http://localhost:8000")

_author_cache: Dict[str, Dict[str, Any]] = {}


def resolve_author_names(
    author_ids: List[str],
    timeout: int = 5,
    retry_count: int = 2,
) -> Dict[str, Dict[str, Any]]:

    result: Dict[str, Dict[str, Any]] = {}
    ids_to_fetch: List[str] = []

    for aid in author_ids:

        if aid in _author_cache and _author_cache[aid].get("full_name") != f"ID: {aid}":
            result[aid] = _author_cache[aid]
        else:
            _author_cache.setdefault(aid, {"id": aid, "full_name": f"ID: {aid}"})
            result[aid] = _author_cache[aid]
            ids_to_fetch.append(aid)

    if ids_to_fetch:
        try:
            r = requests.post(
                f"{API_URL}/api/authors_bulk",
                json={"ids": ids_to_fetch},
                timeout=timeout * 2,
            )
            if r.status_code == 200:
                for ad in r.json().get("authors", []):
                    ad.setdefault("full_name", f"ID: {ad['id']}")
                    _author_cache[ad["id"]] = ad
                    result[ad["id"]] = ad
                ids_to_fetch = [
                    i
                    for i in ids_to_fetch
                    if _author_cache[i].get("full_name") == f"ID: {i}"
                ]
        except Exception:
            pass

    for aid in ids_to_fetch:
        for attempt in range(retry_count + 1):
            try:
                r = requests.get(f"{API_URL}/api/authors/{aid}", timeout=timeout)
                if r.status_code == 200:
                    data = r.json()
                    data.setdefault("full_name", f"ID: {aid}")
                    _author_cache[aid] = data
                    result[aid] = data
                    break
                if r.status_code == 404:
                    break
            except requests.exceptions.Timeout:
                time.sleep(0.2)
            except Exception:
                break
    return result


def fetch_all_author_publications(author_id: str) -> List[Dict[str, Any]]:

    r = requests.post(
        f"{API_URL}/api/author_publications",
        json={"author_id": author_id, "size": 0, "lite": True},
        timeout=300,
    )
    r.raise_for_status()
    pubs = r.json().get("publications", [])
    print(f"[fetch_all_author_publications] {author_id}: {len(pubs)} pubs")
    return pubs


def extract_coauthors_from_publications(
    publications: List[Dict[str, Any]],
    author_id: str,
    top_n: int = 50,
) -> Dict[str, Any]:

    from collections import Counter

    counter: Counter[str] = Counter()
    for pub in publications:
        for aid in pub.get("authors", []):
            if aid != author_id:
                counter[aid] += 1

    coauthors: List[Dict[str, Any]] = []
    for aid, cnt in counter.most_common(top_n):
        coauthors.append(
            {
                "id": aid,
                "full_name": f"ID: {aid}",
                "unit": "Unknown",
                "subunit": "Unknown",
                "collaboration_count": cnt,
            }
        )

    if coauthors:
        try:
            r = requests.post(
                f"{API_URL}/api/authors_bulk",
                json={"ids": [c["id"] for c in coauthors]},
                timeout=30,
            )
            if r.status_code == 200:
                details = {a["id"]: a for a in r.json().get("authors", [])}
                for c in coauthors:
                    d = details.get(c["id"], {})
                    c.update(
                        {
                            "full_name": d.get("full_name", c["full_name"]),
                            "unit": d.get("unit", c["unit"]),
                            "subunit": d.get("subunit", c["subunit"]),
                        }
                    )
        except Exception:
            pass

    return {"author_id": author_id, "total": len(coauthors), "coauthors": coauthors}


def load_author_data(author_id: str) -> Dict[str, Any]:

    t0 = time.time()

    prof_r = requests.get(f"{API_URL}/api/authors/{author_id}", timeout=30)
    if prof_r.status_code != 200:
        return {"error": f"Author {author_id} not found"}
    author = prof_r.json()

    pubs = fetch_all_author_publications(author_id)

    try:
        co_r = requests.post(
            f"{API_URL}/api/author_coauthors", json={"author_id": author_id}, timeout=60
        )
        if co_r.status_code == 200:
            coauthors = co_r.json()
        else:
            raise ValueError("API error")
    except Exception:
        coauthors = extract_coauthors_from_publications(pubs, author_id)

    print(f"[load_author_data] {author_id}: ready in {time.time() - t0:.1f}s")
    return {
        "author": author,
        "publications": {
            "author_id": author_id,
            "total": len(pubs),
            "publications": pubs,
        },
        "coauthors": coauthors,
    }
