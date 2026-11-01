import argparse
import os
import secrets
from pathlib import Path

from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from ronovo_portfolio_auth import portfolio_sso

from .commands import ChatEngine, language_listing
from .storage import CHAT_FIELDS, ChatLimit, ChatStore

MAX_REQUEST_BYTES = 64 * 1024
MAX_NAME_LENGTH = 80
ROOT = Path(__file__).resolve().parent.parent
COVERAGE_DIR = ROOT / "coverage"
DEFAULT_DATA_DIR = ROOT / "data"
LOGIN_NEEDED = "Log in with your portfolio account to save to it"
# The picker lists these in this order. Every theme but esoteric, the default, has a block in static/style.css.
THEMES = {"esoteric": "Esoteric", "cyberpunk": "Cyberpunk", "dark": "Dark", "light": "Light",
          "punch-card": "Punch Card", "chalkboard": "Chalkboard", "baby-girl": "Baby Girl"}


def secret_key(data_dir):
    """ESOTERIC_CHAT_SECRET_KEY, or a key generated once into the data folder so logins survive restarts."""
    configured = os.environ.get("ESOTERIC_CHAT_SECRET_KEY")
    if configured:
        return configured
    path = data_dir / "secret_key"
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def create_app():
    data_dir = Path(os.environ.get("ESOTERIC_CHAT_DATA_DIR") or DEFAULT_DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
        SECRET_KEY=secret_key(data_dir),
        SESSION_COOKIE_NAME="esoteric_chat_session",
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SECURE_COOKIES") == "1",
    )
    engine = ChatEngine()
    store = ChatStore(data_dir / "chats.db")
    listing = {"languages": language_listing()}

    def portfolio_login(account, next_path):
        session.clear()
        session.permanent = True
        session["portfolio_sub"] = account["sub"]
        session["portfolio_user"] = account["username"]
        return redirect(next_path or url_for("index"))

    def portfolio_error(reason):
        flash(portfolio_sso.LOGIN_MESSAGES[reason])
        return redirect(url_for("index"))

    portfolio_sso.add_flask_routes(app, "esoteric-chat", portfolio_login, portfolio_error)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.get("/")
    def index():
        portfolio = portfolio_sso.enabled()
        sub = session.get("portfolio_sub")
        account_theme = store.theme(sub) if sub is not None else None
        return render_template("index.html", portfolio=portfolio, logged_in=sub is not None,
                               portfolio_user=session.get("portfolio_user"),
                               portfolio_url=portfolio_sso.portfolio_url() if portfolio else "", themes=THEMES,
                               account_theme=account_theme if account_theme in THEMES else None)

    @app.get("/api/languages")
    def languages():
        return jsonify(listing)

    def json_body():
        try:
            body = request.get_json(silent=True)
        except RecursionError:
            body = None
        return body if isinstance(body, dict) else None

    def account_required(view):
        """The view gets the logged-in portfolio account's sub first; without a login it answers 401."""
        @wraps(view)
        def wrapper(*args, **kwargs):
            sub = session.get("portfolio_sub")
            if sub is None:
                return jsonify(error=LOGIN_NEEDED), 401
            return view(sub, *args, **kwargs)
        return wrapper

    def chat_fields(body):
        """The name, language and draft fields of a request body that are set and well formed, or an error."""
        fields = {}
        for field in CHAT_FIELDS:
            if field not in body:
                continue
            value = body[field]
            if field == "language" and value is None:
                fields[field] = None
            elif not isinstance(value, str):
                return None, "'%s' must be a string" % field
            elif field == "name" and not 0 < len(value.strip()) <= MAX_NAME_LENGTH:
                return None, "'name' must be 1 to %d characters" % MAX_NAME_LENGTH
            else:
                fields[field] = value
        return fields, None

    @app.post("/api/chat")
    def chat():
        body = json_body()
        if body is None or not isinstance(body.get("message"), str):
            return jsonify(error="Expected JSON body with a 'message' string"), 400
        language = body.get("language")
        if language is not None and not isinstance(language, str):
            return jsonify(error="'language' must be a string"), 400
        chat_id = body.get("chat_id")
        if chat_id is not None:
            if not isinstance(chat_id, int) or not isinstance(body.get("meta"), str):
                return jsonify(error="'chat_id' must be a number and 'meta' a string"), 400
            if "portfolio_sub" not in session:
                return jsonify(error=LOGIN_NEEDED), 401
        replies = engine.handle(body["message"], language)
        if chat_id is not None:
            sent = {"role": "user", "meta": body["meta"], "content": {"type": "text", "text": body["message"]}}
            answers = [{"role": "bot", "meta": "Esoteric Chat", "content": reply} for reply in replies]
            if not store.append(session["portfolio_sub"], chat_id, [sent] + answers):
                return jsonify(error="No such chat"), 404
        return jsonify(replies=replies)

    @app.get("/api/chats")
    @account_required
    def list_chats(sub):
        return jsonify(chats=store.chats(sub))

    @app.post("/api/chats")
    @account_required
    def create_chat(sub):
        body = json_body()
        fields, problem = chat_fields(body or {})
        if body is None or problem or "name" not in fields:
            return jsonify(error=problem or "Expected JSON body with a 'name' string"), 400
        try:
            return jsonify(store.create(sub, fields["name"], fields.get("language"))), 201
        except ChatLimit as e:
            return jsonify(error=str(e)), 409

    @app.patch("/api/chats/<int:chat_id>")
    @account_required
    def update_chat(sub, chat_id):
        body = json_body()
        fields, problem = chat_fields(body or {})
        if body is None or problem or not fields:
            return jsonify(error=problem or "Expected JSON body with a name, language or draft"), 400
        if not store.update(sub, chat_id, fields):
            return jsonify(error="No such chat"), 404
        return "", 204

    @app.delete("/api/chats/<int:chat_id>")
    @account_required
    def delete_chat(sub, chat_id):
        if not store.delete(sub, chat_id):
            return jsonify(error="No such chat"), 404
        return "", 204

    @app.delete("/api/chats/<int:chat_id>/messages")
    @account_required
    def clear_chat(sub, chat_id):
        if not store.clear(sub, chat_id):
            return jsonify(error="No such chat"), 404
        return "", 204

    @app.post("/api/chats/<int:chat_id>/messages")
    @account_required
    def add_message(sub, chat_id):
        body = json_body()
        if (body is None or body.get("role") not in ("user", "bot") or not isinstance(body.get("meta"), str)
                or not isinstance(body.get("content"), dict) or not isinstance(body["content"].get("type"), str)):
            return jsonify(error="Expected a 'role' of user or bot, a 'meta' string and a 'content' object"), 400
        message = {"role": body["role"], "meta": body["meta"], "content": body["content"]}
        if not store.append(sub, chat_id, [message]):
            return jsonify(error="No such chat"), 404
        return "", 204

    @app.put("/api/theme")
    @account_required
    def save_theme(sub):
        body = json_body()
        if body is None or body.get("theme") not in THEMES:
            return jsonify(error="Expected a 'theme' from: %s" % ", ".join(THEMES)), 400
        store.set_theme(sub, body["theme"])
        return "", 204

    @app.get("/coverage/", defaults={"path": ""})
    @app.get("/coverage/<path:path>")
    def coverage(path):
        if not path or path.endswith("/"):
            path += "index.html"
        return send_from_directory(COVERAGE_DIR, path)

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="Message too large"), 413

    return app


def main():
    parser = argparse.ArgumentParser(description="Run the Esoteric Chat web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug and args.host not in ("127.0.0.1", "localhost"):
        print("Warning: --debug lets anyone who can reach this server run Python code on it.")
    create_app().run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
