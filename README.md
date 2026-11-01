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

The `Dockerfile` runs the app under gunicorn on port 5000. Saved chats and the generated session key live in
`/app/data`, so mount a volume there to keep them.

```sh
docker build -t esoteric-chat .
docker run -d -p 5000:5000 -v esoteric-chat-data:/app/data esoteric-chat
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
| `ESOTERIC_CHAT_DATA_DIR` | Folder for `chats.db` and the generated session key | `/app/data` (outside Docker: `data/` in the repo) |

### Log in with a portfolio account

With `PORTFOLIO_SSO_URL` (the portfolio's address) and `PORTFOLIO_SSO_PUBLIC_KEY`
(printed by the portfolio's `python sso.py`) set, the header offers to log in with a portfolio account and shows
who is logged in. It reads **Log in as** and the portfolio username when this browser is logged in to the
portfolio. Logged in, your chats and theme are saved to the account and come back on the next visit, on any
device; logged out, chats last until the page is reloaded and the theme is kept in this browser. Logins last across restarts: the session key is `ESOTERIC_CHAT_SECRET_KEY` when set,
otherwise one is generated once into the data folder.

## Using the chat

- Pick a language from the dropdown, type code, and press **Enter** (Shift+Enter adds a new line).
  **Try example** lists sample programs for the selected language and fills in the one you pick, **Commands** shows the language's
  valid characters, and **Language Explained** opens the language's esolangs.org page.
- **New chat** opens another chat in the sidebar. Each chat keeps its own messages, language and unsent draft, so
  you can switch between them and back. Close a chat with its × button; the last one stays open.
- **Clear Chat** asks first, then empties the open chat's messages. Its name, language and unsent draft stay, and
  it's disabled while that chat waits for a reply.
- The theme picker in the header switches between Esoteric (the default, which follows the system's light or dark
  setting), Cyberpunk, Dark, Light, Punch Card, Chalkboard and Baby Girl. The choice is kept in this
  browser, and also saved to your portfolio account when you're logged in.
- Every message runs in the selected language. Kallisti repeats every message back exactly: it first replies with
  the message as it looked once scrambled, under a "Scrambled:" line, then with the exact echo.
- Limits: a request is at most 64 KB, and the replies to one message are at most 65,536 characters together
  (longer output is cut off with a note; for Kallisti only the scrambled copy is cut, so the echo always comes back
  whole). Brainfart has a 30,000-cell tape and stops after 1,000,000 steps;
  characters that aren't commands don't count. The HQ9+ `+` accumulator is shared by everyone using the server.
  An account can save 50 chats, and a chat keeps its newest 1,000 messages.

## API

- `GET /api/languages` returns `{"languages": [{"id", "name", "examples", "intro", "info_url", "help"}]}`, the
  languages in picker order; the first is selected on load. `examples` is a list of `{"label", "code"}`, `intro` is
  shown when the language is selected (every language has one), and `help` is the card the **Commands** button shows.
- `POST /api/chat` with `{"message": "...", "language": "bf"}` returns `{"replies": [...]}`. Each reply is
  `{"type": "text" | "error", "text"}`. Add `"chat_id"` and `"meta"` (the label shown on the sent message) to
  also save the message and its replies to that chat; this needs a portfolio login.
- The saved-chat routes need a portfolio login and only reach the account's own chats (404 otherwise):
  `GET /api/chats` returns `{"chats": [{"id", "name", "language", "draft", "messages": [{"role", "meta",
  "content"}]}]}`; `POST /api/chats` with `{"name", "language"}` creates one (409 past 50 chats);
  `PATCH /api/chats/<id>` sets any of `name`, `language` and `draft`; `DELETE /api/chats/<id>` removes one; `DELETE /api/chats/<id>/messages` empties one; and
  `POST /api/chats/<id>/messages` with `{"role": "user" | "bot", "meta", "content": {"type", ...}}` appends a
  message the page made itself, such as the welcome or a help card.
- `PUT /api/theme` with `{"theme": "chalkboard"}` saves the theme to the logged-in account (401 without a login,
  400 for a theme the picker doesn't offer). The page then opens on that theme on any device.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover every interpreter, the language examples, the HTTP API, saved chats and portfolio login.
`requirements-dev.txt` includes `requirements.txt`, which the portfolio login tests need.

The chat page's script has its own tests, run with Vitest on Node.js after `npm install` once:

```sh
npm test
```

### Coverage

```sh
python -m coverage run -m pytest
python -m coverage report
python -m coverage html
npm run coverage
```

The HTML reports go to `coverage/python` and `coverage/js`, and the coverage commands fail below 100%. The Docker
image builds both reports and serves them at `/coverage/`, under the landing page in `coverage-index/`, the
`ronovos-coverage-index` submodule, with this repo's `coverage-reports.json`. Failing tests or low coverage don't
stop the image build; the reports show what is missing.

## Project layout

```
esoteric_chat/interpreters.py   The esoteric language interpreters
esoteric_chat/commands.py       ChatEngine: runs the languages, language metadata, help cards
esoteric_chat/server.py         Flask app and the command-line entry point
esoteric_chat/storage.py        ChatStore: the chats saved to portfolio accounts (SQLite)
esoteric_chat/templates/        The chat page
esoteric_chat/static/           Client script and styles
tests/                          pytest suite; js/ holds the chat page's Vitest tests
coverage-index/                 The test coverage landing page, the ronovos-coverage-index submodule
coverage-reports.json           This repo's entry for that page: its name and reports
pytest.ini
docker/git-sync.sh              Updates the container from GitHub on start
Dockerfile
requirements.txt                Flask, PyJWT and ronovo-portfolio-auth (portfolio login)
requirements-dev.txt            Adds pytest and coverage
package.json                    The chat page's test tools (Vitest, jsdom)
```

## Differences from the Discord bot

- Brainfart supports nested loops, uses 8-bit wrapping cells and stops after 1,000,000 steps.
- HQ9+ accepts upper- and lowercase commands, the `+` accumulator is kept in memory per server process
  instead of in `index.json`, and the 10-reply limit is gone (the output cap covers it).
- The `$` commands are gone (`$ping`, `$hi`, `$hello`, `$close` and one per language). Every message runs in the
  selected language, and **Try example** holds the sample programs.
- DeadSimple works as described on esolangs.org: one number that starts at 0, `+` and `-` change it, `_` resets it
  and `S` prints it as a Unicode character. The bot's `^` and `%` letter commands are gone.
- Kallisti scrambles each message with 1 to 13 passes picked at random (reverse, swap case, shift letters, rotate,
  flip blocks, riffle, mirror alphabet, leetspeak, reverse each word, wave case, deal into piles), each with a random
  amount up to 6, then undoes them in reverse order, so the message still comes back exactly as sent. The scrambled
  message is shown first.

## License

BSD 2-Clause. See [LICENSE](LICENSE).
