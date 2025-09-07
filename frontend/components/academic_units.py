import os
import traceback


import dash_bootstrap_components as dbc
from collections import Counter
import requests
from dash import dcc, html


API_URL = os.environ.get("API_URL", "http://localhost:8000")


try:
    from components.pagination_helper import (
        fetch_all_unit_publications,
        extract_collaborations_from_publications,
    )
    from components.author_resolution_helper import resolve_author_names
except ImportError:

    def fetch_all_unit_publications(unit_name: str, *, lite: bool = True):
        try:
            resp = requests.post(
                f"{API_URL}/api/unit_publications",
                json={
                    "unit": unit_name,
                    "size": 0,
                    "cluster_results": False,
                    "lite": lite,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as exc:
            return {"error": f"Błąd pobierania danych: {exc}"}

    def extract_collaborations_from_publications(unit_data):
        return []

    def resolve_author_names(author_ids, timeout=5, retry_count=2):
        return {aid: {"id": aid, "full_name": f"ID: {aid}"} for aid in author_ids}


def create_academic_units_panel():

    initial_tab_content = html.Div(
        dbc.Alert(
            [
                html.I(className="bi bi-info-circle me-2"),
                "Search for an academic unit to see information.",
            ],
            color="info",
            className="text-center p-5",
        )
    )

    return html.Div(
        [
            html.Div(
                style={"display": "none"},
                children=dcc.Markdown(
                    """
<style>
.pagination-container {flex-wrap: wrap; max-width: 100%; overflow-x: visible;}
.pagination-container .page-item {margin: 2px;}
</style>
""",
                    dangerously_allow_html=True,
                ),
            ),
            dbc.Row(
                dbc.Col(
                    [
                        html.H3("Academic Units Explorer", className="mb-3"),
                        html.P(
                            "Explore academic units  "
                            "and their research publications and collaborations.",
                            className="text-muted",
                        ),
                    ],
                    width=12,
                )
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(className="bi bi-building me-2"),
                                    "Search Academic Unit",
                                ]
                            ),
                            dbc.CardBody(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText(
                                                [
                                                    html.I(
                                                        className="bi bi-building me-2"
                                                    ),
                                                    "Unit Name",
                                                ]
                                            ),
                                            dbc.Input(
                                                id="unit-name-input",
                                                type="text",
                                                placeholder="Enter unit name (e.g. WH, WEAIiIB, ...)",
                                                value="",
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-search me-2"
                                                    ),
                                                    "Search",
                                                ],
                                                id="unit-search-button",
                                                color="primary",
                                                className="ms-2",
                                                n_clicks=0,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Popular Units", className="mb-2"),
                                            html.Div(
                                                [
                                                    dbc.Button(
                                                        lbl,
                                                        id={
                                                            "type": "popular-unit",
                                                            "name": lbl,
                                                        },
                                                        color="light",
                                                        className="me-2 mb-2",
                                                        n_clicks=0,
                                                    )
                                                    for lbl in [
                                                        "WH",
                                                        "WEAIiIB",
                                                        "WIEiT",
                                                        "WIMiC",
                                                        "WIMiR",
                                                    ]
                                                ]
                                            ),
                                        ],
                                        className="mt-3",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4 shadow-sm",
                    ),
                    width=12,
                )
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(className="bi bi-graph-up me-2"),
                                    "Topic-based Unit Analysis",
                                ]
                            ),
                            dbc.CardBody(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText(
                                                [
                                                    html.I(className="bi bi-tag me-2"),
                                                    "Topic",
                                                ]
                                            ),
                                            dbc.Input(
                                                id="topic-input-unit",
                                                type="text",
                                                placeholder="Enter topic (e.g. machine learning, neural networks, ...)",
                                                value="",
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-search me-2"
                                                    ),
                                                    "Analyze",
                                                ],
                                                id="topic-analysis-button-unit",
                                                color="primary",
                                                className="ms-2",
                                                n_clicks=0,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    html.P(
                                        "Enter a research topic to see which academic units are most active in this area.",
                                        className="text-muted small",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4 shadow-sm",
                    ),
                    width=12,
                )
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                html.Div(
                                    initial_tab_content, id="unit-profile-container"
                                ),
                                label="Unit Profile",
                            ),
                            dbc.Tab(
                                html.Div(
                                    initial_tab_content,
                                    id="unit-publications-container",
                                ),
                                label="Publications",
                            ),
                            dbc.Tab(
                                html.Div(
                                    initial_tab_content, id="unit-analytics-container"
                                ),
                                label="Analytics",
                            ),
                            dbc.Tab(
                                html.Div(
                                    initial_tab_content,
                                    id="unit-collaborations-container",
                                ),
                                label="Collaborations",
                            ),
                        ],
                        id="unit-tabs",
                        active_tab="tab-unit-profile",
                        className="mb-4",
                    ),
                    width=12,
                )
            ),
            dbc.Row(dbc.Col(html.Div(id="topic-analysis-unit-results"), width=12)),
        ]
    )


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
        color_discrete_sequence=px.colors.sequential.Viridis_r,  
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


def create_collaborations_chart(collaborations, unit_name):

    import pandas as pd
    import plotly.express as px

    df_collab = pd.DataFrame(collaborations)

    if len(df_collab) > 15:
        df_collab = df_collab.head(15)

    fig = px.bar(
        df_collab,
        x="joint_publications",
        y="unit",
        orientation="h",
        title=f"Top Collaborating Units with {unit_name}",
        labels={
            "joint_publications": "Joint Publications",
            "unit": "Collaborating Unit",
        },
        template="plotly_white",
        color="joint_publications",
        color_continuous_scale=px.colors.sequential.Viridis,
    )

    fig.update_layout(
        xaxis_title="Number of Joint Publications",
        yaxis_title="",
        coloraxis_showscale=False,
        height=600,
        yaxis={"categoryorder": "total ascending"},
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                [html.I(className="bi bi-people me-2"), "Unit Collaborations"]
            ),
            dbc.CardBody(
                [
                    html.P(
                        f"Showing collaboration data for {unit_name} with other units."
                    ),
                    dcc.Graph(figure=fig),
                ]
            ),
        ],
        className="shadow-sm",
    )


def register_unit_callbacks(app):

    import dash
    from dash import callback, Input, Output, State, ALL
    from dash.exceptions import PreventUpdate

    @app.callback(
        Output("unit-name-input", "value", allow_duplicate=True),
        Output("unit-search-button", "n_clicks", allow_duplicate=True),
        Input({"type": "popular-unit", "name": dash.ALL}, "n_clicks"),
        State({"type": "popular-unit", "name": dash.ALL}, "id"),
        prevent_initial_call=True,
    )
    def select_popular_unit(clicks, ids):

        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            button_data = eval(button_id)
            unit_name = button_data.get("name", "")

            if not unit_name:
                raise PreventUpdate

            return unit_name, 1

        except Exception as e:
            print(f"Error in select_popular_unit: {e}")
            raise PreventUpdate

    @app.callback(
        Output("current-unit-store", "data"),
        Output("unit-profile-container", "children"),
        Output("notification-toast", "children", allow_duplicate=True),
        Output("notification-toast", "header", allow_duplicate=True),
        Output("notification-toast", "is_open", allow_duplicate=True),
        Output("loading-modal", "is_open", allow_duplicate=True),
        Input("unit-search-button", "n_clicks"),
        State("unit-name-input", "value"),
        prevent_initial_call=True,
    )
    def search_unit(n_clicks, unit_name):

        if not n_clicks or not unit_name:
            raise PreventUpdate

        print(f"Searching for unit: {unit_name}, clicks: {n_clicks}")

        try:

            notification = html.Div(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    f"Loading data for unit {unit_name}... This may take a while if there are many publications.",
                ]
            )

            unit_data = fetch_all_unit_publications(unit_name)

            if "error" in unit_data:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-exclamation-triangle me-2"),
                        unit_data["error"],
                    ],
                    color="warning",
                )

                error_alert = html.Div(
                    [
                        error_alert,
                        dbc.Alert(
                            [
                                html.I(className="bi bi-lightbulb me-2"),
                                "Try using the topic analysis option below to find information about this unit.",
                            ],
                            color="info",
                        ),
                    ]
                )

                return dash.no_update, error_alert, notification, "Error", True, False

            profile_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [html.I(className="bi bi-building me-2"), f"Unit: {unit_name}"]
                    ),
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    html.Strong("Authors in index: "),
                                    html.Span(str(unit_data.get("author_count", 0))),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Strong("Publications found: "),
                                    html.Span(
                                        str(unit_data.get("publication_count", 0))
                                    ),
                                ],
                                className="mb-2",
                            ),
                            (
                                html.Div(
                                    [
                                        dbc.Alert(
                                            [
                                                html.I(
                                                    className="bi bi-info-circle me-2"
                                                ),
                                                "Note: Data loading was completed partially due to timeout. "
                                                + "Some publications might not be included.",
                                            ],
                                            color="info",
                                            className="mt-3",
                                        )
                                    ]
                                )
                                if unit_data.get("partial_loading", False)
                                else None
                            ),
                        ]
                    ),
                ],
                className="shadow-sm",
            )

            success_notification = html.Div(
                [
                    html.I(className="bi bi-check-circle me-2"),
                    f"Successfully loaded {unit_data.get('publication_count', 0)} publications for unit {unit_name}",
                ]
            )

            return (
                unit_data,
                profile_card,
                success_notification,
                "Unit Loaded",
                True,
                False,
            )

        except Exception as e:
            import traceback

            print(f"Exception in search_unit: {str(e)}")
            print(traceback.format_exc())
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    f"Error: {str(e)}",
                ],
                color="danger",
            )
            return dash.no_update, error_alert, notification, "Error", True, False

    @app.callback(
        Output("unit-publications-container", "children"),
        Input("current-unit-store", "data"),
        prevent_initial_call=True,
    )
    def update_unit_publications(unit_data):
        from components.author_link_component import create_article_author_links

        if not unit_data:
            raise PreventUpdate

        publications = unit_data.get("publications", [])

        if not publications:
            return dbc.Alert(
                "No publications found for this unit.",
                color="warning",
                className="text-center",
            )

        page_size = 15
        total_pubs = len(publications)
        total_pages = (total_pubs + page_size - 1) // page_size

    
        pagination_controls = dbc.Pagination(
            id="unit-card-pagination",
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

        first_page_publications = publications[:page_size]

        card_view_components = [
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
            html.P(
                id="unit-card-pagination-info",
                children=f"Showing publications 1-{min(page_size, total_pubs)} of {total_pubs}",
                className="text-muted mb-3",
            ),
            html.Div(
                id="unit-publications-cards-container",
                children=create_publication_cards(first_page_publications),
            ),
            pagination_controls if total_pages > 1 else html.Div(),
        ]


        from dash import dash_table
        import pandas as pd

        datatable_data = []
        for pub in publications:
            datatable_entry = {
                "ID": pub.get("id", ""),
                "Title": pub.get("title", "No title")[:100],
                "Year": pub.get("publication_year", ""),
                "Type": pub.get("publication_type", "Unknown"),
            }
            datatable_data.append(datatable_entry)

        df = pd.DataFrame(datatable_data)

        table = dash_table.DataTable(
            id="unit-publications-table",
            columns=[
                {"name": "Title", "id": "Title"},
                {"name": "Year", "id": "Year"},
                {"name": "Type", "id": "Type"},
            ],
            data=df.to_dict("records"),
            filter_action="native",
            sort_action="native",
            page_size=15,
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "8px",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"}
            ],
            row_selectable="single",
            selected_rows=[],
        )

        tabs = dbc.Tabs(
            [
                dbc.Tab(
                    html.Div(card_view_components),
                    label="Card View",
                    tab_id="tab-card-view",
                ),
                dbc.Tab(
                    [
                        html.Div(
                            [
                                html.P(
                                    f"Table shows all {len(publications)} publications. Use filters to find specific articles.",
                                    className="text-muted mb-3",
                                ),
                                html.Div(
                                    [
                                        html.P(
                                            "Click on a row to view article details:",
                                            className="mb-2",
                                        ),
                                        html.Div(id="selected-article-from-table"),
                                    ]
                                ),
                                html.Hr(),
                                table,
                            ]
                        )
                    ],
                    label="Table View",
                    tab_id="tab-table-view",
                ),
            ],
            className="mt-3",
        )

        return dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.I(className="bi bi-journal-text me-2"),
                        f"Publications ({len(publications)})",
                    ]
                ),
                dbc.CardBody(
                    [
                        html.P(
                            f"Found {len(publications)} publications for this unit."
                        ),
                        tabs,
                    ]
                ),
            ],
            className="shadow-sm",
        )

    @app.callback(
        Output("unit-publications-cards-container", "children"),
        Output("unit-card-pagination-info", "children"),
        Input("unit-card-pagination", "active_page"),
        State("current-unit-store", "data"),
        prevent_initial_call=True,
    )
    def paginate_unit_publications_cards(page, unit_data):

        if not page or not unit_data:
            raise PreventUpdate

        publications = unit_data.get("publications", [])

        if not publications:
            return html.Div("No publications data available"), "No publications"

        page_size = 15
        total_pubs = len(publications)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_pubs)

        current_publications = publications[start_idx:end_idx]

        pagination_info = (
            f"Showing publications {start_idx + 1}-{end_idx} of {total_pubs}"
        )

        cards = create_publication_cards(current_publications)

        return cards, pagination_info

    @app.callback(
        Output("selected-article-from-table", "children"),
        Input("unit-publications-table", "selected_rows"),
        State("unit-publications-table", "data"),
        prevent_initial_call=True,
    )
    def display_selected_article(selected_rows, data):

        if not selected_rows or not data:
            return html.P(
                "Select an article from the table to view details",
                className="text-muted",
            )

        idx = selected_rows[0]
        article_data = data[idx]
        article_id = article_data.get("ID", "")

        if not article_id:
            return html.P("Article ID not found", className="text-danger")

        return dbc.Button(
            "View Full Article Details",
            id={"type": "article-card", "id": article_id},
            color="primary",
            className="mt-2",
            n_clicks=0,
        )

    @app.callback(
        Output("unit-analytics-container", "children"),
        Input("current-unit-store", "data"),
        prevent_initial_call=True,
    )

    def update_unit_analytics(unit_data):

        from dash import dcc
        import plotly.express as px
        import pandas as pd

        if not unit_data:
            raise PreventUpdate

        publications = unit_data.get("publications", [])
        analytics = unit_data.get("analytics", {})

        if not publications:
            return dbc.Alert(
                "No publications available for analytics.",
                color="warning",
                className="text-center",
            )


        if "keywords" not in analytics or not analytics["keywords"]:
            keywords_counter = Counter()
            for pub in publications:
                keywords = pub.get("keywords", [])
                if keywords:
                    if isinstance(keywords, list):
                        keywords_counter.update(keywords)
                    else:
                        keywords_counter[keywords] = keywords_counter.get(keywords, 0) + 1

            if keywords_counter:
                analytics["keywords"] = [
                    {"value": k, "count": c} 
                    for k, c in keywords_counter.most_common(40)
                ]

                unit_data["analytics"]["keywords"] = analytics["keywords"]

        visualizations = []

        if "timeline" in analytics and analytics["timeline"]:
            timeline_data = analytics["timeline"]
            

            df_timeline = pd.DataFrame(timeline_data)
            
            fig_timeline = px.bar(
                df_timeline,
                x="year",
                y="count",
                title="Publications by Year",
                labels={"year": "Year", "count": "Count"},
                template="plotly_white",
                color="count",  
                color_continuous_scale="Viridis",  
            )
            fig_timeline.update_layout(
                xaxis_title="Year", 
                yaxis_title="Number of Publications",
                coloraxis_showscale=False, 
            )
            visualizations.append(
                dbc.Col(
                    dcc.Graph(figure=fig_timeline), width=12, lg=6, className="mb-4"
                )
            )

        if "types" in analytics and analytics["types"]:
            types_data = analytics["types"]
            fig_types = create_improved_publication_types_chart(types_data)
            if fig_types:
                visualizations.append(
                    dbc.Col(
                        dcc.Graph(figure=fig_types), width=12, lg=6, className="mb-4"
                    )
                )

        if "keywords" in analytics and analytics["keywords"]:
            keywords_data = analytics["keywords"][:15]
            

            if keywords_data and len(keywords_data) > 0:

                df_keywords = pd.DataFrame(keywords_data)
                

                x_col = "count" if "count" in df_keywords.columns else next((c for c in df_keywords.columns if c != "value"), "count")
                y_col = "value" if "value" in df_keywords.columns else next((c for c in df_keywords.columns if c != "count"), "value")
                
                fig_keywords = px.bar(
                    df_keywords,
                    x=x_col,
                    y=y_col,
                    orientation="h",
                    title="Top Keywords",
                    labels={x_col: "Count", y_col: "Keyword"},
                    template="plotly_white",
                    color=x_col,  
                    color_continuous_scale="Viridis",  
                )
                fig_keywords.update_layout(
                    xaxis_title="Count",
                    yaxis_title="",
                    yaxis={"categoryorder": "total ascending"},
                    coloraxis_showscale=False,  
                )
                visualizations.append(
                    dbc.Col(
                        dcc.Graph(figure=fig_keywords), width=12, lg=6, className="mb-4"
                    )
                )


        if not visualizations:
            return dbc.Alert(
                "No analytics data available for this unit.",
                color="warning",
                className="text-center",
            )

        return dbc.Card(
            [
                dbc.CardHeader(
                    [html.I(className="bi bi-graph-up me-2"), "Unit Analytics"]
                ),
                dbc.CardBody([dbc.Row(visualizations)]),
            ],
            className="shadow-sm",
        )

    @app.callback(
    Output("topic-analysis-unit-results", "children"),
    Output("loading-modal", "is_open", allow_duplicate=True),
    Input("topic-analysis-button-unit", "n_clicks"),
    State("topic-input-unit", "value"),
    prevent_initial_call=True,
    )
    def analyze_topic(n_clicks, topic):

        import pandas as pd
        import plotly.express as px
        from dash import dcc

        if not n_clicks or not topic:
            raise PreventUpdate

        try:
            
            print(f"Analyzing topic: {topic}")
            response = requests.post(
                f"{API_URL}/api/topic_analysis",
                json={
                    "query": topic, 
                    "top_n": 15
                },
                timeout=180,
            )

            if response.status_code != 200:
                error_message = f"Error analyzing topic: HTTP {response.status_code}"
                try:
                    error_message += (
                        f" - {response.json().get('detail', response.text)}"
                    )
                except:
                    error_message += f" - {response.text}"
                return dbc.Alert(error_message, color="danger"), False

            analysis_data = response.json()

            affiliations = analysis_data.get("affiliation_analysis", {}).get(
                "affiliations", []
            )

            if not affiliations:
                return (
                    dbc.Alert(
                        "No data found for this topic analysis.",
                        color="warning",
                        className="text-center",
                    ),
                    False,
                )

            df_aff = pd.DataFrame(affiliations)

            fig = px.bar(
                df_aff,
                x="count",
                y="name",
                orientation="h",
                title=f"Units Most Active in '{topic}'",
                labels={"count": "Publications", "name": "Academic Unit"},
                template="plotly_white",
                color="percentage",
                color_continuous_scale=px.colors.sequential.Viridis,
                text="percentage",
            )

            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")

            fig.update_layout(
                xaxis_title="Number of Publications",
                yaxis_title="",
                height=500,
                yaxis={"categoryorder": "total ascending"},
            )

            unit_buttons = []
            for aff in affiliations[:5]:
                unit_name = aff.get("name", "")
                if unit_name:
                    unit_buttons.append(
                        dbc.Button(
                            unit_name,
                            id={"type": "topic-unit-button", "name": unit_name},
                            color="outline-primary",
                            size="sm",
                            className="me-2 mb-2",
                            n_clicks=0,
                        )
                    )

            result = dbc.Card(
                [
                    dbc.CardHeader(
                        [html.I(className="bi bi-tag me-2"), f"Topic Analysis: {topic}"]
                    ),
                    dbc.CardBody(
                        [
                            html.P(
                                f"Showing academic units most active in the topic '{topic}' based on {analysis_data.get('affiliation_analysis', {}).get('total_articles', 0)} publications."
                            ),
                            dcc.Graph(figure=fig),
                            html.Div(
                                [
                                    html.P(
                                        [
                                            html.Strong("Total publications: "),
                                            html.Span(
                                                str(
                                                    analysis_data.get(
                                                        "affiliation_analysis", {}
                                                    ).get("total_articles", 0)
                                                )
                                            ),
                                        ],
                                        className="mb-2 mt-3",
                                    ),
                                    html.Small(
                                        "Percentage values show what portion of the topic's publications come from each unit.",
                                        className="text-muted mb-3 d-block",
                                    ),
                                    (
                                        html.Div(
                                            [
                                                html.P(
                                                    "Explore top units:",
                                                    className="mb-2",
                                                ),
                                                html.Div(unit_buttons),
                                            ]
                                        )
                                        if unit_buttons
                                        else None
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="shadow-sm mt-4",
            )

            return result, False

        except Exception as e:
            print(f"Exception in analyze_topic: {str(e)}")
            print(traceback.format_exc())
            return (
                dbc.Alert(f"Error processing topic analysis: {str(e)}", color="danger"),
                False,
            )

    @app.callback(
        Output("unit-name-input", "value", allow_duplicate=True),
        Output("unit-search-button", "n_clicks", allow_duplicate=True),
        Input({"type": "topic-unit-button", "name": dash.ALL}, "n_clicks"),
        State({"type": "topic-unit-button", "name": dash.ALL}, "id"),
        prevent_initial_call=True,
    )
    def select_topic_unit(clicks, ids):

        if not any(c for c in clicks if c):
            raise PreventUpdate

        idx = next(i for i, c in enumerate(clicks) if c)
        unit_name = ids[idx]["name"]
        return unit_name, 1
    
    @app.callback(
        Output("unit-collaborations-container", "children"),
        Input("current-unit-store", "data"),
        prevent_initial_call=True,
    )
    def update_unit_collaborations(unit_data):
        if not unit_data:
            return dbc.Alert("No unit data available.",
                            color="warning", className="text-center")

        collabs = unit_data.get("collaborations", [])
        

        if not collabs and "publications" in unit_data and unit_data.get("publications"):
            from collections import Counter
            
            unit_name = unit_data.get("unit", "")
            publications = unit_data.get("publications", [])
            
            counter = Counter()
            for pub in publications:
                if "author_units" in pub:
                    for other in pub.get("author_units", []):
                        if other != unit_name:
                            counter[other] += 1
            
            collabs = [
                {"unit": other, "joint_publications": cnt}
                for other, cnt in counter.most_common(15)
            ]
        
        if not collabs:
            return dbc.Alert("No collaboration data for this unit.",
                            color="warning", className="text-center")

        return create_collaborations_chart(collabs, unit_data.get("unit", ""))