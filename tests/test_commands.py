import pytest

from esoteric_chat import interpreters as interp
from esoteric_chat.commands import HELP, LANGUAGES, ChatEngine, info_url


@pytest.fixture
def engine():
    return ChatEngine()


def texts(replies):
    return [r["text"] for r in replies]


class TestCommands:
    def test_ping(self, engine):
        assert texts(engine.handle("$ping")) == [interp.PING_BF]

    @pytest.mark.parametrize("name", ["hello", "hi"])
    def test_hello(self, engine, name):
        assert texts(engine.handle("$" + name)) == [interp.HELLO_BF]

    def test_bf_command(self, engine):
        assert texts(engine.handle("$bf ++++++++[>++++++++<-]>+.")) == ["A"]

    def test_command_ignores_selected_language(self, engine):
        assert texts(engine.handle("$deadsimple S%S", language="bf")) == ["Aa"]

    def test_command_name_case_insensitive(self, engine):
        assert texts(engine.handle("$PING")) == [interp.PING_BF]

    def test_multiline_command_argument(self, engine):
        assert texts(engine.handle("$kallisti line one\nline two")) == ["line one\nline two"]

    def test_command_without_args(self, engine):
        assert texts(engine.handle("$unnecessary")) == ["*"]

    def test_unknown_command(self, engine):
        [reply] = engine.handle("$nope")
        assert reply["type"] == "error"
        assert "$nope" in reply["text"]

    def test_bare_prefix(self, engine):
        [reply] = engine.handle("$")
        assert reply["type"] == "error"

    def test_debugfivecommand(self, engine):
        assert texts(engine.handle("$debugfivecommand ^p")) == ["Result : 1", "Debug : ^ 1, P"]

    def test_fivecommand(self, engine):
        assert texts(engine.handle("$fivecommand ^p+^^^p+^^^p+^^^^^^^p")) == ["1337"]


class TestErrors:
    def test_interpreter_error_includes_reason(self, engine):
        [reply] = engine.handle("$bf [")
        assert reply["type"] == "error"
        assert reply["text"].startswith("Invalid Brainfart Command: unmatched")

    def test_unexpected_error_uses_original_message(self, engine):
        assert engine.handle("$hatemath <+") == [{"type": "error", "text": "Invalid Hatemath Command"}]

    def test_deadsimple_error(self, engine):
        [reply] = engine.handle("$deadsimple -")
        assert reply["type"] == "error"
        assert reply["text"].startswith("Invalid DeadSimple Command")


class TestLanguagePicker:
    @pytest.mark.parametrize("language", list(LANGUAGES))
    def test_every_example_runs(self, engine, language):
        replies = engine.handle(LANGUAGES[language]["example"], language=language)
        assert replies
        assert all(r["type"] == "text" for r in replies)

    @pytest.mark.parametrize("language, code, expected", [
        ("bf", "++++++++[>++++++++<-]>+.", ["A"]),
        ("kallisti", "  spaced out  ", ["  spaced out  "]),
        ("unnecessary", "#", ["*"]),
        ("unnecessary", "print", ["Unsuccessful"]),
        ("hq9plus", "qhq", ["qhq", "Hello World! :)", "qhq"]),
        ("hatemath", "<^^^^^^^^]^]", ["hi"]),
        ("deadsimple", "S%+S^++S", ["AbC"]),
        ("fivecommand", "^p+^^^p+^^^p+^^^^^^^p", ["1337"]),
    ])
    def test_runs_selected_language(self, engine, language, code, expected):
        assert texts(engine.handle(code, language=language)) == expected

    def test_no_language_selected(self, engine):
        [reply] = engine.handle("+++.")
        assert reply["type"] == "error"

    def test_unknown_language(self, engine):
        [reply] = engine.handle("+++.", language="cobol")
        assert reply == {"type": "error", "text": "Unknown language: cobol"}

    def test_hq9_accumulator_shared_across_messages(self, engine):
        assert texts(engine.handle("+", language="hq9plus")) == ["Accumulator is now at 1"]
        assert texts(engine.handle("$hq9plus +")) == ["Accumulator is now at 2"]

    def test_languages_listing(self, engine):
        listing = engine.languages()
        assert [l["id"] for l in listing] == list(LANGUAGES)
        assert all({"id", "name", "example", "info_url", "help"} <= l.keys() for l in listing)

    def test_languages_listing_help_matches_help_command(self, engine):
        bf = engine.languages()[0]
        assert [bf["help"]] == engine.handle("$help bf")

    @pytest.mark.parametrize("language, url", [
        ("bf", "https://esolangs.org/wiki/brainfuck"),
        ("kallisti", "https://bit.ly/2SdwN4b"),
        ("unnecessary", "https://esolangs.org/wiki/unnecessary"),
        ("hq9plus", "https://esolangs.org/wiki/HQ9%2B"),
        ("hatemath", "https://esolangs.org/wiki/Hatemath"),
        ("deadsimple", "https://esolangs.org/wiki/DeadSimple"),
        ("fivecommand", "https://esolangs.org/wiki/5command"),
        ("debugfivecommand", "https://esolangs.org/wiki/5command"),
    ])
    def test_info_url(self, language, url):
        assert info_url(language) == url


class TestHelp:
    def test_general_help(self, engine):
        [card] = engine.handle("$help")
        assert card["type"] == "help"
        assert card["title"] == "Help"
        names = [f["name"] for f in card["fields"]]
        assert "$bf <code>" in names

    @pytest.mark.parametrize("topic", [t for t in HELP if t != "help"])
    def test_language_help(self, engine, topic):
        [card] = engine.handle("$help " + topic)
        assert card["type"] == "help"
        assert card["title"] == HELP[topic]["title"]
        assert card["fields"]

    def test_every_language_has_help(self):
        assert set(LANGUAGES) <= set(HELP)

    def test_invalid_help_topic(self, engine):
        assert engine.handle("$help cobol") == [{"type": "error", "text": "Invalid Command"}]
