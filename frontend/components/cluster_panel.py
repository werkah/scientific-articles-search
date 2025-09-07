import dash_bootstrap_components as dbc
from dash import html, dcc


def create_cluster_panel():

    cluster_panel = html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3("Article Clustering"),
                            html.P(
                                "Clustering articles helps discover connections between search results. "
                                "First perform a search, then configure clustering parameters below."
                            ),
                        ],
                        width=12,
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Clustering Parameters"),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Clustering Method"
                                                            ),
                                                            dcc.Dropdown(
                                                                id="cluster-method-select",
                                                                options=[
                                                                    {
                                                                        "label": "Automatic",
                                                                        "value": "auto",
                                                                    },
                                                                    {
                                                                        "label": "K-means",
                                                                        "value": "kmeans",
                                                                    },
                                                                    {
                                                                        "label": "Hierarchical",
                                                                        "value": "hierarchical",
                                                                    },
                                                                    {
                                                                        "label": "HDBSCAN",
                                                                        "value": "hdbscan",
                                                                    },
                                                                    {
                                                                        "label": "Adaptive (recommended)",
                                                                        "value": "adaptive",
                                                                    },
                                                                ],
                                                                value="adaptive",
                                                                clearable=False,
                                                            ),
                                                            html.Div(
                                                                [
                                                                    dbc.Tooltip(
                                                                        "Adaptive mode automatically selects optimal clustering parameters based on data characteristics",
                                                                        target="adaptive-badge",
                                                                        placement="right",
                                                                    ),
                                                                ],
                                                                id="adaptive-badge",
                                                                className="mt-1",
                                                            ),
                                                        ],
                                                        width=12,
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Maximum Number of Clusters"
                                                            ),
                                                            dcc.Slider(
                                                                id="max-clusters-slider",
                                                                min=2,
                                                                max=20,
                                                                step=1,
                                                                value=10,
                                                                marks={
                                                                    2: "2",
                                                                    5: "5",
                                                                    10: "10",
                                                                    15: "15",
                                                                    20: "20",
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                            html.Div(
                                                                "In adaptive mode, this is the upper limit for clusters",
                                                                className="text-muted small mt-1",
                                                            ),
                                                        ],
                                                        width=12,
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Minimum Cluster Size"
                                                            ),
                                                            dcc.Slider(
                                                                id="min-cluster-size-slider",
                                                                min=2,
                                                                max=10,
                                                                step=1,
                                                                value=3,
                                                                marks={
                                                                    2: "2",
                                                                    4: "4",
                                                                    6: "6",
                                                                    8: "8",
                                                                    10: "10",
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                        ],
                                                        width=12,
                                                        md=4,
                                                    ),
                                                ]
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Switch(
                                                            id="use-adaptive-switch",
                                                            label="Use adaptive parameter optimization",
                                                            value=True,
                                                            className="mt-3 mb-1",
                                                        ),
                                                        width=12,
                                                        className="text-center",
                                                    ),
                                                    dbc.Col(
                                                        html.Div(
                                                            "When enabled, the system will automatically find optimal PCA dimensions and number of clusters",
                                                            className="text-muted small mb-3",
                                                        ),
                                                        width=12,
                                                        className="text-center",
                                                    ),
                                                ]
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                "Cluster",
                                                                id="cluster-button",
                                                                color="primary",
                                                                size="lg",
                                                                className="mt-3",
                                                                disabled=True,
                                                            ),
                                                            html.Div(
                                                                "Please perform a search first to enable clustering",
                                                                id="cluster-button-hint",
                                                                className="text-muted small mt-2",
                                                            ),
                                                        ],
                                                        width=12,
                                                        className="text-center",
                                                    )
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            dbc.Alert(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Div(
                                                        html.I(
                                                            className="bi bi-diagram-3 display-4"
                                                        ),
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
                            ),
                            id="cluster-visualization-container",
                        ),
                        width=12,
                    )
                ]
            ),
        ]
    )
    return cluster_panel