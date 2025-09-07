import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.express as px
from components.author_link_component import create_article_author_links

def create_results_panel(hits=None, facets=None, current_page=1, total_hits=None):
    if not hits:
        return html.Div(
            [
                html.H4("Search Results"),
                html.P("Enter a query to see results.")
            ]
        )

    if total_hits is None:
        total_hits = len(hits)

    facets_charts = []
    
    year_chart = None
    if facets and "publication_years" in facets:
        years = sorted(facets["publication_years"], key=lambda x: x["year"])
        if years:
            fig = px.bar(
                years,
                x="year",
                y="count",
                title="Publications by Year",
                labels={"year": "Year", "count": "Count"},
                color="count",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=40, b=20),
                height=250,
                xaxis=dict(tickangle=45),
            )
            year_chart = dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-calendar me-2"),
                    "Timeline"
                ]),
                dbc.CardBody(
                    dcc.Graph(
                        figure=fig, 
                        config={"displayModeBar": False}
                    ),
                    className="p-2"
                )
            ])
            facets_charts.append(dbc.Col(year_chart, width=12, lg=6, className="mb-3"))

    keywords_chart = None
    if facets and "keywords" in facets:
        kws = sorted(facets["keywords"], key=lambda x: x["count"], reverse=True)[:10]
        if kws:
            fig = px.bar(
                kws,
                x="count",
                y="value",
                orientation="h",
                title="Top Keywords",
                labels={"count": "Count", "value": "Keyword"},
                color="count",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=40, b=20),
                height=250,
            )
            keywords_chart = dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-tags me-2"),
                    "Top Keywords"
                ]),
                dbc.CardBody(
                    dcc.Graph(
                        figure=fig, 
                        config={"displayModeBar": False}
                    ),
                    className="p-2"
                )
            ])
            facets_charts.append(dbc.Col(keywords_chart, width=12, lg=6, className="mb-3"))
    
    pub_types_chart = None
    if facets and "publication_types" in facets:
        types = sorted(facets["publication_types"], key=lambda x: x["count"], reverse=True)
        if types:
            fig = px.pie(
                types,
                values="count",
                names="value",
                title="Publication Types",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=40, b=20),
                height=250,
                legend=dict(orientation="h", y=-0.15)
            )
            pub_types_chart = dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-journals me-2"),
                    "Publication Types"
                ]),
                dbc.CardBody(
                    dcc.Graph(
                        figure=fig, 
                        config={"displayModeBar": False}
                    ),
                    className="p-2"
                )
            ])
            facets_charts.append(dbc.Col(pub_types_chart, width=12, lg=6, className="mb-3"))

    if facets_charts:
        facets_panel = dbc.Row(
            facets_charts,
            className="mt-3 mb-4",
            id="facets-panel"  
        )
    else:
        facets_panel = None

    results_list = []
    for hit in hits:
        article_id = hit.get("id", "")
        
        abstract = hit.get("abstract", "")
        if len(abstract) > 300:
            abstract = abstract[:300] + "..."

        card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H5(
                            hit.get("title", "No title"), 
                            className="card-title"
                        ),
                        html.Div(
                            [
                                dbc.Badge(
                                    f"Year: {hit.get('publication_year','Unknown')}",
                                    color="primary",
                                    className="me-2",
                                ),
                                dbc.Badge(
                                    f"Type: {hit.get('publication_type','Unknown')}",
                                    color="secondary",
                                    className="me-2",
                                ),
                                dbc.Badge(
                                    f"Score: {hit.get('_score', 0):.2f}",
                                    color="light",
                                    text_color="dark",
                                    className="me-2",
                                ),
                            ],
                            className="mb-2",
                        ),
                        html.P(
                            abstract or "No abstract", 
                            className="card-text"
                        ),

                        (
                            html.P(
                                [
                                    html.Strong("Authors: "),
                                    create_article_author_links(hit.get("authors", []))
                                ],
                                className="mb-2"
                            )
                            if hit.get("authors")
                            else None
                        ),
                        (
                            html.P(
                                [
                                    html.Strong("Keywords: "),
                                    html.Span(
                                        [item for kw_list in [
                                            [
                                                dbc.Badge(
                                                    keyword,
                                                    color="light",
                                                    text_color="dark",
                                                    className="me-1",
                                                )
                                            ] for keyword in hit.get("keywords", [])[:5]
                                        ] for item in kw_list] + 
                                        ([
                                            dbc.Badge(
                                                f"+{len(hit.get('keywords', [])) - 5} more",
                                                color="light",
                                                text_color="dark",
                                                className="me-1",
                                            )
                                        ] if len(hit.get("keywords", [])) > 5 else [])
                                    ),
                                ]
                            )
                            if hit.get("keywords")
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
                            ),
                            className="text-end",
                        ),
                    ]
                )
            ],
            className="mb-3 shadow-sm",
        )
        results_list.append(card)

    action_panel = dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Button(
                        [
                            html.I(className="bi bi-arrow-right me-2"),
                            "Go to Clustering Panel",
                        ],
                        id="go-to-clustering-button",
                        color="primary",
                    ),
                ],
                width=12,
                className="mb-4",
            )
        ],
        id="action-panel" 
    )


    total_pages = (total_hits + 9) // 10
    

    pages_to_show = []
    

    if total_pages > 5:

        pages_to_show.append(1) 
        

        start_range = max(2, current_page - 2)
        end_range = min(total_pages - 1, current_page + 2)
        

        if start_range > 2:
            pages_to_show.append('...')
        

        pages_to_show.extend(list(range(start_range, end_range + 1)))
        

        if end_range < total_pages - 1:
            pages_to_show.append('...')
        
        pages_to_show.append(total_pages)  
    else:

        pages_to_show = list(range(1, total_pages + 1))

    pagination = dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        [
                            html.Span(f"Page {current_page} of {total_pages}", className="me-3"),
                            dbc.Pagination(
                                id="results-pagination",
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
                ],
                width=12,
                className="mb-4",
            )
        ],
        id="pagination-panel"  
    )

    result_info = html.P(
        f"Showing results {(current_page-1)*10 + 1}-{min(current_page*10, total_hits)} of {total_hits}",
        className="text-muted mb-3 text-center",
        id="result-info"  
    )

    pagination_css = dcc.Markdown(
        """
        <style>
        .pagination-wrap {
            flex-wrap: wrap !important;
            justify-content: center !important;
        }
        .pagination-wrap .page-item {
            margin: 2px !important;
        }
        
        /* Make sure pagination items are all the same size */
        .pagination-wrap .page-link {
            min-width: 38px !important;
            text-align: center !important;
        }
        </style>
        """,
        dangerously_allow_html=True,
    )

    return html.Div(
        [
            pagination_css,
            html.H3(
                [
                    f"Found {total_hits} articles",
                ],
                className="mb-3",
            ),
            facets_panel if facets_panel and current_page == 1 else html.Div(),
            action_panel if current_page == 1 else html.Div(),
            result_info,
            html.Div(results_list, id="results-list"),  
            pagination if total_pages > 1 else html.Div(),
        ],
        id="complete-results-panel" 
    )