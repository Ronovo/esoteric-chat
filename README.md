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

## Using the chat

- Pick a language from the dropdown, type code, and press **Enter** (Shift+Enter adds a new line).
  **Try example** lists sample programs for the selected language and fills in the one you pick, **Commands** shows the language's
  valid characters, and **Language Explained** opens its esolangs.org page.
- Messages starting with `$` are commands and run regardless of the selected language, except Kallisti: with
  Kallisti selected, every message is repeated back exactly, `$` included.
- Everything after the command name and one space (or new line) is passed on exactly as typed.

| Command | Description |
| --- | --- |
| `$ping` | Returns pong in Brainfart |
| `$hi` / `$hello` | Returns hello in Brainfart |
| `$fivecommand <code>` | 5command |
| `$bf <code>` | Brainfart |
| `$deadsimple <code>` | DeadSimple |
| `$hatemath <code>` | Hatemath |
| `$hq9plus <code>` | HQ9+ |
| `$kallisti <code>` | Kallisti |
| `$unnecessary <code>` | Unnecessary (an empty program or `#` is a successful call) |

## API

- `GET /api/languages` returns `{"languages": [{"id", "name", "examples", "intro", "info_url", "help"}]}` in picker
  order; the first is selected on load. `examples` is a list of `{"label", "code"}`, `intro` is shown when the
  language is selected (or `null`), and `help` is the card the **Commands** button shows.
- `POST /api/chat` with `{"message": "...", "language": "bf"}` returns `{"replies": [...]}`. Each reply is
  `{"type": "text" | "error", "text"}` or `{"type": "help", "title", "color", "fields": [{"name", "value"}]}`.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover every interpreter, the `$` commands, and the HTTP API.

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
- Kallisti reverses each message, swaps its upper and lower case and shifts every letter 5 places, then undoes
  all three, so the message still comes back exactly as sent.
