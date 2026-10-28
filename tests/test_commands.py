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

    def test_command_keeps_argument_exactly(self, engine):
        assert texts(engine.handle("$kallisti   two  spaces  ")) == ["  two  spaces  "]

    def test_kallisti_repeats_dollar_messages(self, engine):
        assert texts(engine.handle("$ping", language="kallisti")) == ["$ping"]

    def test_command_without_args(self, engine):
        assert texts(engine.handle("$unnecessary")) == ["*"]

    def test_unknown_command(self, engine):
        [reply] = engine.handle("$nope")
        assert reply["type"] == "error"
        assert "$nope" in reply["text"]

    def test_bare_prefix(self, engine):
        [reply] = engine.handle("$")
        assert reply["type"] == "error"

    def test_fivecommand(self, engine):
        assert texts(engine.handle("$fivecommand ^p+^^^p+^^^p+^^^^^^^p")) == ["1337"]

    @pytest.mark.parametrize("name", ["help", "debugfivecommand"])
    def test_removed_commands_are_unknown(self, engine, name):
        [reply] = engine.handle("$" + name)
        assert reply["type"] == "error"
        assert reply["text"].startswith("Unknown command")


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
    @pytest.mark.parametrize("language, code", [(language, code) for language, meta in LANGUAGES.items()
                                                for _, code in meta["examples"]])
    def test_every_example_runs(self, engine, language, code):
        replies = engine.handle(code, language=language)
        assert replies
        assert all(r["type"] == "text" for r in replies)

    def test_brainfart_examples(self):
        assert [code for _, code in LANGUAGES["bf"]["examples"]][1:] == ["$hi", "$ping"]

    def test_hq9plus_example(self):
        assert [code for _, code in LANGUAGES["hq9plus"]["examples"]] == ["hq9+"]

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
        assert all({"id", "name", "examples", "info_url", "help"} <= l.keys() for l in listing)

    def test_languages_are_alphabetical(self, engine):
        names = [l["name"] for l in engine.languages()]
        assert names == sorted(names, key=str.lower)

    def test_unnecessary_says_what_succeeds(self, engine):
        unnecessary = next(l for l in engine.languages() if l["id"] == "unnecessary")
        assert "empty program" in unnecessary["intro"]
        assert any(f["name"] == "Successful call:" for f in unnecessary["help"]["fields"])

    @pytest.mark.parametrize("language, url", [
        ("bf", "https://esolangs.org/wiki/brainfuck"),
        ("kallisti", "https://bit.ly/2SdwN4b"),
        ("unnecessary", "https://esolangs.org/wiki/unnecessary"),
        ("hq9plus", "https://esolangs.org/wiki/HQ9%2B"),
        ("hatemath", "https://esolangs.org/wiki/Hatemath"),
        ("deadsimple", "https://esolangs.org/wiki/DeadSimple"),
        ("fivecommand", "https://esolangs.org/wiki/5command"),
    ])
    def test_info_url(self, language, url):
        assert info_url(language) == url


class TestHelp:
    def test_every_language_has_a_card(self, engine):
        assert set(HELP) == set(LANGUAGES)
        for language in engine.languages():
            assert language["help"]["type"] == "help"
            assert language["help"]["title"] == HELP[language["id"]]["title"]
            assert language["help"]["fields"]

    def test_cards_have_no_examples(self, engine):
        for language in engine.languages():
            assert not any(f["name"].startswith("Example") for f in language["help"]["fields"])
