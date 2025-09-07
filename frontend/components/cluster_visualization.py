import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.express as px

import numpy as np
import pandas as pd


from components.visualizations_metrics import create_quality_metrics_visualization


def create_scatter_visualization(clustering_results):
    clusters_data = clustering_results.get("clustering_results", {})
    clusters = clusters_data.get("clusters", [])
    quality = clusters_data.get("quality", {})

    viz_method = quality.get("visualization_method", "")
    if viz_method == "auto":
        n_samples = clusters_data.get("num_publications", 0)
        if n_samples < 50:
            viz_method = "PCA"
        elif n_samples < 5000:
            viz_method = "UMAP"
        else:
            viz_method = "PCA"

    if not clusters:
        return html.Div(
            dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    "No clusters available for visualization",
                ],
                color="warning",
                className="text-center",
            ),
            className="p-5",
        )

    publications_map = {}

    search_results = clustering_results.get("search_results", {})
    if search_results and "hits" in search_results:
        for hit in search_results.get("hits", []):
            if "id" in hit:
                publications_map[hit["id"]] = hit

    all_points = []

    for cluster in clusters:
        cluster_id = cluster.get("id", 0)
        points = cluster.get("points", [])
        publications = cluster.get("publications", [])

        cluster_keywords = []
        if "keywords" in cluster:
            cluster_keywords = [kw for kw, _ in cluster.get("keywords", [])[:3]]

        if not points:
            continue

        for i, point in enumerate(points):
            if isinstance(point, list) and len(point) >= 2:
                pub_id = publications[i] if i < len(publications) else ""

                pub_title = ""
                pub_year = ""
                pub_type = ""
                pub_authors = []

                if pub_id in publications_map:
                    pub_data = publications_map[pub_id]
                    pub_title = pub_data.get("title", "")
                    pub_year = pub_data.get("publication_year", "")
                    pub_type = pub_data.get("publication_type", "")
                    pub_authors = pub_data.get("authors", [])

                    if len(pub_title) > 80:
                        pub_title = pub_title[:77] + "..."

                hover_text = f"Title: {pub_title}<br>"
                if pub_year:
                    hover_text += f"Year: {pub_year}<br>"
                if pub_type:
                    hover_text += f"Type: {pub_type}<br>"
                if pub_authors:
                    authors_text = ", ".join(pub_authors[:3])
                    if len(pub_authors) > 3:
                        authors_text += f" and {len(pub_authors) - 3} more"
                    hover_text += f"Authors: {authors_text}<br>"
                if cluster_keywords:
                    hover_text += f"Cluster keywords: {', '.join(cluster_keywords)}<br>"
                hover_text += f"Publication ID: {pub_id}"

                point_data = {
                    "x": point[0],
                    "y": point[1],
                    "cluster": f"Cluster {cluster_id + 1}",
                    "raw_cluster": cluster_id,
                    "publication_id": pub_id,
                    "hover_text": hover_text,
                    "title": pub_title,
                }
                all_points.append(point_data)

    if not all_points:
        return html.Div(
            dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    "No points data available for visualization. Try different clustering method.",
                ],
                color="warning",
                className="text-center",
            ),
            className="p-5",
        )

    df = pd.DataFrame(all_points)

    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="cluster",
        hover_name="title",
        hover_data={
            "x": False,
            "y": False,
            "cluster": True,
            "raw_cluster": False,
            "publication_id": False,
            "hover_text": True,
            "title": False,
        },
        custom_data=["publication_id"],
        title="Articles Clustered by Semantic Similarity",
        labels={"x": "", "y": "", "cluster": "Cluster", "hover_text": ""},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )

    fig.update_traces(
        marker=dict(size=10, opacity=0.7, line=dict(width=1, color="DarkSlateGrey")),
        selector=dict(mode="markers"),
        hovertemplate="%{customdata[0]}<br>%{hovertext}<extra></extra>",
    )

    fig.update_layout(
        xaxis=dict(
            showticklabels=False,
            showgrid=True,
            gridwidth=0.5,
            gridcolor="rgba(0,0,0,0.1)",
            zeroline=False,
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=True,
            gridwidth=0.5,
            gridcolor="rgba(0,0,0,0.1)",
            zeroline=False,
        ),
        hovermode="closest",
        legend_title="Clusters",
        height=650,  
        margin=dict(l=20, r=20, t=60, b=30),  
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            font=dict(size=10), 

            itemsizing="constant",
            itemwidth=30
        ),
        plot_bgcolor="white",
    )

    return html.Div(
        [
            html.P(
                [
                    "Each point represents an article. Hover over points to see details or click a cluster in the legend to focus on it.",
                    html.Span(
                        f" Visualization method: {viz_method}" if viz_method else "",
                        className="badge bg-secondary ms-2"
                    ) if viz_method else None,
                ],
                className="text-muted mb-2",
            ),
            dcc.Graph(
                id="scatter-plot",
                figure=fig,
                config={
                    "displayModeBar": True,
                    "scrollZoom": True,
                    "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                },
                className="border shadow-sm rounded",
                style={"minHeight": "650px"} 
            ),
            html.Div(id="selected-article-details", className="mt-3"),
        ]
    )



def create_visualization_tabs(clustering_results):
    if not clustering_results:
        return html.Div(
            dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    "No clustering results available. Run clustering to see visualizations.",
                ],
                color="warning",
                className="text-center",
            ),
            className="p-5",
        )

    tabs = dbc.Tabs(
        [
            dbc.Tab(
                create_scatter_visualization(clustering_results),
                label="Scatter Plot",
                tab_id="tab-scatter",
                active_label_class_name="fw-bold text-primary",
            ),
        ],
        id="visualization-tabs",
        active_tab="tab-scatter",
        className="mt-3",
    )

    return html.Div([html.H4("Cluster Visualizations", className="mb-3"), tabs])


def create_cluster_dropdown(clusters):
    if not clusters:
        return dbc.Select(
            id="cluster-select",
            options=[{"label": "No clusters available", "value": "none"}],
            value="none",
            disabled=True,
        )

    options = []
    for cluster in clusters:
        cluster_id = cluster.get("id", 0)
        display_cluster_id = (
            cluster_id + 1 if isinstance(cluster_id, int) else cluster_id
        )

        size = cluster.get("size", 0)
        keywords_text = ""
        if cluster.get("keywords"):
            top_keywords = [kw for kw, _ in cluster.get("keywords", [])[:3]]
            if top_keywords:
                keywords_text = f" - Keywords: {', '.join(top_keywords)}"

        options.append(
            {
                "label": f"Cluster {display_cluster_id} ({size} articles){keywords_text}",
                "value": str(cluster_id),
            }
        )

    return dbc.Select(
        id="cluster-select",
        options=options,
        value=options[0]["value"] if options else None,
        className="mb-3",
    )


def create_enhanced_visualization_panel(clustering_results=None):
    if not clustering_results:
        return html.Div(
            dbc.Alert(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        html.I(className="bi bi-diagram-3 display-4"),
                                        className="text-center mb-3",
                                    ),
                                    html.H5(
                                        "Search for articles and run clustering to see visualizations",
                                        className="text-center mb-3",
                                    ),
                                    html.P(
                                        [
                                            "First, go to the ",
                                            html.Strong("Search"),
                                            " tab to find articles. Then return here and click the ",
                                            html.Strong("Cluster"),
                                            " button to discover patterns.",
                                        ],
                                        className="text-center mb-0",
                                    ),
                                ],
                                width=12,
                                className="py-5",
                            )
                        ]
                    )
                ],
                color="light",
                className="text-center p-0",
            )
        )

    clusters_data = clustering_results.get("clustering_results", {})
    clusters = clusters_data.get("clusters", [])
    method = clusters_data.get("method", "")
    n_clusters = clusters_data.get("n_clusters", 0)
    quality = clusters_data.get("quality", {})

    if not clusters:
        return html.Div(
            dbc.Alert(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.I(className="bi bi-exclamation-triangle me-2"),
                                    html.H5("No clusters found", className="mb-3"),
                                    html.P(
                                        [
                                            "The algorithm couldn't create meaningful clusters with the current parameters. ",
                                            "Try selecting different clustering method or adjusting the parameters.",
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                width=12,
                                className="p-4",
                            )
                        ]
                    )
                ],
                color="warning",
                className="text-center",
            )
        )

    silhouette = quality.get("silhouette", float("nan"))
    silhouette_color = "success"
    if silhouette < 0.3:
        silhouette_color = "danger"
    elif silhouette < 0.5:
        silhouette_color = "warning"

    quality_metrics_panel = create_quality_metrics_visualization(clustering_results)

    is_adaptive = "adaptive" in method.lower() or "parameter_metrics" in quality


    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-bar-chart-fill me-2"),
                                            "Clustering Statistics",
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                [
                                                    html.Strong("Method: "),
                                                    html.Span(method),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.P(
                                                [
                                                    html.Strong("Number of Clusters: "),
                                                    html.Span(str(n_clusters)),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.P(
                                                [
                                                    html.Strong("Silhouette Score: "),
                                                    dbc.Badge(
                                                        (
                                                            f"{silhouette:.3f}"
                                                            if not np.isnan(silhouette)
                                                            else "N/A"
                                                        ),
                                                        color=silhouette_color,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.P(
                                                [
                                                    html.Strong("Noise Points: "),
                                                    html.Span(
                                                        f"{quality.get('share_noise', 0):.1%}"
                                                    ),
                                                ],
                                                className="mb-0",
                                            ),

                                            html.Div(
                                                dbc.Badge(
                                                    "Adaptive parameter optimization",
                                                    color="primary",
                                                    className="mt-2",
                                                ),
                                                className="text-center",
                                                style={"display": "block" if is_adaptive else "none"}
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3 shadow-sm",
                            ),
                            create_points_info_panel(),

                            dbc.Row([
                                dbc.Col([
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    html.I(className="bi bi-list-ul me-2"),
                                                    "Cluster Selection",
                                                ]
                                            ),
                                            dbc.CardBody(
                                                [
                                                    html.P(
                                                        "Select a cluster to view its publications:",
                                                        className="mb-2",
                                                    ),
                                                    create_cluster_dropdown(clusters),
                                                    html.Div(
                                                        dbc.Spinner(
                                                            html.Div(
                                                                id="loading-cluster-details"
                                                            ),
                                                            color="primary",
                                                            size="sm",
                                                        ),
                                                        className="text-center my-3",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        className="mb-3 shadow-sm",
                                    ),
                                ], width=12),
                            ]),

                            html.Div(id="cluster-details-container"),
                        ],
                        width=12,
                        lg=3,
                        className="mb-4",
                    ),
                    dbc.Col(
                        [

                            quality_metrics_panel if quality_metrics_panel else html.Div(),

                            create_visualization_tabs(clustering_results)
                        ], 
                        width=12, 
                        lg=9
                    ),
                ]
            ),
        ]
    )

def create_points_info_panel():
    return dbc.Card(
        [
            dbc.CardHeader(
                [html.I(className="bi bi-info-circle me-2"), "About Point Positioning"]
            ),
            dbc.CardBody(
                [
                    html.P(
                        "Points represent semantic embeddings of articles reduced to 2D space. "
                        "Articles with similar content are positioned closer together."
                    ),
                    dbc.Button(
                        ["Learn more ", html.I(className="bi bi-caret-down-fill")],
                        id="points-info-button",
                        color="link",
                        className="p-0 mb-2",
                    ),
                    dbc.Collapse(
                        [
                            html.P(
                                [
                                    html.Strong("X, Y coordinates: "),
                                    "Generated by dimensionality reduction algorithms (UMAP or PCA) "
                                    "from high-dimensional semantic embeddings.",
                                ],
                                className="mb-1",
                            ),
                            html.P(
                                [
                                    html.Strong("Dimension reduction: "),
                                    "The system automatically selects the best reduction method between PCA, UMAP"
                                    "based on dataset characteristics when using adaptive mode.",
                                ],
                                className="mb-0 text-muted small",
                            ),
                        ],
                        id="points-info-collapse",
                        is_open=False,
                    ),
                ]
            ),
        ],
        className="shadow-sm mb-3",
    )