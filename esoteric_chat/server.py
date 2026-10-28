import argparse

from flask import Flask, jsonify, render_template, request

from .commands import ChatEngine

MAX_REQUEST_BYTES = 64 * 1024


def create_app(engine=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
    engine = engine or ChatEngine()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/languages")
    def languages():
        return jsonify(languages=engine.languages())

    @app.post("/api/chat")
    def chat():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("message"), str):
            return jsonify(error="Expected JSON body with a 'message' string"), 400
        language = body.get("language")
        if language is not None and not isinstance(language, str):
            return jsonify(error="'language' must be a string"), 400
        return jsonify(replies=engine.handle(body["message"], language))

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
    create_app().run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
