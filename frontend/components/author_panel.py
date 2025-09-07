import dash
from dash import html, dcc, Input, Output, State, ALL, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import requests
import os
import plotly.express as px
import traceback
import pandas as pd

try:
    from components.author_resolution_helper import (
        load_author_data,
        resolve_author_names,
    )
except ImportError:

    def load_author_data(author_id):
        API_URL = os.environ.get("API_URL", "http://localhost:8000")
        try:
            response = requests.get(f"{API_URL}/api/authors/{author_id}", timeout=10)
            if response.status_code == 200:
                return {"author": response.json(), "author_id": author_id}
            return {"error": f"Author with ID '{author_id}' not found"}
        except Exception as e:
            return {"error": f"Error fetching author data: {str(e)}"}

    def resolve_author_names(author_ids, timeout=5, retry_count=2):
        return {aid: {"id": aid, "full_name": f"ID: {aid}"} for aid in author_ids}


API_URL = os.environ.get("API_URL", "http://localhost:8000")


def create_author_panel():
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3("Author Explorer", className="mb-3"),
                            html.P(
                                "Search for authors by name or ID to explore their publications and co-authorship network.",
                                className="text-muted",
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
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-person-badge me-2"),
                                            "Search by Name",
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.InputGroup(
                                                [
                                                    dbc.InputGroupText(
                                                        [
                                                            html.I(
                                                                className="bi bi-search me-2"
                                                            ),
                                                            "Name",
                                                        ]
                                                    ),
                                                    dbc.Input(
                                                        id="author-name-input",
                                                        placeholder="Enter author name",
                                                        type="text",
                                                    ),
                                                    dbc.Button(
                                                        "Search",
                                                        id="author-name-search-button",
                                                        color="primary",
                                                        n_clicks=0,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Div(id="author-name-search-results"),
                                        ]
                                    ),
                                ],
                                className="mb-3 shadow-sm",
                            )
                        ],
                        width=12,
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-fingerprint me-2"),
                                            "Search by ID",
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.InputGroup(
                                                [
                                                    dbc.InputGroupText(
                                                        [
                                                            html.I(
                                                                className="bi bi-search me-2"
                                                            ),
                                                            "ID",
                                                        ]
                                                    ),
                                                    dbc.Input(
                                                        id="author-id-input",
                                                        placeholder="Enter author ID",
                                                        type="text",
                                                    ),
                                                    dbc.Button(
                                                        "Search",
                                                        id="author-id-search-button",
                                                        color="primary",
                                                        n_clicks=0,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3 shadow-sm",
                            )
                        ],
                        width=12,
                        md=6,
                    ),
                ]
            ),
            dbc.Row([dbc.Col([html.Div(id="author-info-container")], width=12)]),
            dcc.Store(
                id="author-publications-pagination",
                data={"page": 1, "per_page": 10, "total_publications": 0},
            ),
        ]
    )


def create_improved_publication_types_chart(types_data):
    import plotly.express as px
    import pandas as pd

    df = pd.DataFrame(types_data)

    if "type" not in df.columns or "count" not in df.columns:
        return None

    total = df["count"].sum()

    df["percentage"] = (df["count"] / total * 100).round(1)

    if len(df) > 5:
        top_5 = df.nlargest(5, "count")
        other_sum = df.iloc[5:]["count"].sum()
        other_pct = df.iloc[5:]["percentage"].sum()

        other_row = pd.DataFrame(
            [{"type": "pozostałe", "count": other_sum, "percentage": other_pct}]
        )

        df = pd.concat([top_5, other_row], ignore_index=True)

    df["hover_text"] = df.apply(
        lambda x: f"{x['type']}: {x['count']} ({x['percentage']}%)", axis=1
    )

    df = df.sort_values("count", ascending=False)

    fig = px.pie(
        df,
        values="count",
        names="type",
        title="Publication Types",
        template="plotly_white",
        hover_data=["hover_text"],
        color_discrete_sequence=px.colors.qualitative.Plotly,
    )

    fig.update_traces(
        textinfo="percent+label",
        textposition="inside",
        textfont_size=12,
        insidetextfont=dict(color="white"),
        hovertemplate="%{customdata[0]}<extra></extra>",
    )

    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=40, b=100),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            itemsizing="constant",
        ),
    )

    return fig


def create_publication_cards(publications):
    from components.author_link_component import create_article_author_links

    cards = []

    for pub in publications:
        article_id = pub.get("id", "")
        title = pub.get("title", "Untitled")
        year = pub.get("publication_year", "Unknown")
        pub_type = pub.get("publication_type", "Unknown")
        abstract = pub.get("abstract", "No abstract available.")
        keywords = pub.get("keywords", [])
        authors = pub.get("authors", [])

        if len(abstract) > 300:
            abstract = abstract[:297] + "..."

        keyword_badges = []
        if keywords:
            if isinstance(keywords, list):
                for kw in keywords[:5]:
                    keyword_badges.append(
                        dbc.Badge(
                            kw, color="light", text_color="dark", className="me-1 mb-1"
                        )
                    )
                if len(keywords) > 5:
                    keyword_badges.append(
                        dbc.Badge(
                            f"+{len(keywords) - 5} more",
                            color="secondary",
                            className="me-1 mb-1",
                        )
                    )
            else:
                keyword_badges.append(
                    dbc.Badge(
                        keywords,
                        color="light",
                        text_color="dark",
                        className="me-1 mb-1",
                    )
                )

        cards.append(
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(title, className="card-title"),
                            html.Div(
                                [
                                    dbc.Badge(
                                        f"Year: {year}",
                                        color="primary",
                                        className="me-2",
                                    ),
                                    dbc.Badge(
                                        f"Type: {pub_type}",
                                        color="secondary",
                                        className="me-2",
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.P(abstract, className="mb-3"),
                            (
                                html.P(
                                    [
                                        html.Strong("Authors: "),
                                        create_article_author_links(authors),
                                    ],
                                    className="mb-2",
                                )
                                if authors
                                else None
                            ),
                            (
                                html.P(
                                    [
                                        html.Strong("Keywords: "),
                                        html.Span(keyword_badges),
                                    ]
                                )
                                if keywords
                                else None
                            ),
                            html.Div(
                                dbc.Button(
                                    "View Details",
                                    id={"type": "article-card", "id": article_id},
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                    className="mt-2",
                                    n_clicks=0,
                                ),
                                className="text-end",
                            ),
                        ]
                    )
                ],
                className="mb-3 shadow-sm",
            )
        )

    return cards


def create_coauthors_content(coauthors):
    if not coauthors:
        return dbc.Alert(
            "No co-authors found for this author.",
            color="info",
            className="text-center",
        )

    coauthor_cards = []
    for i, coauthor in enumerate(coauthors):
        if not coauthor.get("id"):
            continue

        coauthor_id = coauthor.get("id", "")
        full_name = coauthor.get("full_name", "Unknown")
        unit = coauthor.get("unit", "Not specified")
        subunit = coauthor.get("subunit", "Not specified")

        coauthor_cards.append(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.H5(full_name, className="card-title"),
                                html.Div(
                                    [
                                        html.Strong("Unit: "),
                                        html.Span(unit),
                                    ],
                                    className="mb-2",
                                ),
                                html.Div(
                                    [
                                        html.Strong("Subunit: "),
                                        html.Span(
                                            subunit if subunit else "Not specified"
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                dbc.Button(
                                    "View Profile",
                                    id={
                                        "type": "coauthor-select-button",
                                        "id": coauthor_id,
                                    },
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                    className="mt-2",
                                    n_clicks=0,
                                ),
                            ]
                        )
                    ],
                    className="h-100 shadow-sm",
                ),
                width=12,
                md=6,
                lg=4,
                className="mb-3",
            )
        )

    return dbc.Row(coauthor_cards)


def create_analytics_content(publications):

    if not publications:
        return dbc.Alert(
            "No publications available for analytics.",
            color="info",
            className="text-center",
        )

    years = {}
    types = {}
    all_keywords = {}

    for pub in publications:
        year = pub.get("publication_year")
        if year:
            years[year] = years.get(year, 0) + 1

        pub_type = pub.get("publication_type", "Unknown")
        types[pub_type] = types.get(pub_type, 0) + 1

        keywords = pub.get("keywords", [])
        if keywords:
            if isinstance(keywords, list):
                for kw in keywords:
                    all_keywords[kw] = all_keywords.get(kw, 0) + 1
            else:
                all_keywords[keywords] = all_keywords.get(keywords, 0) + 1

    summary_card = dbc.Card(
        [
            dbc.CardHeader(
                [html.I(className="bi bi-info-circle me-2"), "Publication Summary"]
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Strong("Total Publications: "),
                                            html.Span(str(len(publications))),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.Div(
                                        [
                                            html.Strong("Publication Years: "),
                                            html.Span(
                                                f"{min(years.keys()) if years else '–'} - {max(years.keys()) if years else '–'}"
                                            ),
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
                                            html.Strong("Most Common Type: "),
                                            html.Span(
                                                max(types.items(), key=lambda x: x[1])[
                                                    0
                                                ]
                                                if types
                                                else "Unknown"
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.Div(
                                        [
                                            html.Strong("Top Keyword: "),
                                            html.Span(
                                                max(
                                                    all_keywords.items(),
                                                    key=lambda x: x[1],
                                                )[0]
                                                if all_keywords
                                                else "None"
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                ],
                                width=12,
                                md=6,
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4 shadow-sm",
    )

    charts = []

    if years:
        years_items = sorted(years.items())
        fig_years = px.bar(
            x=[y[0] for y in years_items],
            y=[y[1] for y in years_items],
            labels={"x": "Year", "y": "Number of Publications"},
            title="Publications by Year",
            template="plotly_white",
            color=[y[1] for y in years_items],  
            color_continuous_scale="Viridis",  
        )
        fig_years.update_layout(
            xaxis_title="Year", 
            yaxis_title="Number of Publications",
            coloraxis_showscale=False, 
        )
        charts.append(
            dbc.Col(dcc.Graph(figure=fig_years), width=12, lg=6, className="mb-4")
        )

    if types:
        types_data = [{"type": t, "count": c} for t, c in types.items()]

        fig_types = create_improved_publication_types_chart(types_data)

        if fig_types:
            charts.append(
                dbc.Col(dcc.Graph(figure=fig_types), width=12, lg=6, className="mb-4")
            )

    if all_keywords:
        top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:15]
        

        keywords_df = pd.DataFrame({
            "keyword": [k[0] for k in top_keywords],
            "count": [k[1] for k in top_keywords]
        })
        
        fig_keywords = px.bar(
            keywords_df,
            x="count",
            y="keyword",
            orientation="h",
            labels={"count": "Count", "keyword": "Keyword"},
            title="Top Keywords",
            template="plotly_white",
            color="count", 
            color_continuous_scale="Viridis", 
        )
        fig_keywords.update_layout(
            xaxis_title="Count",
            yaxis_title="",
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,  
        )
        charts.append(
            dbc.Col(
                dcc.Graph(figure=fig_keywords), width=12, lg=6, className="mb-4"
            )
        )



    if not charts:
        return dbc.Alert(
            "No analytics data available for this unit.",
            color="warning",
            className="text-center",
        )

    return html.Div([summary_card, dbc.Row(charts)])


def register_author_callbacks(app):
    @app.callback(
        Output("loading-modal", "is_open", allow_duplicate=True),
        Input("current-author-store", "data"),
        prevent_initial_call=True,
    )
    def close_loading_modal_after_author_loaded(author_data):
        return False

    @app.callback(
        Output("tabs", "active_tab", allow_duplicate=True),
        Output("author-id-input", "value"),
        Output("author-id-search-button", "n_clicks"),
        Output("modal-close-trigger", "data"),
        Input({"type": "author-link", "id": ALL}, "n_clicks"),
        Input({"type": "author-link-modal", "id": ALL}, "n_clicks"),
        State({"type": "author-link", "id": ALL}, "id"),
        State({"type": "author-link-modal", "id": ALL}, "id"),
        prevent_initial_call=True,
    )
    def handle_author_link_click(clicks1, clicks2, ids1, ids2):
        ctx = dash.callback_context

        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if "author-link" in trigger_id and "modal" not in trigger_id:
            if not any(click for click in clicks1 if click):
                raise PreventUpdate

            click_idx = next((i for i, c in enumerate(clicks1) if c), None)
            if click_idx is None:
                raise PreventUpdate

            author_id = ids1[click_idx]["id"]

            return "tab-authors", author_id, 1, "close_modal"

        elif "author-link-modal" in trigger_id:
            if not any(click for click in clicks2 if click):
                raise PreventUpdate

            click_idx = next((i for i, c in enumerate(clicks2) if c), None)
            if click_idx is None:
                raise PreventUpdate

            author_id = ids2[click_idx]["id"]

            return "tab-authors", author_id, 1, "close_modal"

        raise PreventUpdate

    @app.callback(
        [
            Output("current-author-store", "data", allow_duplicate=True),
            Output("author-id-input", "value", allow_duplicate=True),
            Output("author-name-search-results", "children"),
        ],
        Input("author-name-search-button", "n_clicks"),
        State("author-name-input", "value"),
        prevent_initial_call=True,
    )
    def search_authors_by_name(n_clicks, name):
        if not n_clicks or not name:
            raise PreventUpdate

        try:
            print(f"Searching for authors matching: {name}")
            response = requests.post(
                f"{API_URL}/api/search_authors",
                json={"query": name, "size": 20},
                timeout=10,
            )
            data = response.json()

            if response.status_code != 200:
                return (
                    no_update,
                    no_update,
                    dbc.Alert(
                        f"Error: {data.get('detail', 'Unknown error')}",
                        color="danger",
                    ),
                )

            authors = data.get("authors", [])

            if not authors:
                return (
                    no_update,
                    no_update,
                    dbc.Alert(
                        f"No authors found matching '{name}'",
                        color="warning",
                    ),
                )

            author_list = []
            for author in authors:
                author_id = author.get("id")
                full_name = author.get("full_name", "Unknown")
                unit = author.get("unit", "Unknown")
                pub_count = len(author.get("publications", [])) or author.get(
                    "art_num", 0
                )

                author_list.append(
                    dbc.ListGroupItem(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H5(full_name, className="mb-1"),
                                            html.P(
                                                f"Unit: {unit}",
                                                className="text-muted mb-1",
                                            ),
                                            html.P(
                                                f"Publications: {pub_count}",
                                                className="small mb-0",
                                            ),
                                        ],
                                        width=9,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "View Profile",
                                                id={
                                                    "type": "author-select-button",
                                                    "id": author_id,
                                                },
                                                color="primary",
                                                outline=True,
                                                size="sm",
                                                className="float-end",
                                                n_clicks=0,
                                            ),
                                        ],
                                        width=3,
                                        className="d-flex align-items-center justify-content-end",
                                    ),
                                ]
                            ),
                        ],
                        className="shadow-sm mb-2",
                    )
                )

            author_results = dbc.ListGroup(author_list)

            first_author = authors[0]
            first_author_id = first_author.get("id")

            if first_author_id:
                author_data = load_author_data(first_author_id)
                return author_data, first_author_id, author_results

            return no_update, no_update, author_results

        except Exception as e:
            print(f"Error searching for authors: {str(e)}")
            print(traceback.format_exc())
            return (
                no_update,
                no_update,
                dbc.Alert(
                    f"Error searching for authors: {str(e)}",
                    color="danger",
                ),
            )

    @app.callback(
        Output("current-author-store", "data", allow_duplicate=True),
        Input("author-id-search-button", "n_clicks"),
        State("author-id-input", "value"),
        prevent_initial_call=True,
    )
    def search_author_by_id(n_clicks, author_id):
        if not n_clicks or not author_id:
            raise PreventUpdate

        print(f"Loading data for author ID: {author_id}")
        return load_author_data(author_id)

    @app.callback(
        Output("current-author-store", "data", allow_duplicate=True),
        Output("author-id-input", "value", allow_duplicate=True),
        Input({"type": "author-select-button", "id": ALL}, "n_clicks"),
        State({"type": "author-select-button", "id": ALL}, "id"),
        prevent_initial_call=True,
    )
    def handle_author_selection(n_clicks_list, button_ids):
        if not any(click for click in n_clicks_list if click):
            raise PreventUpdate

        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        button_data = eval(button_id)
        author_id = button_data.get("id")

        if not author_id:
            raise PreventUpdate

        print(f"Loading data for selected author ID: {author_id}")
        author_data = load_author_data(author_id)
        return author_data, author_id

    @app.callback(
        Output("author-info-container", "children"),
        Input("current-author-store", "data"),
        prevent_initial_call=True,
    )
    def update_author_info(author_data):
        if not author_data:
            raise PreventUpdate

        if "error" in author_data:
            return dbc.Alert(
                author_data["error"],
                color="danger",
            )

        if "publications" not in author_data or "publications" not in author_data.get(
            "publications", {}
        ):
            return dbc.Alert(
                "No publication data available for this author",
                color="warning",
            )

        author = author_data.get("author", {})
        publications = author_data.get("publications", {}).get("publications", [])
        coauthors = author_data.get("coauthors", {}).get("coauthors", [])

        profile_tab = dbc.Card(
            [
                dbc.CardHeader(
                    [html.I(className="bi bi-person-circle me-2"), "Author Profile"]
                ),
                dbc.CardBody(
                    [
                        html.H4(author.get("full_name", "Unknown"), className="mb-3"),
                        html.Div(
                            [
                                html.Strong("Unit: "),
                                html.Span(author.get("unit", "Not specified")),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("Subunit: "),
                                html.Span(author.get("subunit", "Not specified")),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("Total Publications: "),
                                html.Span(str(len(publications))),
                            ],
                            className="mb-2",
                        ),
                    ]
                ),
            ],
            className="mb-4 shadow-sm",
        )

        total_pubs = len(publications)
        page_size = 10
        total_pages = (total_pubs + page_size - 1) // page_size

        publications_tab = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.I(className="bi bi-journal-richtext me-2"),
                        f"Publications ({total_pubs})",
                    ]
                ),
                dbc.CardBody(
                    [
                        dcc.Markdown(
                            """
                    <style>
                    .pagination-wrap {
                        flex-wrap: wrap !important;
                        justify-content: center !important;
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
                        ),
                        html.Div(
                            id="author-publications-pagination-info",
                            children=f"Showing publications 1-{min(page_size, total_pubs)} of {total_pubs}",
                            className="text-muted mb-3",
                        ),
                        html.Div(
                            id="author-publications-list",
                            children=create_publication_cards(publications[:page_size]),
                        ),
                        (
                            dbc.Pagination(
                                id="author-publications-pagination-control",
                                max_value=total_pages,
                                first_last=True,
                                previous_next=True,
                                active_page=1,
                                fully_expanded=False, 
                                className="mt-3 justify-content-center pagination-wrap",
                                style={
                                    "maxWidth": "100%",
                                    "overflowX": "auto",
                                    "display": "flex",
                                    "flexWrap": "wrap",
                                },
                            )
                            if total_pages > 1
                            else html.Div()
                        ),
                    ]
                ),
            ],
            className="mb-4 shadow-sm",
        )


        coauthors_tab = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.I(className="bi bi-people me-2"),
                        f"Co-authors ({len(coauthors)})",
                    ]
                ),
                dbc.CardBody(create_coauthors_content(coauthors)),
            ],
            className="mb-4 shadow-sm",
        )

        analytics_tab = dbc.Card(
            [
                dbc.CardHeader(
                    [html.I(className="bi bi-graph-up me-2"), "Publication Analytics"]
                ),
                dbc.CardBody(create_analytics_content(publications)),
            ],
            className="mb-4 shadow-sm",
        )

        tabs = dbc.Tabs(
            [
                dbc.Tab(
                    profile_tab,
                    label="Profile",
                    tab_id="tab-profile",
                    active_label_class_name="fw-bold text-primary",
                ),
                dbc.Tab(
                    publications_tab,
                    label="Publications",
                    tab_id="tab-publications",
                    active_label_class_name="fw-bold text-primary",
                ),
                dbc.Tab(
                    coauthors_tab,
                    label="Co-authors",
                    tab_id="tab-coauthors",
                    active_label_class_name="fw-bold text-primary",
                ),
                dbc.Tab(
                    analytics_tab,
                    label="Analytics",
                    tab_id="tab-analytics",
                    active_label_class_name="fw-bold text-primary",
                ),
            ],
            className="mb-4",
            active_tab="tab-profile",
        )

        app.clientside_callback(
            """
            function(data) {
                if (!data || !data.publications || !data.publications.publications) {
                    return {"page": 1, "per_page": 10, "total_publications": 0};
                }
                return {"page": 1, "per_page": 10, "total_publications": data.publications.publications.length};
            }
            """,
            Output("author-publications-pagination", "data", allow_duplicate=True),
            Input("current-author-store", "data"),
            prevent_initial_call=True,
        )

        return tabs

    @app.callback(
        Output("current-author-store", "data", allow_duplicate=True),
        Output("author-id-input", "value", allow_duplicate=True),
        Input({"type": "coauthor-select-button", "id": ALL}, "n_clicks"),
        State({"type": "coauthor-select-button", "id": ALL}, "id"),
        prevent_initial_call=True,
    )
    def handle_coauthor_selection(n_clicks_list, button_ids):
        if not any(click for click in n_clicks_list if click):
            raise PreventUpdate

        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        button_data = eval(button_id)
        author_id = button_data.get("id")

        if not author_id:
            raise PreventUpdate

        print(f"Loading data for selected coauthor ID: {author_id}")
        author_data = load_author_data(author_id)
        return author_data, author_id

    @app.callback(
        Output("author-publications-list", "children"),
        Output("author-publications-pagination-info", "children"),
        Input("author-publications-pagination-control", "active_page"),
        State("current-author-store", "data"),
        State("author-publications-pagination", "data"),
        prevent_initial_call=True,
    )
    def paginate_author_publications(page, author_data, pagination_data):
        if not page or not author_data or not pagination_data:
            raise PreventUpdate

        if "publications" not in author_data or "publications" not in author_data.get(
            "publications", {}
        ):
            return html.Div("No publications data available"), "No publications"

        publications = author_data.get("publications", {}).get("publications", [])
        if not publications:
            raise PreventUpdate

        per_page = pagination_data.get("per_page", 10)
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, len(publications))

        current_publications = publications[start_idx:end_idx]

        publication_cards = create_publication_cards(current_publications)

        pagination_info = (
            f"Showing publications {start_idx + 1}-{end_idx} of {len(publications)}"
        )

        return publication_cards, pagination_info
