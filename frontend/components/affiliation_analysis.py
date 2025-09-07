import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.express as px
import pandas as pd


def create_affiliation_analysis_panel(affiliation_data):

    if not affiliation_data:
        return None

    affiliations = affiliation_data.get("affiliations", [])
    total_articles = affiliation_data.get("total_articles", 0)

    if not affiliations or not total_articles:
        return None

    df = pd.DataFrame(affiliations[:10])

    if df.empty or "name" not in df.columns or "count" not in df.columns:
        return None

    fig = px.bar(
        df,
        x="count",
        y="name",
        orientation="h",
        title="Top Units Contributing to This Topic",
        labels={"count": "Publications", "name": "Academic Unit"},
        template="plotly_white",
        color="percentage" if "percentage" in df.columns else None,
        color_continuous_scale=px.colors.sequential.Viridis,
        text="percentage" if "percentage" in df.columns else None,
    )

    if "percentage" in df.columns:
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")

    fig.update_layout(
        xaxis_title="Number of Publications",
        yaxis_title="",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"},
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                [html.I(className="bi bi-building me-2"), "Academic Units Analysis"]
            ),
            dbc.CardBody(
                [
                    html.P(
                        "This chart shows which academic units are most active in this topic.",
                        className="mb-3",
                    ),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                    html.Div(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-box-arrow-up-right me-2"),
                                    "Explore Academic Units",
                                ],
                                id="goto-units-button",
                                color="link",
                                className="mt-2",
                                n_clicks=0,
                            )
                        ],
                        className="text-end",
                    ),
                ]
            ),
        ],
        className="mb-4 shadow-sm",
    )
