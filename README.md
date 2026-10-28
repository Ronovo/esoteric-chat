# Esoteric Chat

A Flask chat web app that interprets esoteric languages. It is a port of my esoteric-bot Discord bot.

## Running

Requires Python 3.9 or newer.

```sh
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` elsewhere
pip install -r requirements.txt
python -m esoteric_chat.server   # http://127.0.0.1:5000  (--host, --port, --debug)
```

`python -m esoteric_chat.server` uses Flask's built-in server, which is fine on your own machine or a LAN.
Use `--host 0.0.0.0` so other machines can connect.

### Docker

The `Dockerfile` runs the app under gunicorn on port 5000. It keeps no data, so it needs no volume.

```sh
docker build -t esoteric-chat .
docker run -d -p 5000:5000 esoteric-chat
```

### Inside another site

`esoteric_chat.server.create_app()` returns a normal WSGI app, so a larger Flask site can mount it under a
path. The page and its API use relative URLs, so the path can be anything. Pass `BACK_LINK`, a
`{"href", "label"}` pair, to show a back link at the top of the page:

```python
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from esoteric_chat.server import create_app as create_esoteric_chat

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/esoteric-chat": create_esoteric_chat({"BACK_LINK": {"href": "/projects", "label": "Projects"}}),
})
```

## Using the chat

- Pick a language from the dropdown, type code, and press **Enter** (Shift+Enter adds a new line).
  **Try example** fills in a sample program for the selected language, **Commands** shows the language's
  valid characters, and **Language Explained** opens its esolangs.org page.
- Messages starting with `$` are commands and run regardless of the selected language.

| Command | Description |
| --- | --- |
| `$ping` | Returns pong in Brainfart |
| `$hi` / `$hello` | Returns hello in Brainfart |
| `$bf <code>` | Brainfart |
| `$kallisti <code>` | Kallisti |
| `$unnecessary <code>` | Unnecessary |
| `$hq9plus <code>` | HQ9+ |
| `$hatemath <code>` | Hatemath |
| `$deadsimple <code>` | DeadSimple |
| `$fivecommand <code>` | 5command |
| `$debugfivecommand <code>` | 5command with a debug log |
| `$help` / `$help <command>` | Help, or details about one language |

## API

- `GET /api/languages` returns `{"languages": [{"id", "name", "example", "intro", "info_url", "help"}]}`, where `intro` is shown when
  the language is selected (or `null`) and `help`
  is the same card `$help <id>` returns
- `POST /api/chat` with `{"message": "...", "language": "bf"}` returns `{"replies": [...]}`. Each reply is
  `{"type": "text" | "error", "text"}` or `{"type": "help", "title", "color", "fields": [{"name", "value"}]}`.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover every interpreter, the `$` commands, the HTTP API, and running mounted under a path.

## Project layout

```
esoteric_chat/interpreters.py   The esoteric language interpreters
esoteric_chat/commands.py       ChatEngine: $commands, language metadata, help cards
esoteric_chat/server.py         Flask app and the command-line entry point
esoteric_chat/templates/        The chat page
esoteric_chat/static/           Client script and styles
tests/                          pytest suite
```

## Differences from the Discord bot

- Brainfart supports nested loops, uses 8-bit wrapping cells and stops after 1,000,000 steps.
- HQ9+ accepts upper- and lowercase commands, and the `+` accumulator is kept in memory per server process
  instead of in `index.json`.
- `$close` was dropped because there is no bot connection to close.
