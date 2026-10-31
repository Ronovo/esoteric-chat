import pytest

from esoteric_chat.commands import (
    HELLO_BF,
    LANGUAGES,
    MAX_OUTPUT,
    OUTPUT_CUT_NOTE,
    PING_BF,
    ChatEngine,
    cap_output,
    info_url,
    language_listing,
)


# What each example's label says it prints.
PRINTS = {"Print 1337": "1337", "Print Hello World!": "Hello World!", "Print AbC": "AbC", "Print hi": "hi",
          "Repeat Rule 3: Everything is true": "Everything is true", "Successful call: prints *": "*"}


@pytest.fixture
def engine():
    return ChatEngine()


def texts(replies):
    return [r["text"] for r in replies]


class TestCommands:
    def test_ping(self, engine):
        assert texts(engine.handle("$ping")) == [PING_BF]

    @pytest.mark.parametrize("name", ["hello", "hi"])
    def test_hello(self, engine, name):
        assert texts(engine.handle("$" + name)) == [HELLO_BF]

    def test_command_ignores_selected_language(self, engine):
        assert texts(engine.handle("$deadsimple S%S", language="bf")) == ["Aa"]

    def test_command_name_case_insensitive(self, engine):
        assert texts(engine.handle("$PING")) == [PING_BF]

    def test_multiline_command_argument(self, engine):
        assert texts(engine.handle("$kallisti line one\nline two")) == ["line one\nline two"]

    def test_command_keeps_argument_exactly(self, engine):
        assert texts(engine.handle("$kallisti   two  spaces  ")) == ["  two  spaces  "]

    def test_leading_spaces_before_a_command(self, engine):
        assert texts(engine.handle("   $ping")) == [PING_BF]

    def test_a_tab_separates_the_command_from_its_argument(self, engine):
        assert texts(engine.handle("$kallisti\t two")) == [" two"]

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



class TestErrors:
    def test_interpreter_error_includes_reason(self, engine):
        [reply] = engine.handle("$bf [")
        assert reply["type"] == "error"
        assert reply["text"].startswith("Invalid Brainfart Command: unmatched")

    def test_type_errors_explain_themselves(self, engine):
        assert engine.handle("$hatemath <+") == [
            {"type": "error", "text": "Invalid Hatemath Command: + needs x to be a number"}]

    def test_long_output_is_cut_off(self, engine):
        # Prints 16 * 16 * 16 * 20 = 81,920 characters.
        program = "+" * 16 + "[>" + "+" * 16 + "[>" + "+" * 16 + "[>" + "+" * 20 + "[>.<-]<-]<-]<-]"
        [reply] = engine.handle("$bf " + program)
        assert reply["text"].endswith(OUTPUT_CUT_NOTE)
        assert len(reply["text"]) < MAX_OUTPUT + 50

    def test_cap_counts_every_reply(self):
        assert cap_output(["a" * MAX_OUTPUT, "b"]) == ["a" * MAX_OUTPUT, OUTPUT_CUT_NOTE]

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

    @pytest.mark.parametrize("language, label, code", [(language, label, code) for language, meta in LANGUAGES.items()
                                                       for label, code in meta["examples"] if label in PRINTS])
    def test_examples_print_what_their_labels_say(self, engine, language, label, code):
        assert texts(engine.handle(code, language=language)) == [PRINTS[label]]

    def test_the_hq9plus_example_runs_all_four_commands(self, engine):
        [(_, code)] = LANGUAGES["hq9plus"]["examples"]
        replies = texts(engine.handle(code, language="hq9plus"))
        assert replies[:2] == ["Hello World! :)", code]
        assert replies[2].startswith("99 bottles")
        assert replies[-1] == "Accumulator is now at 1"

    def test_every_example_has_its_output_checked(self):
        labels = {label for meta in LANGUAGES.values() for label, _ in meta["examples"]}
        commands = {label for label in labels if label.startswith("$")}
        assert labels - commands - set(PRINTS) == {LANGUAGES["hq9plus"]["examples"][0][0]}

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

    def test_languages_are_alphabetical(self):
        names = [l["name"] for l in language_listing()]
        assert names == sorted(names, key=str.lower)

    def test_every_language_links_to_esolangs(self):
        assert info_url("unnecessary") == "https://esolangs.org/wiki/unnecessary"
        assert all("esolangs.org" in l["info_url"] for l in language_listing())


class TestHelp:
    def test_every_language_has_a_card(self):
        for language in language_listing():
            assert language["help"]["title"] == language["name"]
            assert language["help"]["fields"]
