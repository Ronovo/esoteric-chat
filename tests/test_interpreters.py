import random
import string

import pytest

from esoteric_chat import interpreters as interp
from esoteric_chat.commands import HELLO_BF, PING_BF
from esoteric_chat.interpreters import InterpreterError

HELLO_WORLD_BF = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."


class TestBrainfart:
    def test_ping_and_hello_command_programs(self):
        assert interp.brainfart(PING_BF) == "Pong!"
        assert interp.brainfart(HELLO_BF) == "Hello"

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

    def test_pointer_past_the_end_of_the_tape(self):
        with pytest.raises(InterpreterError, match="past the end"):
            interp.brainfart(">" * interp.BF_TAPE_SIZE)

    def test_comments_are_not_counted_as_steps(self):
        assert interp.brainfart("x" * 2000 + "+.", max_steps=2) == "\x01"

    def test_output_stops_just_past_the_limit(self):
        output = interp.brainfart("+[.]", max_steps=10 * interp.MAX_OUTPUT)
        assert len(output) == interp.MAX_OUTPUT + 1

    def test_infinite_loop_hits_step_limit(self):
        with pytest.raises(InterpreterError, match="exceeded"):
            interp.brainfart("+[]", max_steps=1000)


class TestHatemath:
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
        with pytest.raises(InterpreterError, match="needs x to be a number"):
            interp.hatemath("<^+")

    @pytest.mark.parametrize("code", [">^", "[^", ">/", "[/"])
    def test_letter_moves_need_a_letter(self, code):
        with pytest.raises(InterpreterError, match="needs x to be a letter"):
            interp.hatemath(code)

    def test_other_characters_are_ignored(self):
        assert interp.hatemath("> +x+ ]") == "2"


class TestDeadSimple:
    def test_steps_back_within_a_case(self):
        assert interp.deadsimple("++-S %++-S") == "Bb"

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
    def test_uppercase_aliases(self):
        assert interp.fivecommand("^^VP") == "1"

    def test_negative_pointer(self):
        assert interp.fivecommand("-^P+P") == "10"

    def test_other_characters_are_ignored(self):
        assert interp.fivecommand("^ ^x p") == "2"


class TestUnnecessary:
    @pytest.mark.parametrize("code", ["", "   "])
    def test_no_program_succeeds(self, code):
        assert interp.unnecessary(code) == "*"


class TestKallisti:
    def test_echoes(self):
        assert interp.kallisti("Everything is true") == "Everything is true"

    @pytest.mark.parametrize("code", [
        "", "  spaced  out  ", "line one\nline two", "$ping", "Zebra zz ZZ", "Café ß İ naïve", "1234 !?#",
    ])
    def test_round_trip_is_exact(self, code):
        for seed in range(20):
            assert interp.kallisti(code, random.Random(seed)) == code

    def test_shift_really_changes_letters(self):
        assert interp._shift("abz ABZ 9!", 5) == "fge FGE 9!"
        assert interp._shift("fge FGE", -5) == "abz ABZ"

    def test_swap_case_really_changes_letters(self):
        assert "aBc ß".translate(interp.SWAP_CASE) == "AbC ß"

    def test_rotate_flip_and_riffle_move_characters(self):
        assert interp._rotate("ab12", 1) == "b12a"
        assert interp._flip_blocks("abc123", 3) == "cba321"
        assert interp._riffle("abc12") == "a1b2c"

    @pytest.mark.parametrize("text", ["", "a", "ab", "Hello, World! 42", "line one\nline two", "Café ß 9"])
    @pytest.mark.parametrize("amount", range(1, interp.KALLISTI_MAX_AMOUNT + 1))
    def test_every_pass_undoes_itself(self, text, amount):
        for scramble, unscramble, smallest in interp.KALLISTI_PASSES:
            used = max(amount, smallest)
            assert unscramble(scramble(text, used), used) == text

    def test_random_messages_come_back_unchanged(self):
        rng = random.Random(7)
        alphabet = string.ascii_letters + string.digits + string.punctuation + " \n\téß"
        for _ in range(500):
            code = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
            assert interp.kallisti(code, rng) == code
        assert interp.kallisti("$ping", rng) == "$ping"


class TestHq9Plus:
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

    def test_limit_counts_replies_not_commands(self):
        messages = interp.hq9plus("999", {})
        assert len(messages) == interp.HQ9_MAX_MESSAGES + 1
        assert messages[-1] == "Please do not make such big programs. No one likes spam."

    def test_exactly_at_limit_has_no_warning(self):
        messages = interp.hq9plus("h" * interp.HQ9_MAX_MESSAGES, {})
        assert len(messages) == interp.HQ9_MAX_MESSAGES

    def test_other_characters_ignored(self):
        assert interp.hq9plus("xyz", {}) == []
