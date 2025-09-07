import dash_bootstrap_components as dbc
from dash import html


def create_error_message(title, message, details=None):

    return html.Div(
        [
            html.H4(
                [
                    html.I(
                        className="bi bi-exclamation-triangle-fill me-2 text-danger"
                    ),
                    title,
                ],
                className="text-danger",
            ),
            html.P(message, className="mb-2"),
            (
                html.Details(
                    [
                        html.Summary("Error details"),
                        html.Pre(
                            details,
                            className="text-muted mt-2 p-2 border rounded bg-light small",
                            style={"whiteSpace": "pre-wrap"},
                        ),
                    ]
                )
                if details
                else None
            ),
        ],
        className="p-3 bg-light border rounded shadow-sm",
    )




def create_notification(message, header="Notification", is_success=True):

    icon = (
        "bi bi-check-circle-fill me-2"
        if is_success
        else "bi bi-exclamation-circle-fill me-2"
    )
    color = "success" if is_success else "danger"
    return (
        html.Div(
            [html.I(className=icon), html.Span(message)], className=f"text-{color}"
        ),
        header,
        True,
    )


loading_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [html.I(className="bi bi-hourglass-split me-2"), "Processing Request"]
            )
        ),
        dbc.ModalBody(
            [
                html.P(
                    [
                        "Please wait for processing the request. ",
                        "This may take a moment for complex operations.",
                    ],
                    className="text-center mb-4",
                ),
                html.Div(
                    dbc.Spinner(size="lg", color="primary", type="grow"),
                    className="text-center",
                ),
            ]
        ),
    ],
    id="loading-modal",
    is_open=False,
    centered=True,
    backdrop="static",
    keyboard=False,
)


notification_toast = dbc.Toast(
    id="notification-toast",
    header="Notification",
    is_open=False,
    dismissable=True,
    duration=4000,
    style={"position": "fixed", "top": 20, "right": 20, "width": 350, "zIndex": 1000},
)


help_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [html.I(className="bi bi-question-circle me-2"), "System Help"]
            )
        ),
        dbc.ModalBody(
            dbc.Tabs(
                [
                    dbc.Tab(
                        [
                            html.H5("Getting Started", className="mt-3 mb-3"),
                            html.P(
                                [
                                    "This system helps to find and analyze scientific publications ",
                                    "using advanced search, clustering, and analytics capabilities.",
                                ]
                            ),
                            html.H6("Main Features", className="mt-4 mb-2"),
                            dbc.ListGroup(
                                [
                                    dbc.ListGroupItem(
                                        [
                                            html.I(
                                                className="bi bi-search me-2 text-primary"
                                            ),
                                            html.Strong("Search:"),
                                            " Find articles using text-based, semantic, or hybrid search methods",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.I(
                                                className="bi bi-diagram-3 me-2 text-success"
                                            ),
                                            html.Strong("Clustering:"),
                                            " Group similar articles to discover connections",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.I(
                                                className="bi bi-person-badge me-2 text-info"
                                            ),
                                            html.Strong("Authors:"),
                                            " Explore authors and their publication networks",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.I(
                                                className="bi bi-building me-2 text-warning"
                                            ),
                                            html.Strong("Academic Units:"),
                                            " Analyze publications by department and research topics across units",
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                        label="Overview",
                        tab_id="tab-overview",
                    ),
                    dbc.Tab(
                        [
                            html.H5("Search Options", className="mt-3 mb-3"),
                            html.P(
                                [
                                    "The system offers multiple search approaches to find ",
                                    "the most relevant scientific articles.",
                                ]
                            ),
                            html.H6("Search Methods", className="mt-3 mb-2"),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-fonts me-2 text-primary"
                                                    ),
                                                    "Text-based Search",
                                                ]
                                            ),
                                            html.P(
                                                [
                                                    "Looks for exact word matches in articles. ",
                                                    "Best for finding specific terms or phrases.",
                                                ]
                                            ),
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-magic me-2 text-success"
                                                    ),
                                                    "Semantic Search",
                                                ],
                                                className="mt-3",
                                            ),
                                            html.P(
                                                [
                                                    "Uses embeddings to understand the meaning behind the query. ",
                                                    "Good for finding conceptually related articles, even if they ",
                                                    "don't contain your exact search terms.",
                                                ]
                                            ),
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-intersect me-2 text-info"
                                                    ),
                                                    "Hybrid Search",
                                                ],
                                                className="mt-3",
                                            ),
                                            html.P(
                                                [
                                                    "Combines text-based and semantic approaches for more balanced results."
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3",
                            ),
                            html.H6("Filtering Options", className="mt-4 mb-2"),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6("Publication Year Range"),
                                            html.P(
                                                [
                                                    "Limit your search to a specific time period using the year range slider."
                                                ],
                                                className="mb-3",
                                            ),
                                            html.H6("Publication Types"),
                                            html.P(
                                                [
                                                    "Filter by specific publication types such as articles, patents, or books."
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3",
                            ),
                            html.H6("Search Tips", className="mt-4 mb-2"),
                            html.Ul(
                                [
                                    html.Li(
                                        "Use specific, descriptive terms for better results"
                                    ),
                                    html.Li(
                                        "Try different search methods for different types of queries"
                                    ),
                                    html.Li(
                                        "Use filters to narrow down results by year, publication type, etc."
                                    ),
                                    html.Li(
                                        "After searching, try clustering to discover topic groups"
                                    ),
                                    html.Li(
                                        'Use quotation marks for exact phrase matching (e.g., "machine learning")'
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-graph-up-arrow me-2 text-info"
                                    ),
                                    html.Strong("Visualization: "),
                                    "Search results include interactive charts showing publication years, top keywords, and publication types.",
                                ],
                                className="alert alert-info mt-3",
                            ),
                        ],
                        label="Search",
                        tab_id="tab-search-help",
                    ),
                    dbc.Tab(
                        [
                            html.H5("Clustering Explained", className="mt-3 mb-3"),
                            html.P(
                                [
                                    "Clustering automatically groups similar articles together based on their ",
                                    "content, helping to discover connections in your search results.",
                                ]
                            ),
                            html.H6("Clustering Methods", className="mt-3 mb-2"),
                            dbc.ListGroup(
                                [
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("Automatic: "),
                                            "The system chooses clustering method based on your data",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("K-means: "),
                                            "Fast algorithm that creates evenly sized clusters",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("Hierarchical: "),
                                            "Creates a nested structure of clusters",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("HDBSCAN: "),
                                            "Handles noise and varying density patterns in your data",
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.H6(
                                "Understanding Visualization", className="mt-4 mb-2"
                            ),
                            html.P(
                                [
                                    "The system provides multiple ways to visualize clusters:"
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        [
                                            html.Strong("2D Scatter Plot: "),
                                            "Shows clusters in two-dimensional space with each point representing an article",
                                        ]
                                    ),
                                    html.Li(
                                        [
                                            html.Strong("Cluster Details: "),
                                            "Shows publications and statistics for each cluster",
                                        ]
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-lightbulb-fill me-2 text-warning"
                                    ),
                                    html.Strong("Tips:"),
                                    html.Ul(
                                        [
                                            html.Li(
                                                "Click on points in visualizations to see article details"
                                            ),
                                            html.Li(
                                                "Use the cluster dropdown to explore specific clusters"
                                            ),
                                            html.Li(
                                                "Look at cluster keywords to understand the focus"
                                            ),
                                        ],
                                        className="mb-0 mt-2",
                                    ),
                                ],
                                className="alert alert-info mt-3",
                            ),
                        ],
                        label="Clustering",
                        tab_id="tab-clustering-help",
                    ),
                    dbc.Tab(
                        [
                            html.H5("Author Explorer", className="mt-3 mb-3"),
                            html.P(
                                [
                                    "The Authors panel allows you to find and analyze scientific authors, ",
                                    "their publications, collaboration networks, and research trends.",
                                ]
                            ),
                            html.H6("Finding Authors", className="mt-3 mb-2"),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-person-badge me-2 text-primary"
                                                    ),
                                                    "Search by Name",
                                                ]
                                            ),
                                            html.P(
                                                [
                                                    "Enter an author's name to find matching researchers. ",
                                                    "Results show basic information and publication counts.",
                                                ],
                                                className="mb-3",
                                            ),
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-fingerprint me-2 text-success"
                                                    ),
                                                    "Search by ID",
                                                ]
                                            ),
                                            html.P(
                                                [
                                                    "You can directly access author's profile with their ID."
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3",
                            ),
                            html.H6("Author Profile Features", className="mt-4 mb-2"),
                            dbc.ListGroup(
                                [
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("Profile: "),
                                            "Basic information about the author, their unit, and publication summary",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("Publications: "),
                                            "Complete list of author's publications with details and interactive pagination",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("Co-authors: "),
                                            "Network of researchers who have collaborated with this author",
                                        ]
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong("Analytics: "),
                                            "Publication trends over time, common topics, and visualization of research patterns",
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-info-circle me-2 text-info"
                                    ),
                                    html.Strong("Note: "),
                                    "You can click on co-authors to view their profiles, and click on author names in article listings to quickly navigate between related researchers.",
                                ],
                                className="alert alert-info mt-3",
                            ),
                        ],
                        label="Authors",
                        tab_id="tab-authors-help",
                    ),
                    dbc.Tab(
                        [
                            html.H5("Academic Units Analysis", className="mt-3 mb-3"),
                            html.P(
                                [
                                    "This panel enables you to explore academic departments,",
                                    "and analyze how different topics are researched across institutions.",
                                ]
                            ),
                            html.H6("Features", className="mt-3 mb-2"),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-building me-2 text-primary"
                                                    ),
                                                    "Unit Search",
                                                ]
                                            ),
                                            html.P(
                                                [
                                                    "Search for specific academic units to view their publications, ",
                                                    "research trends, and statistics.",
                                                ],
                                                className="mb-3",
                                            ),
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-diagram-3 me-2 text-success"
                                                    ),
                                                    "Topic Analysis",
                                                ]
                                            ),
                                            html.P(
                                                [
                                                    "Explore how specific research topics are distributed and studied ",
                                                    "across different academic units.",
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3",
                            ),
                            html.H6("Visualizations", className="mt-4 mb-2"),
                            html.Ul(
                                [
                                    html.Li(
                                        [
                                            html.Strong("Publication Statistics: "),
                                            "Year trends, publication types, and key research areas",
                                        ]
                                    ),
                                    html.Li(
                                        [
                                            html.Strong("Topic Distribution: "),
                                            "Shows which units are most active in specific research areas",
                                        ]
                                    ),
                                    html.Li(
                                        [
                                            html.Strong("Timeline Analysis: "),
                                            "How research topics evolve over time across different units",
                                        ]
                                    ),
                                    html.Li(
                                        [
                                            html.Strong("Keyword Comparison: "),
                                            "Compares the focus areas between different academic units",
                                        ]
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-lightbulb-fill me-2 text-warning"
                                    ),
                                    html.Strong("Research Tip: "),
                                    "The Topic Analysis feature is especially useful for identifying potential ",
                                    "collaboration opportunities or finding the leading institutions in specific research areas.",
                                ],
                                className="alert alert-info mt-3",
                            ),
                        ],
                        label="Academic Units",
                        tab_id="tab-units-help",
                    ),
                ]
            ),
        ),
        dbc.ModalFooter(
            dbc.Button(
                [html.I(className="bi bi-x-lg me-2"), "Close"],
                id="close-help-modal",
                className="ms-auto",
            )
        ),
    ],
    id="help-modal",
    size="lg",
    is_open=False,
    scrollable=True,
)

article_detail_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle(id="article-detail-title")),
        dbc.ModalBody(
            [
                html.Div(id="article-detail-content"),
            ]
        ),
        dbc.ModalFooter(
            dbc.Button(
                "Close",
                id="close-article-detail-modal",
                className="ms-auto",
                n_clicks=0,
            )
        ),
    ],
    id="article-detail-modal",
    size="lg",
    scrollable=True,
    is_open=False,
)


def create_article_detail_content(article_data):

    from dash import html
    import dash_bootstrap_components as dbc

    from components.author_link_component import create_article_author_links_for_modal

    if not article_data:
        return html.Div("Brak danych artykułu.")

    abstract = article_data.get("abstract", "Brak abstraktu.")
    publication_year = article_data.get("publication_year", "Nieznany")
    publication_type = article_data.get("publication_type", "Nieznany")
    keywords = article_data.get("keywords", [])
    authors = article_data.get("authors", [])
    url = article_data.get("url", "")

    if isinstance(keywords, str):
        keywords = [keywords]

    content = [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Span("Rok publikacji: ", className="fw-bold"),
                                html.Span(f"{publication_year}"),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Span("Typ publikacji: ", className="fw-bold"),
                                html.Span(f"{publication_type}"),
                            ],
                            className="mb-2",
                        ),
                    ],
                    width=12,
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Span("Słowa kluczowe: ", className="fw-bold"),
                                html.Span(", ".join(keywords) if keywords else "Brak"),
                            ],
                            className="mb-2",
                        ),
                    ],
                    width=12,
                    md=6,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H5("Abstrakt", className="mb-2"),
                        html.P(abstract, className="text-justify"),
                    ],
                    width=12,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H5("Autorzy", className="mb-2"),
                        create_article_author_links_for_modal(
                            authors, className="d-flex flex-wrap"
                        ),
                    ],
                    width=12,
                ),
            ],
            className="mb-3",
        ),
    ]

    if url:
        content.append(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Hr(),
                            html.A(
                                "Link do publikacji",
                                href=url,
                                target="_blank",
                                className="btn btn-outline-primary",
                            ),
                        ],
                        width=12,
                        className="text-center",
                    ),
                ]
            )
        )

    return html.Div(content)
