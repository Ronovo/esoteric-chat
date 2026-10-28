import pytest
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from esoteric_chat.server import create_app

PREFIX = "/esoteric-chat"


@pytest.fixture
def mounted():
    """The chat mounted under a prefix the way the portfolio site mounts it."""
    chat = create_app({"TESTING": True, "BACK_LINK": {"href": "/projects", "label": "Projects"}})
    host = Flask("portfolio")
    host.wsgi_app = DispatcherMiddleware(host.wsgi_app, {PREFIX: chat})
    return host.test_client()


def test_standalone_has_no_back_link():
    assert b'class="back"' not in create_app().test_client().get("/").data


def test_mounted_page_shows_the_back_link(mounted):
    page = mounted.get(f"{PREFIX}/").data
    assert b'<a class="back" href="/projects">&larr; Projects</a>' in page


def test_bare_prefix_redirects_to_trailing_slash(mounted):
    response = mounted.get(PREFIX)
    assert response.status_code == 308
    assert response.headers["Location"].endswith(f"{PREFIX}/")


@pytest.mark.parametrize("path", ["/static/app.js", "/static/style.css", "/api/languages"])
def test_assets_and_api_are_served_under_the_prefix(mounted, path):
    assert mounted.get(PREFIX + path).status_code == 200


def test_chat_works_under_the_prefix(mounted):
    response = mounted.post(f"{PREFIX}/api/chat", json={"message": "$ping"})
    assert response.status_code == 200
    assert response.get_json()["replies"]
