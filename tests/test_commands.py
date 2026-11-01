import pytest

from esoteric_chat import interpreters as interp
from esoteric_chat.commands import (
    KALLISTI_LABEL,
    LANGUAGES,
    MAX_OUTPUT,
    OUTPUT_CUT_NOTE,
    ChatEngine,
    cap_output,
    info_url,
    language_listing,
)


# What each example's label says it prints.
PRINTS = {"Print 1337": "1337", "Print Hello World!": "Hello World!", "Print hello world": "hello world",
          "Repeat Rule 3: Everything is true": "Everything is true", "Successful call: prints *": "*"}


@pytest.fixture
def engine():
    return ChatEngine()


def texts(replies):
    return [r["text"] for r in replies]


def without_scrambled(replies):
    """The replies without Kallisti's scrambled copy, which changes on every run."""
    return [r for r in replies if not r.startswith(KALLISTI_LABEL)]


@pytest.fixture
def reversing(monkeypatch):
    """Kallisti with one known scramble: the message reversed."""
    monkeypatch.setattr(interp, "kallisti", lambda code: (code[::-1], code))


class TestMessages:
    @pytest.mark.parametrize("message", ["$unnecessary", "   $unnecessary", "$ping", "$"])
    def test_dollar_messages_run_in_the_selected_language(self, engine, message):
        assert texts(engine.handle(message, language="unnecessary")) == ["Unsuccessful"]

    def test_kallisti_repeats_dollar_messages(self, engine, reversing):
        assert texts(engine.handle("$unnecessary", language="kallisti")) == ["Scrambled:\nyrassecennu$", "$unnecessary"]

    def test_kallisti_keeps_the_message_exactly(self, engine):
        message = "  line one\n\tline two  "
        assert without_scrambled(texts(engine.handle(message, language="kallisti"))) == [message]

    def test_kallisti_shows_the_scrambled_message_before_the_echo(self, engine, reversing):
        assert texts(engine.handle("abc", language="kallisti")) == ["Scrambled:\ncba", "abc"]

    def test_kallisti_cuts_only_the_scrambled_copy_to_fit(self, engine, reversing):
        message = "a" * 40_000 + "z"
        scrambled, echo = texts(engine.handle(message, language="kallisti"))
        assert echo == message
        assert scrambled.startswith(KALLISTI_LABEL + "z") and scrambled.endswith(OUTPUT_CUT_NOTE)
        assert len(scrambled) + len(echo) == MAX_OUTPUT

    def test_kallisti_leaves_the_scrambled_copy_out_without_room_for_the_note(self, engine, reversing):
        fits = "a" * (MAX_OUTPUT - len(KALLISTI_LABEL) - len(OUTPUT_CUT_NOTE))
        assert len(texts(engine.handle(fits, language="kallisti"))) == 2
        message = fits + "a"
        assert texts(engine.handle(message, language="kallisti")) == [message]


class TestErrors:
    def test_interpreter_error_includes_reason(self, engine):
        [reply] = engine.handle("[", language="bf")
        assert reply["type"] == "error"
        assert reply["text"].startswith("Invalid Brainfart Command: unmatched")

    def test_type_errors_explain_themselves(self, engine):
        assert engine.handle("<+", language="hatemath") == [
            {"type": "error", "text": "Invalid Hatemath Command: + needs x to be a number"}]

    def test_long_output_is_cut_off(self, engine):
        # Prints 16 * 16 * 16 * 20 = 81,920 characters.
        program = "+" * 16 + "[>" + "+" * 16 + "[>" + "+" * 16 + "[>" + "+" * 20 + "[>.<-]<-]<-]<-]"
        [reply] = engine.handle(program, language="bf")
        assert reply["text"].endswith(OUTPUT_CUT_NOTE)
        assert len(reply["text"]) < MAX_OUTPUT + 50

    def test_cap_counts_every_reply(self):
        assert cap_output(["a" * MAX_OUTPUT, "b"]) == ["a" * MAX_OUTPUT, OUTPUT_CUT_NOTE]

    def test_deadsimple_error(self, engine):
        [reply] = engine.handle("-S", language="deadsimple")
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
        assert without_scrambled(texts(engine.handle(code, language=language))) == [PRINTS[label]]

    def test_the_hq9plus_example_runs_all_four_commands(self, engine):
        [(_, code)] = LANGUAGES["hq9plus"]["examples"]
        replies = texts(engine.handle(code, language="hq9plus"))
        assert replies[:2] == ["Hello World! :)", code]
        assert replies[2].startswith("99 bottles")
        assert replies[-1] == "Accumulator is now at 1"

    @pytest.mark.parametrize("language", LANGUAGES)
    def test_every_language_has_an_intro_starting_with_its_name(self, language):
        assert language_listing()[list(LANGUAGES).index(language)]["intro"].startswith(LANGUAGES[language]["name"] + " - ")

    def test_every_example_has_its_output_checked(self):
        labels = {label for meta in LANGUAGES.values() for label, _ in meta["examples"]}
        assert labels - set(PRINTS) == {LANGUAGES["hq9plus"]["examples"][0][0]}

    @pytest.mark.parametrize("language, code, expected", [
        ("bf", "++++++++[>++++++++<-]>+.", ["A"]),
        ("kallisti", "  spaced out  ", ["  spaced out  "]),
        ("unnecessary", "#", ["*"]),
        ("unnecessary", "print", ["Unsuccessful"]),
        ("hq9plus", "qhq", ["qhq", "Hello World! :)", "qhq"]),
        ("hatemath", "<^^^^^^^^]^]", ["hi"]),
        ("deadsimple", "+" * 72 + "S" + "+" * 33 + "S", ["Hi"]),
        ("fivecommand", "^p+^^^p+^^^p+^^^^^^^p", ["1337"]),
    ])
    def test_runs_selected_language(self, engine, language, code, expected):
        assert without_scrambled(texts(engine.handle(code, language=language))) == expected

    @pytest.mark.parametrize("message", ["+++.", "$unnecessary"])
    def test_no_language_selected(self, engine, message):
        assert engine.handle(message) == [{"type": "error", "text": "Pick a language."}]

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
