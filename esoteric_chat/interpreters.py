import string
from collections import defaultdict

MAX_STEPS = 1_000_000
BF_TAPE_SIZE = 30000
HQ9_MAX_MESSAGES = 10
KALLISTI_SHIFT = 5

PING_BF = '++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++++++++++.>+++++++++++.-.-------.<<+++.'
HELLO_BF = '++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.'


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
    while i < len(code):
        steps += 1
        if steps > max_steps:
            raise InterpreterError("program exceeded %d steps" % max_steps)
        ch = code[i]
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
        elif ch == "+":
            x += 1
        elif ch == "-":
            x -= 1
        elif ch == "^":
            if x == "z":
                raise InterpreterError("moved past 'z'")
            x = "a" if x == "" else chr(ord(x[0]) + 1)
        elif ch == "/":
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


def kallisti(code):
    """Reverses, swaps case and shifts the letters, then undoes all three, so the message comes back unchanged."""
    scrambled = _shift(code[::-1].translate(SWAP_CASE), KALLISTI_SHIFT)
    return _shift(scrambled, -KALLISTI_SHIFT).translate(SWAP_CASE)[::-1]


def hq9plus(code, state):
    """Returns a list of messages. `state` holds the shared accumulator and is mutated by '+'."""
    messages = []
    commands_run = 0
    for ch in code.lower():
        if ch not in "hq9+":
            continue
        if commands_run >= HQ9_MAX_MESSAGES:
            messages.append("Please do not make such big programs. No one likes spam.")
            break
        commands_run += 1
        if ch == "h":
            messages.append("Hello World! :)")
        elif ch == "q":
            messages.append(code)
        elif ch == "9":
            for bottles in (99, 98):
                messages.append("%s bottles of beer on the wall! %s bottles of beer!" % (bottles, bottles))
                messages.append("Take one down, and pass it around, %s bottles of beer on the wall!" % (bottles - 1))
            messages.append("....and So On")
        elif ch == "+":
            state["accumulator"] = state.get("accumulator", 0) + 1
            messages.append("Accumulator is now at %s" % state["accumulator"])
    return messages
