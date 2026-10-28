import pytest

from esoteric_chat import interpreters as interp
from esoteric_chat.interpreters import InterpreterError

HELLO_WORLD_BF = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."


class TestBrainfart:
    def test_ping_and_hello_command_programs(self):
        assert interp.brainfart(interp.PING_BF) == "Pong!"
        assert interp.brainfart(interp.HELLO_BF) == "Hello"

    def test_nested_loops(self):
        assert interp.brainfart(HELLO_WORLD_BF) == "Hello World!\n"

    def test_loop_skipped_when_cell_is_zero(self):
        assert interp.brainfart("[.]++++++++[>++++++++<-]>+.") == "A"

    def test_long_running_loop(self):
        assert interp.brainfart("+" * 200 + "[-]" + "+" * 66 + ".") == "B"

    def test_cells_wrap(self):
        assert interp.brainfart("-" + "-" * 190 + ".") == "A"
        assert interp.brainfart("+" * 256 + "+" * 65 + ".") == "A"

    def test_non_commands_ignored(self):
        assert interp.brainfart("hello ++++++++[>++++++++<-]>+. world") == "A"

    def test_input_is_ignored(self):
        assert interp.brainfart(",") == ""

    def test_empty_program(self):
        assert interp.brainfart("") == ""

    @pytest.mark.parametrize("code", ["[", "]", "[[]", "[]]"])
    def test_unmatched_brackets(self, code):
        with pytest.raises(InterpreterError, match="unmatched"):
            interp.brainfart(code)

    def test_pointer_before_tape(self):
        with pytest.raises(InterpreterError, match="before the start"):
            interp.brainfart("<")

    def test_infinite_loop_hits_step_limit(self):
        with pytest.raises(InterpreterError, match="exceeded"):
            interp.brainfart("+[]", max_steps=1000)


class TestHatemath:
    def test_letters(self):
        assert interp.hatemath("<^^^^^^^^]^]") == "hi"

    def test_down_alphabet(self):
        assert interp.hatemath("</]/]") == "zy"

    def test_past_z_fails(self):
        with pytest.raises(interp.InterpreterError):
            interp.hatemath("<" + "^" * 27)

    def test_before_a_fails(self):
        with pytest.raises(interp.InterpreterError):
            interp.hatemath("<^/")

    def test_integers(self):
        assert interp.hatemath(">+++]--]") == "31"

    def test_empty_string_prints_space(self):
        assert interp.hatemath("<]") == " "

    def test_none(self):
        assert interp.hatemath("[]") == "None"

    def test_default_is_empty_string(self):
        assert interp.hatemath("]^]") == " a"

    def test_increment_on_string_fails(self):
        with pytest.raises(TypeError):
            interp.hatemath("<^+")


class TestDeadSimple:
    def test_help_example(self):
        assert interp.deadsimple("S%+S^++S") == "AbC"

    def test_uppercase_rolls_into_lowercase(self):
        assert interp.deadsimple("+" * 25 + "S+S") == "Za"

    def test_lowercase_rolls_back_to_uppercase(self):
        assert interp.deadsimple("%-S") == "Z"

    def test_past_z_fails(self):
        with pytest.raises(InterpreterError):
            interp.deadsimple("%" + "+" * 26)

    def test_before_a_fails(self):
        with pytest.raises(InterpreterError):
            interp.deadsimple("-")


class TestFiveCommand:
    def test_help_example(self):
        assert interp.fivecommand("^p+^^^p+^^^p+^^^^^^^p") == "1337"

    def test_uppercase_aliases(self):
        assert interp.fivecommand("^^VP") == "1"

    def test_negative_pointer(self):
        assert interp.fivecommand("-^P+P") == "10"


class TestUnnecessary:
    @pytest.mark.parametrize("code", ["", "   ", "#"])
    def test_no_program_succeeds(self, code):
        assert interp.unnecessary(code) == "*"

    def test_program_fails(self):
        assert interp.unnecessary("anything") == "Unsuccessful"


class TestKallisti:
    def test_echoes(self):
        assert interp.kallisti("Everything is true") == "Everything is true"

    @pytest.mark.parametrize("code", [
        "", "  spaced  out  ", "line one\nline two", "$ping", "Zebra zz ZZ", "Café ß İ naïve", "1234 !?#",
    ])
    def test_round_trip_is_exact(self, code):
        assert interp.kallisti(code) == code

    def test_shift_really_changes_letters(self):
        assert interp._shift("abz ABZ 9!", 5) == "fge FGE 9!"
        assert interp._shift("fge FGE", -5) == "abz ABZ"

    def test_swap_case_really_changes_letters(self):
        assert "aBc ß".translate(interp.SWAP_CASE) == "AbC ß"


class TestHq9Plus:
    def test_help_example(self):
        assert interp.hq9plus("qhq", {}) == ["qhq", "Hello World! :)", "qhq"]

    def test_case_insensitive(self):
        assert interp.hq9plus("H", {}) == ["Hello World! :)"]

    def test_bottles(self):
        messages = interp.hq9plus("9", {})
        assert messages[0] == "99 bottles of beer on the wall! 99 bottles of beer!"
        assert messages[-1] == "....and So On"
        assert len(messages) == 5

    def test_accumulator_persists_in_state(self):
        state = {"accumulator": 0}
        assert interp.hq9plus("++", state) == ["Accumulator is now at 1", "Accumulator is now at 2"]
        assert interp.hq9plus("+", state) == ["Accumulator is now at 3"]
        assert state["accumulator"] == 3

    def test_spam_limit(self):
        messages = interp.hq9plus("h" * 15, {})
        assert messages.count("Hello World! :)") == interp.HQ9_MAX_MESSAGES
        assert messages[-1] == "Please do not make such big programs. No one likes spam."

    def test_exactly_at_limit_has_no_warning(self):
        messages = interp.hq9plus("h" * interp.HQ9_MAX_MESSAGES, {})
        assert len(messages) == interp.HQ9_MAX_MESSAGES

    def test_other_characters_ignored(self):
        assert interp.hq9plus("xyz", {}) == []
