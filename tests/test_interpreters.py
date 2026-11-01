import random
import string
from unittest import mock

import pytest

from esoteric_chat import interpreters as interp
from esoteric_chat.interpreters import InterpreterError

HELLO_WORLD_BF = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."


class TestBrainfart:
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
    def test_starts_at_zero(self):
        assert interp.deadsimple("S") == "\x00"

    def test_prints_the_value_as_a_character(self):
        assert interp.deadsimple("+" * 72 + "S" + "+" * 33 + "S") == "Hi"
        assert interp.deadsimple("+" * 32 + "S") == " "

    def test_steps_down(self):
        assert interp.deadsimple("+" * 66 + "-S") == "A"

    def test_underscore_resets_to_zero(self):
        assert interp.deadsimple("+" * 100 + "_" + "+" * 65 + "S") == "A"

    def test_lowercase_s_and_other_characters_are_comments(self):
        assert interp.deadsimple("+" * 65 + "s # A\nS") == "A"

    def test_can_go_below_zero_and_back(self):
        assert interp.deadsimple("--" + "+" * 67 + "S") == "A"

    def test_printing_a_negative_value_fails(self):
        with pytest.raises(InterpreterError):
            interp.deadsimple("-S")

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
        assert interp.kallisti("Everything is true")[1] == "Everything is true"

    @pytest.mark.parametrize("code", [
        "", "  spaced  out  ", "line one\nline two", "$ping", "Zebra zz ZZ", "Café ß İ naïve", "1234 !?#",
    ])
    def test_round_trip_is_exact(self, code):
        for seed in range(20):
            assert interp.kallisti(code, random.Random(seed))[1] == code

    def test_shift_really_changes_letters(self):
        assert interp._shift("abz ABZ 9!", 5) == "fge FGE 9!"
        assert interp._shift("fge FGE", -5) == "abz ABZ"

    def test_swap_case_really_changes_letters(self):
        assert "aBc ß".translate(interp.SWAP_CASE) == "AbC ß"

    def test_rotate_flip_and_riffle_move_characters(self):
        assert interp._rotate("ab12", 1) == "b12a"
        assert interp._flip_blocks("abc123", 3) == "cba321"
        assert interp._undeal("abc12", 2) == "a1b2c"

    def test_mirror_alphabet_and_leetspeak_change_letters(self):
        assert "Hello AZ 9".translate(interp.ATBASH) == "Svool ZA 9"
        assert "toast 4 me".translate(interp.LEETSPEAK) == "70457 a m3"
        assert "TOAST".translate(interp.LEETSPEAK) == "TOAST"

    def test_reverse_words_keeps_the_whitespace_in_place(self):
        assert interp._reverse_words(" Hello  big\nworld ") == " olleH  gib\ndlrow "

    def test_wave_case_swaps_every_nth_character(self):
        assert interp._wave_case("everything", 2) == "EvErYtHiNg"
        assert interp._wave_case("abcdefg", 3) == "AbcDefG"

    def test_deal_stacks_the_piles(self):
        assert interp._deal("abcdefgh", 3) == "adgbehcf"
        assert interp._undeal("adgbehcf", 3) == "abcdefgh"

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
            assert interp.kallisti(code, rng)[1] == code
        assert interp.kallisti("$ping", rng)[1] == "$ping"

    def test_returns_the_message_as_it_was_after_every_pass(self):
        rng = mock.Mock()
        rng.randint.side_effect = [2, 1, 3]
        rng.choice.side_effect = [interp.KALLISTI_PASSES[0], interp.KALLISTI_PASSES[2]]
        assert interp.kallisti("Abc", rng) == ("feD", "Abc")


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

    def test_long_programs_get_every_reply(self):
        assert interp.hq9plus("h" * 15, {}) == ["Hello World! :)"] * 15
        assert len(interp.hq9plus("999", {})) == 15

    def test_other_characters_ignored(self):
        assert interp.hq9plus("xyz", {}) == []
