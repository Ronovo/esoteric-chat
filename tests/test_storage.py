import pytest

from esoteric_chat import storage
from esoteric_chat.storage import ChatLimit, ChatStore


def message(text, role="bot"):
    return {"role": role, "meta": "Esoteric Chat", "content": {"type": "text", "text": text}}


@pytest.fixture
def store(tmp_path):
    return ChatStore(tmp_path / "chats.db")


def test_chats_are_listed_per_account_in_order_with_their_messages(store):
    first = store.create("1", "Chat 1", "bf")
    second = store.create("1", "Chat 2", None)
    other = store.create("2", "Theirs", "bf")
    assert store.append("1", second["id"], [message("+.", "user"), message("A")])
    assert store.append("2", other["id"], [message("not yours")])
    chats = store.chats("1")
    assert [c["name"] for c in chats] == ["Chat 1", "Chat 2"]
    assert chats[0] == {"id": first["id"], "name": "Chat 1", "language": "bf", "draft": "", "messages": []}
    assert chats[1]["language"] is None
    assert [m["content"]["text"] for m in chats[1]["messages"]] == ["+.", "A"]
    assert [m["role"] for m in chats[1]["messages"]] == ["user", "bot"]
    assert store.chats("3") == []


def test_update_sets_fields_only_on_the_accounts_chat(store):
    chat = store.create("1", "Chat 1", "bf")
    assert store.update("1", chat["id"], {"name": "Loops", "language": "hq9plus", "draft": "hq"})
    assert not store.update("2", chat["id"], {"draft": "stolen"})
    assert not store.update("1", chat["id"] + 1, {"draft": "missing"})
    saved = store.chats("1")[0]
    assert (saved["name"], saved["language"], saved["draft"]) == ("Loops", "hq9plus", "hq")


def test_append_refuses_other_accounts_chats_and_keeps_only_the_newest(store, monkeypatch):
    monkeypatch.setattr(storage, "MAX_MESSAGES", 3)
    chat = store.create("1", "Chat 1", "bf")
    assert not store.append("2", chat["id"], [message("no")])
    assert store.append("1", chat["id"], [message(str(i)) for i in range(5)])
    assert [m["content"]["text"] for m in store.chats("1")[0]["messages"]] == ["2", "3", "4"]


def test_clear_empties_only_the_accounts_chat(store):
    chat = store.create("1", "Chat 1", "bf")
    other = store.create("1", "Chat 2", "bf")
    store.append("1", chat["id"], [message("A"), message("B")])
    store.append("1", other["id"], [message("kept")])
    store.update("1", chat["id"], {"draft": "+."})
    assert not store.clear("2", chat["id"])
    assert len(store.chats("1")[0]["messages"]) == 2
    assert store.clear("1", chat["id"])
    first, second = store.chats("1")
    assert (first["messages"], first["draft"], first["name"]) == ([], "+.", "Chat 1")
    assert [m["content"]["text"] for m in second["messages"]] == ["kept"]
    assert not store.clear("1", 99)


def test_delete_removes_the_chat_and_its_messages(store):
    chat = store.create("1", "Chat 1", "bf")
    store.append("1", chat["id"], [message("A")])
    assert not store.delete("2", chat["id"])
    assert store.delete("1", chat["id"])
    assert not store.delete("1", chat["id"])
    assert store.chats("1") == []
    assert store._db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_an_account_can_save_a_limited_number_of_chats(store, monkeypatch):
    monkeypatch.setattr(storage, "MAX_CHATS", 2)
    store.create("1", "Chat 1", "bf")
    store.create("1", "Chat 2", "bf")
    with pytest.raises(ChatLimit, match="At most 2 chats"):
        store.create("1", "Chat 3", "bf")
    assert store.create("2", "Chat 1", "bf")["id"] == 3


def test_the_database_survives_reopening(tmp_path):
    chat = ChatStore(tmp_path / "chats.db").create("1", "Chat 1", "bf")
    assert ChatStore(tmp_path / "chats.db").chats("1")[0]["id"] == chat["id"]


def test_themes_are_saved_per_account(store):
    assert store.theme("1") is None
    store.set_theme("1", "chalkboard")
    store.set_theme("2", "light")
    store.set_theme("1", "baby-girl")
    assert (store.theme("1"), store.theme("2"), store.theme("3")) == ("baby-girl", "light", None)
