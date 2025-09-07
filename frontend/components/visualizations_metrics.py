import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def create_quality_metrics_visualization(clustering_results):

    if not clustering_results:
        return None

    clustering_data = clustering_results.get("clustering_results", {})
    quality = clustering_data.get("quality", {})
    param_metrics = quality.get("parameter_metrics", None)

    if not param_metrics:
        return None

    n_clusters_range = param_metrics.get("n_clusters_range", [])
    silhouette_scores = param_metrics.get("silhouette", [])
    ch_scores = param_metrics.get("calinski_harabasz", [])
    db_scores = param_metrics.get("davies_bouldin", [])
    composite_scores = param_metrics.get("composite", [])
    adjusted_scores = param_metrics.get("adjusted_scores", [])

    if not n_clusters_range or not silhouette_scores:
        return None

    metrics_df = pd.DataFrame(
        {
            "Number of Clusters": n_clusters_range,
            "Silhouette Score": silhouette_scores,
            "Calinski-Harabasz Score": (
                ch_scores if ch_scores else [0] * len(n_clusters_range)
            ),
            "Davies-Bouldin Score": (
                db_scores if db_scores else [0] * len(n_clusters_range)
            ),
            "Composite Score": (
                composite_scores if composite_scores else [0] * len(n_clusters_range)
            ),
            "Adjusted Score": adjusted_scores if adjusted_scores else composite_scores,
        }
    )

    fig_silhouette = go.Figure()
    fig_silhouette.add_trace(
        go.Scatter(
            x=metrics_df["Number of Clusters"],
            y=metrics_df["Silhouette Score"],
            mode="lines+markers",
            name="Silhouette Score",
            line=dict(color="#007bff", width=2),
            marker=dict(size=8, symbol="circle"),
        )
    )

    best_silhouette_idx = metrics_df["Silhouette Score"].argmax()
    best_silhouette = metrics_df["Silhouette Score"].iloc[best_silhouette_idx]
    best_n_for_silhouette = metrics_df["Number of Clusters"].iloc[best_silhouette_idx]

    fig_silhouette.add_trace(
        go.Scatter(
            x=[best_n_for_silhouette],
            y=[best_silhouette],
            mode="markers",
            marker=dict(size=12, symbol="star", color="#007bff"),
            name="Optimal",
        )
    )

    fig_silhouette.update_layout(
        title="Silhouette Score vs Number of Clusters",
        xaxis_title="Number of Clusters",
        yaxis_title="Silhouette Score",
        margin=dict(l=20, r=20, t=50, b=50),
        height=350,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=11),
    )

    fig_composite = go.Figure()
    score_to_use = "Adjusted Score" if adjusted_scores else "Composite Score"

    fig_composite.add_trace(
        go.Scatter(
            x=metrics_df["Number of Clusters"],
            y=metrics_df[score_to_use],
            mode="lines+markers",
            name=score_to_use,
            line=dict(color="#28a745", width=2),
            marker=dict(size=8, symbol="circle"),
        )
    )

    best_composite_idx = metrics_df[score_to_use].argmax()
    best_composite = metrics_df[score_to_use].iloc[best_composite_idx]
    best_n_clusters = metrics_df["Number of Clusters"].iloc[best_composite_idx]

    fig_composite.add_trace(
        go.Scatter(
            x=[best_n_clusters],
            y=[best_composite],
            mode="markers",
            marker=dict(size=12, symbol="star", color="#28a745"),
            name="Selected",
        )
    )

    fig_composite.update_layout(
        title=f"{score_to_use} vs Number of Clusters",
        xaxis_title="Number of Clusters",
        yaxis_title=score_to_use,
        margin=dict(l=20, r=20, t=50, b=50),
        height=350,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=11),
    )

    has_multiple_metrics = (len(ch_scores) > 0 and any(x > 0 for x in ch_scores)) or (
        len(db_scores) > 0 and any(x > 0 for x in db_scores)
    )

    all_metrics_fig = None
    if has_multiple_metrics:

        normalized_df = metrics_df.copy()

        sil_min = min(silhouette_scores)
        sil_max = max(silhouette_scores)
        if sil_max > sil_min:
            normalized_df["Normalized Silhouette"] = [
                (x - sil_min) / (sil_max - sil_min) for x in silhouette_scores
            ]
        else:
            normalized_df["Normalized Silhouette"] = [
                1 if x > 0 else 0 for x in silhouette_scores
            ]

        if ch_scores and max(ch_scores) > 0:
            ch_max = max(ch_scores)
            normalized_df["Normalized CH"] = [x / ch_max for x in ch_scores]
        else:
            normalized_df["Normalized CH"] = [0] * len(n_clusters_range)

        if db_scores and min(db_scores) < float("inf"):
            db_min = min(x for x in db_scores if x < float("inf"))
            db_max = max(x for x in db_scores if x < float("inf"))
            if db_max > db_min:
                normalized_df["Normalized DB"] = [
                    1 - ((x - db_min) / (db_max - db_min)) if x < float("inf") else 0
                    for x in db_scores
                ]
            else:
                normalized_df["Normalized DB"] = [
                    1 if x == db_min else 0 for x in db_scores
                ]
        else:
            normalized_df["Normalized DB"] = [0] * len(n_clusters_range)


        score_col = "Adjusted Score" if adjusted_scores else "Composite Score"
        score_min = min(metrics_df[score_col])
        score_max = max(metrics_df[score_col])
        if score_max > score_min:
            normalized_df["Normalized Composite"] = [
                (x - score_min) / (score_max - score_min) for x in metrics_df[score_col]
            ]
        else:
            normalized_df["Normalized Composite"] = [1] * len(n_clusters_range)

        all_metrics_fig = go.Figure()

        all_metrics_fig.add_trace(
            go.Scatter(
                x=normalized_df["Number of Clusters"],
                y=normalized_df["Normalized Silhouette"],
                mode="lines+markers",
                name="Silhouette",
                line=dict(color="#007bff", width=2),
                marker=dict(size=6),
            )
        )

        if any(x > 0 for x in normalized_df["Normalized CH"]):
            all_metrics_fig.add_trace(
                go.Scatter(
                    x=normalized_df["Number of Clusters"],
                    y=normalized_df["Normalized CH"],
                    mode="lines+markers",
                    name="Calinski-Harabasz",
                    line=dict(color="#dc3545", width=2),
                    marker=dict(size=6),
                )
            )

        if any(x > 0 for x in normalized_df["Normalized DB"]):
            all_metrics_fig.add_trace(
                go.Scatter(
                    x=normalized_df["Number of Clusters"],
                    y=normalized_df["Normalized DB"],
                    mode="lines+markers",
                    name="Davies-Bouldin",
                    line=dict(color="#ffc107", width=2),
                    marker=dict(size=6),
                )
            )

        all_metrics_fig.add_trace(
            go.Scatter(
                x=normalized_df["Number of Clusters"],
                y=normalized_df["Normalized Composite"],
                mode="lines+markers",
                name="Composite Score",
                line=dict(color="#28a745", width=2, dash="dash"),
                marker=dict(size=6),
            )
        )

        all_metrics_fig.add_shape(
            type="line",
            x0=best_n_clusters,
            y0=0,
            x1=best_n_clusters,
            y1=1,
            line=dict(color="black", width=1, dash="dot"),
        )

        all_metrics_fig.update_layout(
            title="Normalized Quality Metrics Comparison",
            xaxis_title="Number of Clusters",
            yaxis_title="Normalized Score (higher is better)",
            margin=dict(l=20, r=20, t=50, b=50),
            height=400,
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5,
                font=dict(size=10),
            ),
            font=dict(size=11),
        )

    optimal_n_clusters = metrics_df["Number of Clusters"].iloc[best_composite_idx]
    method_info = (
        clustering_results.get("clustering_results", {}).get("method", "").split(" ")[0]
    )
    if "PCA" in method_info:
        pca_info = method_info[method_info.find("(PCA=") :]
        pca_dims = (
            pca_info.replace("(PCA=", "").split(",")[0]
            if "," in pca_info
            else pca_info.replace("(PCA=", "").replace(")", "")
        )
    else:
        pca_dims = None

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.I(className="bi bi-graph-up me-2"),
                    "Clustering Quality Metrics",
                ]
            ),
            dbc.CardBody(
                [
                    html.P(
                        [
                            "Adaptive optimization tested different parameter combinations. ",
                            html.Strong(
                                f"Optimal number of clusters: {optimal_n_clusters}"
                            ),
                            " based on multiple quality metrics.",
                            (
                                html.Span(
                                    f" PCA dimensions: {pca_dims}",
                                    className="text-muted",
                                )
                                if pca_dims
                                else None
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dcc.Graph(
                                        figure=fig_silhouette,
                                        config={"displayModeBar": False},
                                    ),
                                ],
                                md=6,
                                className="mb-4",
                            ),
                            dbc.Col(
                                [
                                    dcc.Graph(
                                        figure=fig_composite,
                                        config={"displayModeBar": False},
                                    )
                                ],
                                md=6,
                                className="mb-4",
                            ),
                        ]
                    ),
                    (
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Div(
                                            [
                                                dcc.Graph(
                                                    figure=all_metrics_fig,
                                                    config={"displayModeBar": False},
                                                ),
                                            ],
                                            className="mt-2",
                                        )
                                    ],
                                    width=12,
                                )
                            ]
                        )
                        if all_metrics_fig
                        else None
                    ),
                    html.Hr(),
                    dbc.Accordion(
                        [
                            dbc.AccordionItem(
                                [
                                    html.P(
                                        "Quality metrics used to evaluate clustering:"
                                    ),
                                    html.Ul(
                                        [
                                            html.Li(
                                                [
                                                    html.Strong("Silhouette Score: "),
                                                    "Measures how similar an object is to its own cluster compared to other clusters. Higher is better (range: -1 to 1).",
                                                ]
                                            ),
                                            html.Li(
                                                [
                                                    html.Strong(
                                                        "Calinski-Harabasz Score: "
                                                    ),
                                                    "Ratio of between-cluster dispersion to within-cluster dispersion. Higher is better.",
                                                ]
                                            ),
                                            html.Li(
                                                [
                                                    html.Strong(
                                                        "Davies-Bouldin Score: "
                                                    ),
                                                    "Average similarity between each cluster and its most similar cluster. Lower is better.",
                                                ]
                                            ),
                                            html.Li(
                                                [
                                                    html.Strong("Composite Score: "),
                                                    "Weighted combination of normalized metrics, providing a single quality indicator.",
                                                ]
                                            ),
                                            (
                                                html.Li(
                                                    [
                                                        html.Strong("Adjusted Score: "),
                                                        "Composite score with penalty for too many clusters to prefer simpler models.",
                                                    ]
                                                )
                                                if adjusted_scores
                                                else None
                                            ),
                                        ]
                                    ),
                                ],
                                title="About Quality Metrics",
                            ),
                        ],
                        start_collapsed=True,
                        className="mt-3",
                    ),
                ]
            ),
        ],
        className="mb-4 shadow-sm",
    )
