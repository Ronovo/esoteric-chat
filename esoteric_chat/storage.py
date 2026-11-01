import json
import sqlite3
import threading

MAX_CHATS = 50
MAX_MESSAGES = 1000

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_sub TEXT NOT NULL,
    name TEXT NOT NULL,
    language TEXT,
    draft TEXT NOT NULL DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS chats_by_account ON chats (portfolio_sub);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES chats (id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    meta TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_by_chat ON messages (chat_id);

CREATE TABLE IF NOT EXISTS settings (
    portfolio_sub TEXT PRIMARY KEY,
    theme TEXT
);
"""

CHAT_FIELDS = ("name", "language", "draft")


class ChatLimit(Exception):
    pass


class ChatStore:
    """The chats and settings saved to portfolio accounts. Every method takes the account's `sub` and only touches
    what is the account's."""

    def __init__(self, path):
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(SCHEMA)
        self._lock = threading.Lock()

    def chats(self, sub):
        with self._lock:
            chats = [dict(row, messages=[]) for row in self._db.execute(
                "SELECT id, name, language, draft FROM chats WHERE portfolio_sub = ? ORDER BY id", (sub,))]
            by_id = {chat["id"]: chat for chat in chats}
            for row in self._db.execute(
                    "SELECT chat_id, role, meta, content FROM messages WHERE chat_id IN (SELECT id FROM chats "
                    "WHERE portfolio_sub = ?) ORDER BY id", (sub,)):
                by_id[row["chat_id"]]["messages"].append(
                    {"role": row["role"], "meta": row["meta"], "content": json.loads(row["content"])})
        return chats

    def create(self, sub, name, language):
        with self._lock, self._db:
            count = self._db.execute("SELECT COUNT(*) FROM chats WHERE portfolio_sub = ?", (sub,)).fetchone()[0]
            if count >= MAX_CHATS:
                raise ChatLimit("At most %d chats can be saved to an account." % MAX_CHATS)
            chat_id = self._db.execute("INSERT INTO chats (portfolio_sub, name, language) VALUES (?, ?, ?)",
                                       (sub, name, language)).lastrowid
        return {"id": chat_id, "name": name, "language": language, "draft": "", "messages": []}

    def update(self, sub, chat_id, fields):
        """Sets any of name, language and draft. Returns False when the chat isn't the account's."""
        with self._lock, self._db:
            for field, value in fields.items():
                changed = self._db.execute("UPDATE chats SET %s = ? WHERE id = ? AND portfolio_sub = ?" % field,
                                           (value, chat_id, sub)).rowcount
                if not changed:
                    return False
        return True

    def append(self, sub, chat_id, messages):
        """Adds messages to a chat and drops the oldest past MAX_MESSAGES. Returns False when the chat isn't the
        account's."""
        with self._lock, self._db:
            if not self._owned(sub, chat_id):
                return False
            self._db.executemany("INSERT INTO messages (chat_id, role, meta, content) VALUES (?, ?, ?, ?)",
                                 [(chat_id, m["role"], m["meta"], json.dumps(m["content"])) for m in messages])
            self._db.execute("DELETE FROM messages WHERE chat_id = ? AND id NOT IN (SELECT id FROM messages "
                             "WHERE chat_id = ? ORDER BY id DESC LIMIT ?)", (chat_id, chat_id, MAX_MESSAGES))
        return True

    def clear(self, sub, chat_id):
        """Removes every message from a chat. Returns False when the chat isn't the account's."""
        with self._lock, self._db:
            if not self._owned(sub, chat_id):
                return False
            self._db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        return True

    def delete(self, sub, chat_id):
        with self._lock, self._db:
            return self._db.execute("DELETE FROM chats WHERE id = ? AND portfolio_sub = ?",
                                    (chat_id, sub)).rowcount > 0

    def theme(self, sub):
        with self._lock:
            row = self._db.execute("SELECT theme FROM settings WHERE portfolio_sub = ?", (sub,)).fetchone()
        return row["theme"] if row else None

    def set_theme(self, sub, theme):
        with self._lock, self._db:
            self._db.execute("INSERT INTO settings (portfolio_sub, theme) VALUES (?, ?) "
                             "ON CONFLICT (portfolio_sub) DO UPDATE SET theme = excluded.theme", (sub, theme))

    def _owned(self, sub, chat_id):
        return self._db.execute("SELECT 1 FROM chats WHERE id = ? AND portfolio_sub = ?",
                                (chat_id, sub)).fetchone() is not None
