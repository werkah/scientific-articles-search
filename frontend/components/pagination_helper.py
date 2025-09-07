from typing import Dict, Any, List
import os
import requests
import dash_bootstrap_components as dbc
from dash import html

API_URL: str = os.environ.get("API_URL", "http://localhost:8000")
TIMEOUT: int = int(os.environ.get("PAGINATION_TIMEOUT", 60))


def fetch_all_unit_publications(unit_name: str, *, lite: bool = True) -> Dict[str, Any]:

    try:

        resp = requests.post(
            f"{API_URL}/api/unit_publications",
            json={"unit": unit_name, "size": 0, "cluster_results": False, "lite": lite},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()

        return {"error": f"HTTP {resp.status_code}: {resp.text}"}

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {TIMEOUT}s - please try again."}
    except Exception as exc:
        return {"error": f"Error fetching data: {exc}"}


def extract_collaborations_from_publications(
    unit_data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    from collections import Counter

    unit_name = unit_data.get("unit", "")
    publications = unit_data.get("publications", [])

    if not unit_name or not publications:
        return []

    denormalized = len(publications) > 0 and "author_units" in publications[0]
    counter = Counter()

    for pub in publications:
        if denormalized:
            for other in pub.get("author_units", []):
                if other != unit_name:
                    counter[other] += 1

    return [
        {"unit": other, "joint_publications": cnt}
        for other, cnt in counter.most_common(15)
    ]


def create_pagination(current_page, total_pages, id_prefix="pagination"):

    if total_pages <= 1:
        return html.Div()  
    

    pages_to_show = set()

    pages_to_show.add(1)
    pages_to_show.add(total_pages)
    

    for i in range(max(1, current_page - 1), min(total_pages + 1, current_page + 2)):
        pages_to_show.add(i)
    

    if current_page > 3:
        pages_to_show.add(2)
    if current_page < total_pages - 2:
        pages_to_show.add(total_pages - 1)
    

    pages_list = sorted(list(pages_to_show))
    


    return html.Div(
        [
            html.Span(f"Page {current_page} of {total_pages}", className="me-3"),
            dbc.Pagination(
                id=f"{id_prefix}-pagination",
                max_value=total_pages,
                first_last=True,
                previous_next=True,
                active_page=current_page,
                fully_expanded=False,
                className="justify-content-center pagination-wrap",
                style={
                    "maxWidth": "100%", 
                    "overflowX": "auto", 
                    "display": "flex", 
                    "flexWrap": "wrap"
                },
            ),
        ],
        className="d-flex align-items-center justify-content-center"
    )