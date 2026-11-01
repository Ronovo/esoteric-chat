import re
import sys

import pytest

from esoteric_chat import server, storage
from esoteric_chat.commands import LANGUAGES
from esoteric_chat.server import MAX_REQUEST_BYTES, create_app

HI_DEADSIMPLE = "+" * 72 + "S" + "+" * 33 + "S"


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
    assert list(body) == ["languages"]
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
    res = client.post("/api/chat", json={"message": HI_DEADSIMPLE, "language": "deadsimple"})
    assert res.status_code == 200
    assert res.get_json() == {"replies": [{"type": "text", "text": "Hi"}]}


def test_chat_without_a_language(client):
    res = client.post("/api/chat", json={"message": "$unnecessary"})
    assert res.get_json()["replies"] == [{"type": "error", "text": "Pick a language."}]


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


# ---------------------------------------------------------------- saved chats


def log_in(client, sub="1"):
    with client.session_transaction() as sess:
        sess["portfolio_sub"] = sub
        sess["portfolio_user"] = "ronovo"


def create(client, name="Chat 1", language="bf"):
    res = client.post("/api/chats", json={"name": name, "language": language})
    assert res.status_code == 201
    return res.get_json()


def saved(client):
    return client.get("/api/chats").get_json()["chats"]


@pytest.mark.parametrize("method, path", [
    ("GET", "/api/chats"), ("POST", "/api/chats"), ("PATCH", "/api/chats/1"), ("DELETE", "/api/chats/1"),
    ("POST", "/api/chats/1/messages"), ("DELETE", "/api/chats/1/messages"),
])
def test_saved_chats_need_a_portfolio_login(client, method, path):
    res = client.open(path, method=method, json={})
    assert res.status_code == 401
    assert "portfolio" in res.get_json()["error"]


def test_chats_are_created_listed_changed_and_deleted_per_account(client):
    log_in(client)
    chat = create(client)
    assert chat == {"id": 1, "name": "Chat 1", "language": "bf", "draft": "", "messages": []}
    assert create(client, "Chat 2", None)["language"] is None
    assert client.patch("/api/chats/1", json={"draft": "+.", "language": None, "name": "Loops"}).status_code == 204
    assert client.post("/api/chats/1/messages", json={
        "role": "bot", "meta": "Esoteric Chat", "content": {"type": "card", "title": "Brainfart"}}).status_code == 204
    chats = saved(client)
    assert [(c["id"], c["name"], c["language"], c["draft"]) for c in chats] == [(1, "Loops", None, "+."), (2, "Chat 2", None, "")]
    assert chats[0]["messages"] == [{"role": "bot", "meta": "Esoteric Chat", "content": {"type": "card", "title": "Brainfart"}}]

    other = create_app().test_client()
    log_in(other, sub="2")
    assert saved(other) == []
    assert other.patch("/api/chats/1", json={"draft": "x"}).status_code == 404
    assert other.post("/api/chats/1/messages", json={"role": "user", "meta": "m", "content": {"type": "text"}}).status_code == 404
    assert other.delete("/api/chats/1").status_code == 404

    assert client.delete("/api/chats/1").status_code == 204
    assert client.delete("/api/chats/1").status_code == 404
    assert [c["id"] for c in saved(client)] == [2]


@pytest.mark.parametrize("body", [None, {}, {"name": ""}, {"name": "   "}, {"name": "x" * 81}, {"name": 5},
                                  {"name": "ok", "language": 5}])
def test_creating_a_chat_needs_a_short_name_and_a_string_language(client, body):
    log_in(client)
    res = client.post("/api/chats", json=body)
    assert res.status_code == 400
    assert "error" in res.get_json()


@pytest.mark.parametrize("body", [None, {}, {"other": 1}, {"draft": 3}, {"name": ""}])
def test_changing_a_chat_needs_at_least_one_well_formed_field(client, body):
    log_in(client)
    create(client)
    res = client.patch("/api/chats/1", json=body)
    assert res.status_code == 400
    assert "error" in res.get_json()
    assert saved(client)[0]["name"] == "Chat 1"


@pytest.mark.parametrize("body", [None, {}, {"role": "admin", "meta": "m", "content": {"type": "text"}},
                                  {"role": "bot", "meta": 1, "content": {"type": "text"}},
                                  {"role": "bot", "meta": "m", "content": "text"},
                                  {"role": "bot", "meta": "m", "content": {"text": "no type"}}])
def test_saving_a_message_checks_its_shape(client, body):
    log_in(client)
    create(client)
    assert client.post("/api/chats/1/messages", json=body).status_code == 400
    assert saved(client)[0]["messages"] == []


def test_clearing_a_chat_empties_its_messages_for_its_account_only(client):
    log_in(client)
    create(client)
    client.post("/api/chat", json={"message": "+.", "language": "bf", "chat_id": 1, "meta": "Brainfart"})
    other = create_app().test_client()
    log_in(other, sub="2")
    assert other.delete("/api/chats/1/messages").status_code == 404
    assert len(saved(client)[0]["messages"]) == 2
    assert client.delete("/api/chats/1/messages").status_code == 204
    assert saved(client)[0]["messages"] == []
    assert client.delete("/api/chats/2/messages").status_code == 404


def test_an_account_has_a_chat_limit(client, monkeypatch):
    monkeypatch.setattr(storage, "MAX_CHATS", 1)
    log_in(client)
    create(client)
    res = client.post("/api/chats", json={"name": "Chat 2"})
    assert res.status_code == 409
    assert "At most 1 chats" in res.get_json()["error"]


def test_chat_with_a_chat_id_saves_the_message_and_the_replies(client):
    log_in(client)
    create(client)
    res = client.post("/api/chat", json={"message": HI_DEADSIMPLE, "language": "deadsimple", "chat_id": 1, "meta": "DeadSimple"})
    assert res.get_json() == {"replies": [{"type": "text", "text": "Hi"}]}
    res = client.post("/api/chat", json={"message": "[", "language": "bf", "chat_id": 1, "meta": "Brainfart"})
    assert res.status_code == 200
    assert saved(client)[0]["messages"] == [
        {"role": "user", "meta": "DeadSimple", "content": {"type": "text", "text": HI_DEADSIMPLE}},
        {"role": "bot", "meta": "Esoteric Chat", "content": {"type": "text", "text": "Hi"}},
        {"role": "user", "meta": "Brainfart", "content": {"type": "text", "text": "["}},
        {"role": "bot", "meta": "Esoteric Chat",
         "content": {"type": "error", "text": "Invalid Brainfart Command: unmatched '[' at position 0"}},
    ]


@pytest.mark.parametrize("extra, status", [
    ({"chat_id": "1", "meta": "m"}, 400), ({"chat_id": 1}, 400), ({"chat_id": 1, "meta": "m", "language": 3}, 400),
    ({"chat_id": 2, "meta": "m"}, 404),
])
def test_chat_with_a_bad_chat_id_saves_nothing(client, extra, status):
    log_in(client)
    create(client)
    res = client.post("/api/chat", json={"message": "+", "language": "hq9plus", **extra})
    assert res.status_code == status
    assert saved(client)[0]["messages"] == []


def test_chat_with_a_chat_id_needs_a_login(client):
    res = client.post("/api/chat", json={"message": "+.", "language": "bf", "chat_id": 1, "meta": "Brainfart"})
    assert res.status_code == 401
    assert client.post("/api/chat", json={"message": "+.", "language": "bf"}).status_code == 200


def test_secret_key_is_generated_once_into_the_data_folder(data_dir, monkeypatch):
    monkeypatch.delenv("ESOTERIC_CHAT_SECRET_KEY", raising=False)
    key = create_app().secret_key
    assert (data_dir / "secret_key").read_text(encoding="utf-8") == key
    assert create_app().secret_key == key
    monkeypatch.setenv("ESOTERIC_CHAT_SECRET_KEY", "configured")
    assert create_app().secret_key == "configured"


def test_data_folder_defaults_next_to_the_package(monkeypatch, tmp_path):
    monkeypatch.delenv("ESOTERIC_CHAT_DATA_DIR")
    monkeypatch.setattr(server, "DEFAULT_DATA_DIR", tmp_path / "default")
    create_app()
    assert (tmp_path / "default" / "chats.db").exists()


# ---------------------------------------------------------------- themes


def html_tag(client):
    page = client.get("/").data.decode()
    return page[page.index("<html"):page.index(">", page.index("<html")) + 1]


def test_the_picker_lists_every_theme_in_order(client):
    page = client.get("/").data.decode()
    assert re.findall(r'<option value="([\w-]+)">', page) == list(server.THEMES)
    assert 'data-theme="esoteric" data-account-theme=""' in html_tag(client)


def test_a_theme_is_saved_to_the_account_and_put_on_its_pages(client):
    log_in(client)
    assert client.put("/api/theme", json={"theme": "chalkboard"}).status_code == 204
    assert 'data-theme="chalkboard" data-account-theme="chalkboard"' in html_tag(client)
    assert 'data-logged-in="1"' in html_tag(client)
    other = create_app().test_client()
    log_in(other, sub="2")
    assert 'data-theme="esoteric" data-account-theme=""' in html_tag(other)


def test_a_saved_theme_that_is_no_longer_offered_is_not_used(client, monkeypatch):
    log_in(client)
    client.put("/api/theme", json={"theme": "chalkboard"})
    monkeypatch.delitem(server.THEMES, "chalkboard")
    assert 'data-theme="esoteric" data-account-theme=""' in html_tag(client)


@pytest.mark.parametrize("body", [None, {}, {"theme": "hud"}, {"theme": 3}])
def test_saving_a_theme_needs_one_from_the_list(client, body):
    log_in(client)
    res = client.put("/api/theme", json=body)
    assert res.status_code == 400
    assert "baby-girl" in res.get_json()["error"]
    assert 'data-account-theme=""' in html_tag(client)


def test_saving_a_theme_needs_a_login(client):
    res = client.put("/api/theme", json={"theme": "light"})
    assert res.status_code == 401
    assert 'data-logged-in=""' in html_tag(client)
