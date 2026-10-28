import pytest

from esoteric_chat.server import MAX_REQUEST_BYTES, create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_index_serves_chat_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"<title>Esoteric Chat</title>" in res.data


@pytest.mark.parametrize("path", ["/static/app.js", "/static/style.css"])
def test_static_assets(client, path):
    assert client.get(path).status_code == 200


def test_languages(client):
    res = client.get("/api/languages")
    assert res.status_code == 200
    languages = {l["id"]: l for l in res.get_json()["languages"]}
    assert "bf" in languages and "hq9plus" in languages
    assert languages["bf"]["info_url"] == "https://esolangs.org/wiki/brainfuck"
    assert languages["bf"]["help"]["title"] == "Brainfart"


def test_index_has_toolbar_buttons(client):
    page = client.get("/").data
    assert b'id="example"' in page
    assert b'id="commands"' in page
    assert b'id="explained"' in page


def test_chat_with_language(client):
    res = client.post("/api/chat", json={"message": "S%+S^++S", "language": "deadsimple"})
    assert res.status_code == 200
    assert res.get_json() == {"replies": [{"type": "text", "text": "AbC"}]}


def test_chat_command(client):
    res = client.post("/api/chat", json={"message": "$bf ++++++++[>++++++++<-]>+."})
    assert res.get_json()["replies"] == [{"type": "text", "text": "A"}]


def test_chat_help(client):
    [card] = client.post("/api/chat", json={"message": "$help bf"}).get_json()["replies"]
    assert card["type"] == "help"
    assert card["title"] == "Brainfart"


def test_hq9_accumulator_persists_between_requests(client):
    client.post("/api/chat", json={"message": "+", "language": "hq9plus"})
    res = client.post("/api/chat", json={"message": "+", "language": "hq9plus"})
    assert res.get_json()["replies"] == [{"type": "text", "text": "Accumulator is now at 2"}]


@pytest.mark.parametrize("body", [None, [], {}, {"message": 5}, {"message": "+", "language": 3}])
def test_bad_requests(client, body):
    res = client.post("/api/chat", json=body)
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_invalid_json(client):
    res = client.post("/api/chat", data="{not json", content_type="application/json")
    assert res.status_code == 400


def test_message_too_large(client):
    res = client.post("/api/chat", json={"message": "+" * (MAX_REQUEST_BYTES + 1)})
    assert res.status_code == 413
    assert res.get_json() == {"error": "Message too large"}


def test_unknown_route(client):
    assert client.get("/nope").status_code == 404
