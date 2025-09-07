import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output


def create_search_panel():

    publication_types = [
        "patent",
        "materiały konferencyjne (aut.)",
        "artykuł w czasopiśmie",
        "referat w czasopiśmie",
        "abstrakt w czasopiśmie",
        "fragment książki",
        "monografia pokonferencyjna",
        "redakcja czasopisma",
        "redakcja serii",
        "rozdział w podręczniku",
        "książka",
        "skrypt",
        "monografia",
        "zgłoszenie patentowe",
        "podręcznik",
        "patent zastosowany",
        "fragment monografii pokonferencyjnej",
        "raporty, sprawozdania, inne (fragment)",
        "materiały konferencyjne (red.)",
        "przegląd",
        "raporty, sprawozdania, inne (całość)",
        "recenzja",
        "nota edytorska",
        "wywiad, rozmowa",
        "zgłoszenie wzoru użytkowego",
        "komunikat",
        "wzór użytkowy",
        "wstęp",
        "atlas, mapy",
        "hasło w encyklopedii/słowniku",
        "wzór przemysłowy",
        "list",
        "mapa",
        "znak towarowy",
        "norma",
        "znak towarowy zastosowany",
        "przekład",
        "encyklopedia, słownik",
        "komitet redakcyjny czasopisma",
    ]

    publication_types.sort()

    publication_type_options = [{"label": "All Types", "value": "all"}] + [
        {"label": pt, "value": pt} for pt in publication_types
    ]

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3("Article Search", className="mb-3"),
                            html.P(
                                "Search scientific articles using text-based, semantic, or hybrid approaches.",
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
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="search-input",
                                        type="text",
                                        placeholder="Enter query (e.g. machine learning, kopalnia, neural networks)...",
                                        value="",
                                        size="lg",
                                        className="border-primary",
                                    ),
                                    dbc.InputGroupText(
                                        html.I(
                                            className="bi bi-question-circle text-primary",
                                            id="search-help-icon",
                                        ),
                                        className="bg-light border-primary",
                                    ),
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-search me-2"),
                                            "Search",
                                        ],
                                        id="search-button",
                                        color="primary",
                                        size="lg",
                                        className="ms-2",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Tooltip(
                                [
                                    html.P("Search tips:", className="fw-bold mb-2"),
                                    html.Ul(
                                        [
                                            html.Li(
                                                [
                                                    html.Strong("Phrase Search: "),
                                                    "Use quotes for exact matching in text-based search. Example: ",
                                                    html.Code('"neural networks"'),
                                                ]
                                            ),
                                            html.Li(
                                                [
                                                    html.Strong("Combined Search: "),
                                                    "Mix phrases and regular terms in text-based search. Example: ",
                                                    html.Code(
                                                        '"machine learning" application'
                                                    ),
                                                ]
                                            ),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                target="search-help-icon",
                                placement="bottom",
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
                            dbc.Button(
                                [
                                    html.I(className="bi bi-sliders me-2"),
                                    "Search Parameters",
                                    html.I(className="bi bi-chevron-down ms-2"),
                                ],
                                id="search-params-button",
                                color="secondary",
                                outline=True,
                                className="mb-3 w-100",
                            ),
                            dbc.Collapse(
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H5(
                                                "Search Parameters", className="mb-0"
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Search Method"
                                                                ),
                                                                dbc.Select(
                                                                    id="search-method-select",
                                                                    options=[
                                                                        {
                                                                            "label": "Text-based",
                                                                            "value": "text",
                                                                        },
                                                                        {
                                                                            "label": "Semantic",
                                                                            "value": "semantic",
                                                                        },
                                                                        {
                                                                            "label": "Hybrid",
                                                                            "value": "hybrid",
                                                                        },
                                                                    ],
                                                                    value="hybrid",
                                                                ),
                                                            ],
                                                            width=12,
                                                            md=4,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Number of Results"
                                                                ),
                                                                dcc.Slider(
                                                                    id="search-size-slider",
                                                                    min=5,
                                                                    max=1500,
                                                                    step=5,
                                                                    value=100,
                                                                    marks={
                                                                        5: "5",
                                                                        50: "50",
                                                                        150: "150",
                                                                        250: "250",
                                                                        500: "500",
                                                                        1000: "1000",
                                                                        1500: "1500",
                                                                    },
                                                                    tooltip={
                                                                        "placement": "bottom",
                                                                        "always_visible": True,
                                                                    },
                                                                    className="mt-2",
                                                                ),
                                                            ],
                                                            width=12,
                                                            md=4,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Publication Year Range"
                                                                ),
                                                                dcc.RangeSlider(
                                                                    id="year-range-slider",
                                                                    min=1974,
                                                                    max=2025,
                                                                    step=1,
                                                                    value=[2000, 2025],
                                                                    marks={
                                                                        1974: "1974",
                                                                        1980: "1980",
                                                                        1985: "1985",
                                                                        1990: "1990",
                                                                        1995: "1995",
                                                                        2000: "2000",
                                                                        2005: "2005",
                                                                        2010: "2010",
                                                                        2015: "2015",
                                                                        2020: "2020",
                                                                        2025: "2025",
                                                                    },
                                                                    tooltip={
                                                                        "placement": "bottom",
                                                                        "always_visible": True,
                                                                    },
                                                                    className="mt-2",
                                                                ),
                                                            ],
                                                            width=12,
                                                            md=4,
                                                        ),
                                                    ],
                                                    className="mb-3",
                                                ),
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Publication Types",
                                                                    className="mb-2",
                                                                ),
                                                                html.Div(
                                                                    [
                                                                        dbc.Checklist(
                                                                            id="publication-type-select",
                                                                            options=publication_type_options,
                                                                            value=[
                                                                                "all"
                                                                            ],
                                                                            inline=False,
                                                                            className="publication-type-checkbox",
                                                                        ),
                                                                    ],
                                                                    style={
                                                                        "maxHeight": "300px",
                                                                        "overflowY": "auto",
                                                                    },
                                                                    className="border p-3 rounded",
                                                                ),
                                                                html.Small(
                                                                    [
                                                                        html.I(
                                                                            className="bi bi-info-circle me-1"
                                                                        ),
                                                                        "Select multiple publication types. 'All Types' will override other selections.",
                                                                    ],
                                                                    className="text-muted mt-1 d-block",
                                                                ),
                                                            ],
                                                            width=12,
                                                            className="mt-3",
                                                        )
                                                    ]
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="mb-4 shadow-sm",
                                ),
                                id="search-params-collapse",
                                is_open=False,
                            ),
                        ],
                        width=12,
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            html.Div(
                                dbc.Alert(
                                    [
                                        html.I(className="bi bi-info-circle me-2"),
                                        "Enter a query and click Search to see results",
                                    ],
                                    color="info",
                                ),
                                className="text-center p-5",
                            ),
                            id="results-container",
                        ),
                        width=12,
                    )
                ]
            ),
        ]
    )


@callback(
    Output("publication-type-select", "value"),
    Input("publication-type-select", "value"),
    prevent_initial_call=True,
)
def handle_all_types_selection(selected_values):

    if "all" in selected_values and len(selected_values) > 1:

        if selected_values[-1] == "all":
            return ["all"]

        else:
            return [x for x in selected_values if x != "all"]
    return selected_values
