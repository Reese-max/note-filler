"""Read actual browser form fields for review endpoint tests."""

from html.parser import HTMLParser


class ReviewForms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("action") == "/review":
            self.current = {}
        elif tag == "input" and self.current is not None and attrs.get("type") == "hidden":
            self.current[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None


async def review_form(client, argument_id="argument:0"):
    response = await client.get("/result")
    assert response.status_code == 200
    parser = ReviewForms()
    parser.feed(response.text)
    return next(form for form in parser.forms if form["argument_id"] == argument_id)
