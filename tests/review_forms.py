"""Read actual browser form fields for review endpoint tests."""

from html.parser import HTMLParser
import re

import app.server as server


class ReviewForms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("action", "").startswith("/review/"):
            self.current = {}
        elif tag == "input" and self.current is not None and attrs.get("type") == "hidden":
            self.current[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None


def result_id_from_html(body):
    match = re.search(r'/export/([A-Za-z0-9_-]+)', body)
    assert match, "result capability missing"
    return match.group(1)


def seed_result(doc, ledger=None):
    result_id = server._store_result(doc)
    if ledger is not None:
        server.app.state.results[result_id]["review_ledger"] = ledger
    return result_id


async def review_form(client, argument_id="argument:0", *, result_id):
    response = await client.get(f"/result/{result_id}")
    assert response.status_code == 200
    parser = ReviewForms()
    parser.feed(response.text)
    return next(form for form in parser.forms if form["argument_id"] == argument_id)
