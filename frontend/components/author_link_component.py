from dash import html


try:
    from components.author_resolution_helper import resolve_author_names
except ImportError:

    def resolve_author_names(author_ids, timeout=5, retry_count=2):

        return {aid: {"id": aid, "full_name": f"ID: {aid}"} for aid in author_ids}


author_name_cache = {}


def resolve_author_name(author_id):

    if author_id in author_name_cache:
        return author_name_cache[author_id]

    author_data = resolve_author_names([author_id])
    if author_id in author_data and "full_name" in author_data[author_id]:

        author_name_cache[author_id] = author_data[author_id]["full_name"]
        return author_name_cache[author_id]

    author_name_cache[author_id] = f"ID: {author_id}"
    return author_name_cache[author_id]


def create_article_author_links(author_ids, className=""):

    if not author_ids:
        return html.Span("No author information", className=className)

    if isinstance(author_ids, str):
        author_ids = [author_ids]

    author_data = resolve_author_names(author_ids)

    author_links = []

    for i, author_id in enumerate(author_ids):

        if i > 0:
            author_links.append(", ")

        author_name = "Unknown"
        if author_id in author_data:
            author_name = author_data[author_id].get("full_name", f"ID: {author_id}")
        else:
            author_name = f"ID: {author_id}"

        author_links.append(
            html.A(
                author_name,
                id={"type": "author-link", "id": author_id},
                href="#",
                className="text-primary",
                style={"cursor": "pointer", "textDecoration": "none"},
            )
        )

    return html.Span(author_links, className=className)


def create_article_author_links_for_modal(author_ids, className=""):

    if not author_ids:
        return html.Span("No author information", className=className)

    if isinstance(author_ids, str):
        author_ids = [author_ids]

    author_data = resolve_author_names(author_ids)

    author_links = []

    for i, author_id in enumerate(author_ids):

        if i > 0:
            author_links.append(", ")

        author_name = "Unknown"
        if author_id in author_data:
            author_name = author_data[author_id].get("full_name", f"ID: {author_id}")
        else:
            author_name = f"ID: {author_id}"

        author_links.append(
            html.A(
                author_name,
                id={"type": "author-link-modal", "id": author_id},
                href="#",
                className="text-primary",
                style={"cursor": "pointer", "textDecoration": "none"},
            )
        )

    return html.Span(author_links, className=className)


def create_author_detail_content(author_data):

    if not author_data:
        return html.Div("Author information not available")

    return html.Div(
        [
            html.H4(author_data.get("full_name", "Unknown Author"), className="mb-3"),
            html.Div(
                [
                    html.Strong("Unit: "),
                    html.Span(author_data.get("unit", "Not specified")),
                ],
                className="mb-2",
            ),
            html.Div(
                [
                    html.Strong("Subunit: "),
                    html.Span(author_data.get("subunit", "Not specified")),
                ],
                className="mb-2",
            ),
            html.Div(
                [
                    html.Strong("Publications: "),
                    html.Span(str(len(author_data.get("publications", [])))),
                ],
                className="mb-2",
            ),
            html.Div(
                [
                    html.A(
                        "View full author profile",
                        id={"type": "author-link", "id": author_data.get("id", "")},
                        href="#",
                        className="btn btn-primary btn-sm mt-3",
                    )
                ]
            ),
        ]
    )
