import random
import string
from collections import defaultdict
from itertools import zip_longest

MAX_STEPS = 1_000_000
# Replies are cut off once together they pass this many characters.
MAX_OUTPUT = 64 * 1024
BF_TAPE_SIZE = 30000
BF_COMMANDS = frozenset("<>+-.,[]")
HQ9_MAX_MESSAGES = 10
KALLISTI_MAX_PASSES = 6
KALLISTI_MAX_AMOUNT = 6

class InterpreterError(Exception):
    pass


def _match_brackets(code):
    jumps = {}
    stack = []
    for i, ch in enumerate(code):
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if not stack:
                raise InterpreterError("unmatched ']' at position %d" % i)
            start = stack.pop()
            jumps[start] = i
            jumps[i] = start
    if stack:
        raise InterpreterError("unmatched '[' at position %d" % stack[-1])
    return jumps


def brainfart(code, max_steps=MAX_STEPS):
    jumps = _match_brackets(code)
    tape = [0] * BF_TAPE_SIZE
    p = 0
    out = []
    i = 0
    steps = 0
    while i < len(code) and len(out) <= MAX_OUTPUT:
        ch = code[i]
        if ch not in BF_COMMANDS:
            i += 1
            continue
        steps += 1
        if steps > max_steps:
            raise InterpreterError("program exceeded %d steps" % max_steps)
        if ch == ">":
            p += 1
            if p >= BF_TAPE_SIZE:
                raise InterpreterError("pointer moved past the end of the tape")
        elif ch == "<":
            p -= 1
            if p < 0:
                raise InterpreterError("pointer moved before the start of the tape")
        elif ch == "+":
            tape[p] = (tape[p] + 1) % 256
        elif ch == "-":
            tape[p] = (tape[p] - 1) % 256
        elif ch == ".":
            out.append(chr(tape[p]))
        elif ch == "[" and tape[p] == 0:
            i = jumps[i]
        elif ch == "]" and tape[p] != 0:
            i = jumps[i]
        i += 1
    return "".join(out)


def hatemath(code):
    x = ""
    out = []
    for ch in code:
        if ch == "[":
            x = None
        elif ch == "<":
            x = ""
        elif ch == ">":
            x = 0
        elif ch in "+-":
            if type(x) is not int:
                raise InterpreterError("%s needs x to be a number" % ch)
            x += 1 if ch == "+" else -1
        elif ch == "^":
            if type(x) is not str:
                raise InterpreterError("^ needs x to be a letter")
            if x == "z":
                raise InterpreterError("moved past 'z'")
            x = "a" if x == "" else chr(ord(x[0]) + 1)
        elif ch == "/":
            if type(x) is not str:
                raise InterpreterError("/ needs x to be a letter")
            if x == "a":
                raise InterpreterError("moved before 'a'")
            x = "z" if x == "" else chr(ord(x[0]) - 1)
        elif ch == "]":
            out.append(" " if x == "" else str(x))
    return "".join(out)


def deadsimple(code):
    x = ord("A")
    out = []
    for ch in code:
        if ch == "+":
            x += 1
            if ord("Z") < x < ord("a"):
                x = ord("a")
            elif x > ord("z"):
                raise InterpreterError("moved past 'z'")
        elif ch == "-":
            x -= 1
            if ord("Z") < x < ord("a"):
                x = ord("Z")
            elif x < ord("A"):
                raise InterpreterError("moved before 'A'")
        elif ch == "^":
            x = ord("A")
        elif ch == "%":
            x = ord("a")
        elif ch == "S":
            out.append(chr(x))
    return "".join(out)


def fivecommand(code):
    tape = defaultdict(int)
    p = 0
    out = []
    for ch in code:
        if ch == "+":
            p += 1
        elif ch == "-":
            p -= 1
        elif ch == "^":
            tape[p] += 1
        elif ch in "vV":
            tape[p] -= 1
        elif ch in "pP":
            out.append(str(tape[p]))
    return "".join(out)


def unnecessary(code):
    return "*" if code.strip() in ("", "#") else "Unsuccessful"


# ASCII letters only: str.swapcase() changes the length of some letters ("ß" -> "SS"), so it can't be undone.
SWAP_CASE = str.maketrans(string.ascii_lowercase + string.ascii_uppercase,
                          string.ascii_uppercase + string.ascii_lowercase)


def _shift(text, places):
    places %= 26
    lower, upper = string.ascii_lowercase, string.ascii_uppercase
    return text.translate(str.maketrans(lower + upper, lower[places:] + lower[:places] + upper[places:] + upper[:places]))


def _rotate(text, places):
    """Moves the first `places` characters to the end."""
    if not text:
        return text
    places %= len(text)
    return text[places:] + text[:places]


def _flip_blocks(text, size):
    """Reverses each run of `size` characters. Doing it twice puts the text back."""
    return "".join(text[i:i + size][::-1] for i in range(0, len(text), size))


def _riffle(text):
    """Interleaves the first half with the second, like a shuffled deck: abcde -> adbec."""
    half = (len(text) + 1) // 2
    return "".join(a + b for a, b in zip_longest(text[:half], text[half:], fillvalue=""))


def _unriffle(text):
    return text[0::2] + text[1::2]


# (scramble, unscramble, smallest amount). Every pass takes an amount; most ignore it.
KALLISTI_PASSES = (
    (lambda text, _: text[::-1], lambda text, _: text[::-1], 1),
    (lambda text, _: text.translate(SWAP_CASE), lambda text, _: text.translate(SWAP_CASE), 1),
    (_shift, lambda text, places: _shift(text, -places), 1),
    (_rotate, lambda text, places: _rotate(text, -places), 1),
    (_flip_blocks, _flip_blocks, 2),
    (lambda text, _: _riffle(text), lambda text, _: _unriffle(text), 1),
)


def kallisti(code, rng=random):
    """Scrambles the message with 1-6 passes picked at random, then undoes them in reverse order, so it comes back
    unchanged."""
    done = []
    for _ in range(rng.randint(1, KALLISTI_MAX_PASSES)):
        scramble, unscramble, smallest = rng.choice(KALLISTI_PASSES)
        amount = rng.randint(smallest, KALLISTI_MAX_AMOUNT)
        code = scramble(code, amount)
        done.append((unscramble, amount))
    for unscramble, amount in reversed(done):
        code = unscramble(code, amount)
    return code


def hq9plus(code, state):
    """`state` holds the shared accumulator and is mutated by '+'."""
    messages = []
    stopped = False
    for ch in code.lower():
        if ch not in "hq9+":
            continue
        if len(messages) >= HQ9_MAX_MESSAGES:
            stopped = True
            break
        if ch == "h":
            messages.append("Hello World! :)")
        elif ch == "q":
            messages.append(code)
        elif ch == "9":
            for bottles in (99, 98):
                messages.append("%s bottles of beer on the wall! %s bottles of beer!" % (bottles, bottles))
                messages.append("Take one down, and pass it around, %s bottles of beer on the wall!" % (bottles - 1))
            messages.append("....and So On")
        elif ch == "+":  # pragma: no branch - the loop already skipped everything but h, q, 9 and +
            state["accumulator"] = state.get("accumulator", 0) + 1
            messages.append("Accumulator is now at %s" % state["accumulator"])
    if stopped or len(messages) > HQ9_MAX_MESSAGES:
        del messages[HQ9_MAX_MESSAGES:]
        messages.append("Please do not make such big programs. No one likes spam.")
    return messages
