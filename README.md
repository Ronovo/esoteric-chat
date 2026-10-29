# Esoteric Chat

A Flask chat web app that interprets esoteric languages. It is a port of my esoteric-bot Discord bot.

## Running

Requires Python 3.10 or newer.

```sh
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` elsewhere
pip install -r requirements.txt
python -m esoteric_chat.server   # http://127.0.0.1:5000  (--host, --port, --debug)
```

`python -m esoteric_chat.server` uses Flask's built-in server, which is fine on your own machine or a LAN.
Use `--host 0.0.0.0` so other machines can connect. Don't add `--debug` then: its debugger lets anyone who can
reach the server run Python code on it, and the server warns when the two are used together.

### Docker

The `Dockerfile` runs the app under gunicorn on port 5000. It keeps no data, so it needs no volume.

```sh
docker build -t esoteric-chat .
docker run -d -p 5000:5000 esoteric-chat
```

On every start the container runs `docker/git-sync.sh` before the app. It fetches the latest commit on GitHub
`main`, so a pushed commit goes live on the next restart without rebuilding the image, and removes files the
commit doesn't have. When that commit hasn't been built yet it reinstalls `requirements.txt` first, and a failed
install is tried again on the next start. If GitHub can't be reached the app starts on the code it already has.

| Variable | What it does | Default in the image |
| --- | --- | --- |
| `REPO_URL` | The repo to pull. Set it empty to run exactly what is in the image. | This repo on GitHub |
| `REPO_BRANCH` | Branch to pull | `main` |
| `SYNC_DIR` | Folder the code is pulled into | The app folder |
| `BUILD_CMD` | Runs after pulling a commit that hasn't been built yet | `pip install --no-cache-dir --user -q -r requirements.txt` |

### Log in with a portfolio account

With `PORTFOLIO_SSO_URL` (the portfolio's address) and `PORTFOLIO_SSO_PUBLIC_KEY`
(printed by the portfolio's `python sso.py`) set, the header offers to log in with a portfolio account and shows
who is logged in. It reads **Log in as** and the portfolio username when this browser is logged in to the
portfolio. Nothing is saved to the account yet. Set `ESOTERIC_CHAT_SECRET_KEY` to keep logins across restarts.

## Using the chat

- Pick a language from the dropdown, type code, and press **Enter** (Shift+Enter adds a new line).
  **Try example** lists sample programs for the selected language and fills in the one you pick, **Commands** shows the language's
  valid characters, and **Language Explained** opens the language's esolangs.org page.
- Messages starting with `$` (after any leading spaces) are commands and run regardless of the selected language, except Kallisti: with
  Kallisti selected, every message is repeated back exactly, `$` included.
- Everything after the command name and one whitespace character (a space, tab or new line) is passed on exactly
  as typed.
- Limits: a request is at most 64 KB, and the replies to one message are at most 65,536 characters together
  (longer output is cut off with a note). Brainfart has a 30,000-cell tape and stops after 1,000,000 steps;
  characters that aren't commands don't count. HQ9+ sends at most 10 replies per message, then one more asking
  for smaller programs. The HQ9+ `+` accumulator is shared by everyone using the server.

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

- `GET /api/languages` returns `{"languages": [{"id", "name", "examples", "intro", "info_url", "help"}], "prefix",
  "echo_language"}`, the languages in picker order; the first is selected on load. `examples` is a list of
  `{"label", "code"}`, `intro` is shown when the language is selected (or `null`), and `help` is the card the
  **Commands** button shows. `prefix` starts a command and `echo_language` is the one that repeats commands back,
  so the page labels messages the way the server reads them.
- `POST /api/chat` with `{"message": "...", "language": "bf"}` returns `{"replies": [...]}`. Each reply is
  `{"type": "text" | "error", "text"}`.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover every interpreter, the `$` commands, the HTTP API and portfolio login.
`requirements-dev.txt` includes `requirements.txt`, which the portfolio login tests need.

## Project layout

```
esoteric_chat/interpreters.py   The esoteric language interpreters
esoteric_chat/commands.py       ChatEngine: $commands, language metadata, help cards
esoteric_chat/server.py         Flask app and the command-line entry point
esoteric_chat/templates/        The chat page
esoteric_chat/static/           Client script and styles
tests/                          pytest suite
pytest.ini
docker/git-sync.sh              Updates the container from GitHub on start
Dockerfile
requirements.txt                Flask, PyJWT and ronovo-portfolio-auth (portfolio login)
requirements-dev.txt            Adds pytest
```

## Differences from the Discord bot

- Brainfart supports nested loops, uses 8-bit wrapping cells and stops after 1,000,000 steps.
- HQ9+ accepts upper- and lowercase commands, and the `+` accumulator is kept in memory per server process
  instead of in `index.json`.
- `$close` was dropped because there is no bot connection to close.
- Kallisti scrambles each message with 1 to 6 passes picked at random (reverse, swap case, shift letters, rotate,
  flip blocks, riffle), each with a random amount up to 6, then undoes them in reverse order, so the message still
  comes back exactly as sent.

## License

BSD 2-Clause. See [LICENSE](LICENSE).
