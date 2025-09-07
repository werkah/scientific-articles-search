import os
import json
import requests
import dash
from dash import dcc, html, callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

API_URL = os.environ.get("API_URL", "http://localhost:8000")

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap",
    ],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)

server = app.server
app.title = "Scientific Article Search & Clustering System"

from components.search_panel import create_search_panel
from components.results_panel import create_results_panel
from components.cluster_panel import create_cluster_panel
from components.author_panel import create_author_panel, register_author_callbacks
from components.academic_units import create_academic_units_panel, register_unit_callbacks
from components.author_link_component import create_article_author_links
from components.ui_helpers import (
    create_error_message,
    create_notification,
    loading_modal,
    notification_toast,
    help_modal,
    article_detail_modal,
    create_article_detail_content
)
from components.cluster_visualization import (
    create_enhanced_visualization_panel
)

pagination_styles = dcc.Markdown(
    """
    <style>
    .pagination-wrap {
        flex-wrap: wrap !important;
        justify-content: center !important;
        max-width: 100% !important;
        overflow-x: visible !important;
    }
    
    .pagination-wrap .page-item {
        margin: 2px !important;
    }
    
    .pagination-wrap .page-link {
        min-width: 38px !important;
        text-align: center !important;
    }
    </style>
    """,
    dangerously_allow_html=True,
)

app.layout = dbc.Container(
    [
        pagination_styles,
        dcc.Location(id="url", refresh=False),
        
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Div(
                            [
                                html.H1(
                                    "Scientific Article Search & Clustering System",
                                    className="display-4 text-primary mb-0",
                                ),
                                html.Button(
                                    html.I(className="bi bi-question-circle text-primary"),
                                    id="help-button",
                                    className="btn btn-link",
                                    style={"fontSize": "1.5rem"}
                                ),
                            ],
                            className="d-flex justify-content-between align-items-center",
                        ),
                        html.P(
                            "Search, cluster, and analyze scientific publications with advanced semantic analysis",
                            className="text-muted lead mt-0",
                        ),
                    ],
                    className="p-4 mt-4 bg-light rounded",
                ),
                width=12,
            )
        ),
        
        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    [
                        dbc.Tab(
                            create_search_panel(),
                            label="Search",
                            tab_id="tab-search",
                            label_class_name="fw-bold",
                            tab_class_name="border-bottom",
                            active_label_class_name="text-primary border-primary",
                        ),
                        dbc.Tab(
                            create_cluster_panel(),
                            label="Clustering",
                            tab_id="tab-clustering",
                            label_class_name="fw-bold",
                            tab_class_name="border-bottom",
                            active_label_class_name="text-primary border-primary",
                        ),
                        dbc.Tab(
                            create_author_panel(),
                            label="Authors",
                            tab_id="tab-authors",
                            label_class_name="fw-bold",
                            tab_class_name="border-bottom",
                            active_label_class_name="text-primary border-primary",
                        ),
                        dbc.Tab(
                            create_academic_units_panel(),
                            label="Academic Units",
                            tab_id="tab-units",
                            label_class_name="fw-bold",
                            tab_class_name="border-bottom",
                            active_label_class_name="text-primary border-primary",
                        ),
                    ],
                    id="tabs",
                    active_tab="tab-search",
                    className="nav-fill",
                ),
                width=12,
            ),
            className="mb-4",
        ),
        
        dbc.Row(
            dbc.Col(
                html.Footer(
                    html.Div(
                        [
                            html.P(
                                "© 2025 Scientific Article Search & Clustering System",
                                className="text-center text-muted mb-0",
                            )
                        ]
                    ),
                    className="mt-5 py-3 border-top",
                ),
                width=12,
            )
        ),
        
        dcc.Store(id="search-results-store", storage_type="memory"),
        dcc.Store(id="clustering-results-store", storage_type="memory"),
        dcc.Store(id="advanced-filters-store", storage_type="memory", data={}),
        dcc.Store(id="pagination-store", storage_type="memory", data={"page": 1}),
        dcc.Store(id="current-author-store", storage_type="memory"),
        dcc.Store(id="modal-close-trigger", storage_type="memory", data=None),
        dcc.Store(id="current-unit-store", storage_type="memory"), 
        dcc.Store(id="topic-analysis-store", storage_type="memory"),
        
        notification_toast,
        loading_modal,
        help_modal,
        article_detail_modal,
    ],
    fluid=True,
    className="px-3 px-md-4 py-3",
)


@callback(
    Output("search-results-store", "data"),
    Output("results-container", "children"),
    Output("notification-toast", "children", allow_duplicate=True),
    Output("notification-toast", "header", allow_duplicate=True),
    Output("notification-toast", "is_open", allow_duplicate=True),
    Output("loading-modal", "is_open", allow_duplicate=True),
    Output("pagination-store", "data", allow_duplicate=True),
    Input("search-button", "n_clicks"),
    State("search-input", "value"),
    State("search-method-select", "value"),
    State("search-size-slider", "value"),
    State("year-range-slider", "value"),
    State("publication-type-select", "value"),
    State("advanced-filters-store", "data"),
    prevent_initial_call=True,
)
def search_articles(n_clicks, query, search_method, size, year_range, pub_types, advanced_filters):
    if not n_clicks or not query:
        raise PreventUpdate
    
    
    try:
        filters = {}
        
        if year_range:
            filters["publication_year"] = {"gte": year_range[0], "lte": year_range[1]}

        if pub_types and "all" not in pub_types:
            filters["publication_type"] = pub_types

        if advanced_filters:
            for k, v in advanced_filters.items():
                if v and k not in ("publication_type", "publication_types_or"):
                    filters[k] = v
        
        request_body = {
            "query": query,
            "size": size,
            "from_": 0,
            "search_method": search_method,
            "filters": filters or None,
            "include_facets": True,
        }
        
        response = requests.post(
            f"{API_URL}/api/search",
            json=request_body,
            timeout=90,
        )
        
        if response.status_code != 200:
            error_msg = f"Search error: {response.status_code} - {response.text}"
            error_panel = create_error_message("Search Error", error_msg)
            notification, header, is_open = create_notification(
                error_msg, "Error", False
            )
            return None, error_panel, notification, header, is_open, False, {"page": 1}
            
        results = response.json()
        all_hits = results.get("hits", [])
        facets = results.get("facets", {})
        
        results["hits"] = all_hits
        results.update(
            query=query,
            search_method=search_method,
            size=size,
            filters=filters or None
        )
        
        if not all_hits:
            error_msg = f"No results found for query '{query}' with selected publication types."
            error_panel = create_error_message("Search Error", error_msg)
            notification, header, is_open = create_notification(
                error_msg, "Error", False
            )
            return None, error_panel, notification, header, is_open, False, {"page": 1}
        
        results_panel = create_results_panel(all_hits, facets)
        
        notification, header, is_open = create_notification(
            f"Found {len(all_hits)} articles matching '{query}'", "Search Results", True
        )
        
        pagination_data = {"page": 1, "total_pages": (len(all_hits) + 9) // 10}
        
        return results, results_panel, notification, header, is_open, False, pagination_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = f"Search exception: {str(e)}"
        error_panel = create_error_message("Search Error", error_msg)
        notification, header, is_open = create_notification(f"Search exception: {str(e)}", "Error", False)
        return None, error_panel, notification, header, is_open, False, {"page": 1}

@callback(
    Output("clustering-results-store", "data"),
    Output("cluster-visualization-container", "children"),
    Output("notification-toast", "children", allow_duplicate=True),
    Output("notification-toast", "header", allow_duplicate=True),
    Output("notification-toast", "is_open", allow_duplicate=True),
    Output("loading-modal", "is_open", allow_duplicate=True),
    Input("cluster-button", "n_clicks"),
    State("search-results-store", "data"),
    State("cluster-method-select", "value"),
    State("max-clusters-slider", "value"),
    State("min-cluster-size-slider", "value"),
    State("use-adaptive-switch", "value"),
    prevent_initial_call=True,
)
def cluster_results(
    n_clicks, results_json, cluster_method, max_clusters, min_cluster_size, use_adaptive
):
    if not n_clicks or not results_json:
        raise PreventUpdate
    
    
    try:
        search_results = results_json
        original_query = search_results.get("query", "")
        search_size = search_results.get("size", 100)
        search_method = search_results.get("search_method", "hybrid")
        filters = search_results.get("filters", None)
        
        print(f"Sending clustering query for: {original_query}, method: {cluster_method}, adaptive: {use_adaptive}")
        
        response = requests.post(
            f"{API_URL}/api/cluster",
            json={
                "query": original_query,
                "size": search_size,
                "search_method": search_method,
                "clustering_params": {
                    "method": cluster_method,
                    "max_clusters": max_clusters,
                    "min_cluster_size": min_cluster_size,
                    "adaptive": use_adaptive  
                },
                "filters": filters,
            },
            timeout=90,  
        )
        
        if response.status_code == 200:
            cluster_results = response.json()
            
            print(f"Received response, main keys: {list(cluster_results.keys())}")
            
            clustering_results = cluster_results.get("clustering_results", {})
            clusters = clustering_results.get("clusters", [])
            
            if not clusters:
                print("No clusters in response!")
                error_panel = dbc.Alert(
                    [
                        html.I(className="bi bi-exclamation-triangle me-2"),
                        "No clusters were found. Try different parameters or a different query."
                    ],
                    color="warning",
                    className="text-center p-5",
                )
                notification, header, is_open = create_notification(
                    "No clusters were found. Try different parameters.", "Clustering result", True
                )
                return cluster_results, error_panel, notification, header, is_open, False
            
            print(f"Found {len(clusters)} clusters")
            
            visualization = create_enhanced_visualization_panel(cluster_results)
            

            method_used = clustering_results.get("method", "")
            is_adaptive = "adaptive" in method_used or use_adaptive
            adaptive_info = " with adaptive parameter optimization" if is_adaptive else ""
            
            n_clusters = len(clusters)
            notification, header, is_open = create_notification(
                f"Created {n_clusters} clusters using {method_used}{adaptive_info}",
                "Clustering Complete",
                True,
            )
            
            return cluster_results, visualization, notification, header, is_open, False
        else:
            error_msg = f"Clustering error: {response.status_code} - {response.text}"
            error_panel = create_error_message("Clustering Error", error_msg)
            notification, header, is_open = create_notification(
                error_msg, "Error", False
            )
            return None, error_panel, notification, header, is_open, False
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = f"Clustering exception: {str(e)}"
        error_panel = create_error_message("Clustering Error", error_msg)
        notification, header, is_open = create_notification(error_msg, "Error", False)
        return None, error_panel, notification, header, is_open, False

@callback(
    Output("cluster-button", "disabled"),
    Output("cluster-button-hint", "children"),
    Input("search-results-store", "data"),
    prevent_initial_call=True,
)
def enable_cluster_button(search_results):
    if not search_results or "hits" not in search_results:
        return True, "Please perform a search first to enable clustering"
    
    hits = search_results.get("hits", [])
    
    if not hits:
        return True, "No search results available for clustering"
    
    if len(hits) < 3:
        return True, f"Need at least 3 documents for clustering (found {len(hits)})"
    
    return False, f"Ready to cluster {len(hits)} articles"

@callback(
    Output("help-modal", "is_open"),
    Input("help-button", "n_clicks"),
    Input("close-help-modal", "n_clicks"),
    State("help-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_help_modal(help_clicks, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
        
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "help-button" and help_clicks:
        return True
    elif button_id == "close-help-modal" and close_clicks:
        return False
    
    return is_open

@callback(
    Output("loading-modal", "is_open", allow_duplicate=True),
    Input("search-button", "n_clicks"),
    Input("cluster-button", "n_clicks"),
    Input("author-id-search-button", "n_clicks"),
    Input("author-name-search-button", "n_clicks"),
    Input("unit-search-button", "n_clicks"),
    Input("topic-analysis-button-unit", "n_clicks"),
    prevent_initial_call=True,
)
def show_loading_on_action(search_clicks, cluster_clicks, author_id_clicks, author_name_clicks, 
                           unit_search_clicks, topic_analysis_clicks):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        raise PreventUpdate
    
    return True

@callback(
    Output("article-detail-modal", "is_open", allow_duplicate=True),
    Input("modal-close-trigger", "data"),
    prevent_initial_call=True,
)
def close_modal_on_author_select(trigger):
    if trigger == "close_modal":
        return False
    raise PreventUpdate

@callback(
    Output("tabs", "active_tab"),
    Input("go-to-clustering-button", "n_clicks"),
    prevent_initial_call=True,
)
def go_to_clustering_tab(n_clicks):
    if n_clicks:
        return "tab-clustering"
    raise PreventUpdate

@callback(
    Output("search-params-collapse", "is_open"),
    Input("search-params-button", "n_clicks"),
    State("search-params-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_search_params(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output("results-container", "children", allow_duplicate=True),
    Input("results-pagination", "active_page"),
    State("search-results-store", "data"),
    State("pagination-store", "data"),
    prevent_initial_call=True,
)
def change_page(page_number, search_results, pagination_data):
    if not page_number or not search_results or "hits" not in search_results:
        raise PreventUpdate
    
    hits = search_results.get("hits", [])
    facets = search_results.get("facets", {})
    
    start_idx = (page_number - 1) * 10
    end_idx = min(start_idx + 10, len(hits))
    
    current_page_hits = hits[start_idx:end_idx]
    
    results_panel = create_results_panel(
        hits=current_page_hits, 
        facets=facets, 
        current_page=page_number,
        total_hits=len(hits)
    )
    
    return results_panel

@app.callback(
    Output("article-detail-modal", "is_open"),
    Output("article-detail-title", "children"),
    Output("article-detail-content", "children"),
    Input({"type": "article-card", "id": ALL}, "n_clicks"),
    State("search-results-store", "data"),
    State("current-author-store", "data"),
    State("current-unit-store", "data"),
    State("clustering-results-store", "data"),
    prevent_initial_call=True,
)
def open_article_detail(n_clicks, search_results, author_data, unit_data, clustering_results):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    if not any(x is not None and x > 0 for x in n_clicks):
        raise PreventUpdate
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    article_id = None
    
    try:
        button_data = json.loads(button_id)
        article_id = button_data.get("id")
    except:
        raise PreventUpdate
    
    if not article_id:
        raise PreventUpdate
    
    article_data = None
    
    if search_results and "hits" in search_results:
        for hit in search_results.get("hits", []):
            if hit.get("id") == article_id:
                article_data = hit
                break
    
    if not article_data and author_data and "publications" in author_data.get("publications", {}):
        for pub in author_data["publications"]["publications"]:
            if pub.get("id") == article_id:
                article_data = pub
                break
    
    if not article_data and unit_data and "publications" in unit_data:
        for pub in unit_data.get("publications", []):
            if pub.get("id") == article_id:
                article_data = pub
                break
    
    if not article_data and clustering_results:
        if "search_results" in clustering_results and "hits" in clustering_results["search_results"]:
            for hit in clustering_results["search_results"]["hits"]:
                if hit.get("id") == article_id:
                    article_data = hit
                    break
    
    if not article_data:
        try:
            response = requests.get(f"{API_URL}/api/publications/{article_id}", timeout=10)
            if response.status_code == 200:
                article_data = response.json()
        except Exception as e:
            print(f"Error fetching article details: {e}")
    
    if not article_data:
        return False, "Article Not Found", html.Div("Could not retrieve article details.")
    
    MISSING_HEAVY = not article_data.get("abstract") or not article_data.get("keywords")
    if MISSING_HEAVY:
        try:
            full = requests.get(f"{API_URL}/api/publications/{article_id}", timeout=10).json()
            for heavy in ("abstract", "keywords", "references", "authors"):
                if heavy in full:
                    article_data[heavy] = full[heavy]
        except Exception as exc:
            print(f"[modal] could not fetch full doc for {article_id}: {exc}")

    title = article_data.get("title", "Article Details")
    
    content = create_article_detail_content(article_data)
    
    return True, title, content

@callback(
    Output("article-detail-modal", "is_open", allow_duplicate=True),
    Input("close-article-detail-modal", "n_clicks"),
    State("article-detail-modal", "is_open"),
    prevent_initial_call=True,
)
def close_article_detail_modal(n_clicks, is_open):
    if n_clicks:
        return False
    return is_open

@callback(
    Output("points-info-collapse", "is_open"),
    Input("points-info-button", "n_clicks"),
    State("points-info-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_points_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@callback(
    Output("selected-article-details", "children"),
    Input("scatter-plot", "clickData"),
    State("search-results-store", "data"),
    State("clustering-results-store", "data"),
    prevent_initial_call=True,
)
def display_selected_article_details(click_data, search_results, clustering_results):
    if not click_data or not (search_results or clustering_results):
        raise PreventUpdate
    
    point_data = click_data["points"][0]
    custom_data = point_data.get("customdata", [])
    if not custom_data:
        raise PreventUpdate
    
    publication_id = custom_data[0]
    if not publication_id:
        raise PreventUpdate
    
    article_data = None
    
    if search_results and "hits" in search_results:
        for hit in search_results["hits"]:
            if hit.get("id") == publication_id:
                article_data = hit
                break
    
    if not article_data and clustering_results and "clustering_results" in clustering_results:
        clusters = clustering_results["clustering_results"].get("clusters", [])
        search_results_in_clusters = clustering_results["search_results"]
        
        if search_results_in_clusters and "hits" in search_results_in_clusters:
            for hit in search_results_in_clusters["hits"]:
                if hit.get("id") == publication_id:
                    article_data = hit
                    break
    
    if not article_data:
        try:
            response = requests.get(f"{API_URL}/api/publications/{publication_id}", timeout=10)
            if response.status_code == 200:
                article_data = response.json()
        except Exception as e:
            print(f"Error fetching article details: {e}")
    
    if not article_data:
        return html.Div(
            dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    f"Could not find details for publication ID: {publication_id}"
                ],
                color="warning",
                className="text-center"
            ),
            className="mt-3"
        )
    
    title = article_data.get("title", "No title")
    abstract = article_data.get("abstract", "")
    authors = article_data.get("authors", [])
    year = article_data.get("publication_year", "Unknown")
    pub_type = article_data.get("publication_type", "Unknown")
    keywords = article_data.get("keywords", [])
    
    if len(abstract) > 500:
        abstract = abstract[:497] + "..."
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5(title, className="mb-0"),
            html.Div([
                dbc.Badge(f"Year: {year}", color="primary", className="me-1"),
                dbc.Badge(f"Type: {pub_type}", color="secondary", className="me-1"),
            ], className="mt-2")
        ]),
        dbc.CardBody([
            html.H6("Abstract", className="mb-2"),
            html.P(abstract, className="mb-3"),
            html.H6("Authors", className="mb-2"),
            create_article_author_links(authors, className="mb-3"),
            html.H6("Keywords", className="mb-2"),
            html.Div([
                dbc.Badge(keyword, color="light", text_color="dark", className="me-1 mb-1")
                for keyword in keywords
            ] if keywords else "No keywords"),
            html.Div([
                dbc.Button(
                    "View Full Details",
                    id={"type": "article-card", "id": publication_id},
                    color="primary",
                    className="mt-3",
                    outline=True,
                    size="sm",
                    n_clicks=0
                )
            ], className="text-end")
        ])
    ], className="mt-3 shadow-sm")
            


@callback(
    Output("cluster-details-container", "children"),
    Input("cluster-select", "value"),
    State("clustering-results-store", "data"),
    prevent_initial_call=True,
)
def display_cluster_details(cluster_id, clustering_results):
    if not cluster_id or not clustering_results or cluster_id == "none":
        raise PreventUpdate
    
    try:
        cluster_id_int = int(cluster_id)
    except ValueError:
        cluster_id_int = cluster_id
    
    selected_cluster = None
    clusters = clustering_results.get("clustering_results", {}).get("clusters", [])
    
    for cluster in clusters:
        if cluster.get("id") == cluster_id_int:
            selected_cluster = cluster
            break
    
    if not selected_cluster:
        return dbc.Alert(f"Cluster {cluster_id} not found", color="warning")
    
    publication_ids = selected_cluster.get("publications", [])
    
    if not publication_ids:
        return dbc.Alert("No publications found in this cluster", color="info")
    
    publications = []
    search_results = clustering_results.get("search_results", {})
    hits = search_results.get("hits", [])
    
    for pub_id in publication_ids:
        for hit in hits:
            if hit.get("id") == pub_id:
                publications.append(hit)
                break
    
    keywords = selected_cluster.get("keywords", [])
    keywords_html = html.Div([
        html.Strong("Cluster Keywords: "),
        html.Span([
            dbc.Badge(
                kw[0], 
                color="primary",
                className="me-1 mb-1"
            ) for kw in keywords[:7]
        ])
    ], className="mb-3") if keywords else None
    
    publication_cards = []
    
    for pub in publications:
        pub_id = pub.get("id", "")
        title = pub.get("title", "No title")
        abstract = pub.get("abstract", "No abstract available")
        year = pub.get("publication_year", "Unknown")
        pub_type = pub.get("publication_type", "Unknown")
        authors = pub.get("authors", [])
        
        if len(abstract) > 300:
            abstract = abstract[:297] + "..."
        
        publication_cards.append(
            dbc.Card([
                dbc.CardBody([
                    html.H5(title, className="card-title"),
                    html.Div([
                        dbc.Badge(f"Year: {year}", color="primary", className="me-2"),
                        dbc.Badge(f"Type: {pub_type}", color="secondary", className="me-2"),
                    ], className="mb-2"),
                    html.P(abstract, className="mb-3"),
                    html.P([
                        html.Strong("Authors: "),
                        create_article_author_links(authors)
                    ], className="mb-2") if authors else None,
                    html.Div(
                        dbc.Button(
                            "View Details",
                            id={"type": "article-card", "id": pub_id},
                            color="primary",
                            outline=True,
                            size="sm",
                            className="mt-2",
                            n_clicks=0
                        ),
                        className="text-end",
                    ),
                ])
            ], className="mb-3 shadow-sm")
        )
    
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-diagram-3 me-2"),
                f"Cluster {cluster_id_int + 1} Details"
            ]),
            dbc.CardBody([
                html.Div([
                    html.Strong("Size: "),
                    html.Span(f"{len(publication_ids)} publications")
                ], className="mb-3"),
                keywords_html,
                html.Hr(),
                html.H5(f"Publications in Cluster {cluster_id_int + 1}", className="mb-3"),
                html.Div(publication_cards)
            ])
        ], className="shadow-sm")
    ])


register_unit_callbacks(app)
register_author_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)