import sys

import pytest

from esoteric_chat import server
from esoteric_chat.commands import LANGUAGES
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
    body = res.get_json()
    assert (body["prefix"], body["echo_language"]) == ("$", "kallisti")
    languages = {l["id"]: l for l in body["languages"]}
    assert list(languages) == list(LANGUAGES)
    assert all({"id", "name", "examples", "intro", "info_url", "help"} <= l.keys() for l in languages.values())
    assert languages["bf"]["info_url"] == "https://esolangs.org/wiki/brainfuck"
    assert languages["bf"]["help"]["title"] == "Brainfart"


def test_security_headers(client):
    headers = client.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_chat_with_language(client):
    res = client.post("/api/chat", json={"message": "S%+S^++S", "language": "deadsimple"})
    assert res.status_code == 200
    assert res.get_json() == {"replies": [{"type": "text", "text": "AbC"}]}


def test_chat_command(client):
    res = client.post("/api/chat", json={"message": "$bf ++++++++[>++++++++<-]>+."})
    assert res.get_json()["replies"] == [{"type": "text", "text": "A"}]


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


def test_coverage_reports_are_served_from_their_folder(client, monkeypatch, tmp_path):
    reports = tmp_path / "coverage"
    (reports / "python").mkdir(parents=True)
    (reports / "index.html").write_text("landing page", encoding="utf-8")
    (reports / "python" / "index.html").write_text("python report", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    monkeypatch.setattr(server, "COVERAGE_DIR", reports)
    assert client.get("/coverage").status_code == 308
    assert client.get("/coverage/").data == b"landing page"
    assert client.get("/coverage/python/").data == b"python report"
    for path in ("/coverage/js/", "/coverage/../secret.txt", "/coverage/%2e%2e/secret.txt"):
        assert client.get(path).status_code == 404, path


@pytest.mark.parametrize("host, warned", [("0.0.0.0", True), ("localhost", False)])
def test_main_runs_the_app_and_warns_about_public_debugging(monkeypatch, capsys, host, warned):
    run = []
    monkeypatch.setattr(sys, "argv", ["server.py", "--host", host, "--port", "5050", "--debug"])
    monkeypatch.setattr(server.Flask, "run", lambda app, **options: run.append(options))
    server.main()
    assert run == [{"host": host, "port": 5050, "debug": True}]
    assert ("Warning" in capsys.readouterr().out) == warned


def test_main_runs_privately_by_default(monkeypatch, capsys):
    run = []
    monkeypatch.setattr(sys, "argv", ["server.py"])
    monkeypatch.setattr(server.Flask, "run", lambda app, **options: run.append(options))
    server.main()
    assert run == [{"host": "127.0.0.1", "port": 5000, "debug": False}]
    assert capsys.readouterr().out == ""


def test_deeply_nested_json_is_refused(client):
    nested = b"[" * 30_000 + b"]" * 30_000
    assert client.post("/api/chat", data=nested, content_type="application/json").status_code == 400
