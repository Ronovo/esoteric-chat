import threading

from . import interpreters as interp

MAX_OUTPUT = interp.MAX_OUTPUT
OUTPUT_CUT_NOTE = f"\n... (output cut off at {MAX_OUTPUT:,} characters)"
KALLISTI_LABEL = "Scrambled:\n"


def text(value):
    return {"type": "text", "text": value}


def error(value):
    return {"type": "error", "text": value}


def help_card(language):
    meta = LANGUAGES[language]
    return {"title": meta["name"], "color": meta["color"], "about": meta.get("about"),
            "fields": [{"name": n, "value": v} for n, v in meta["fields"]]}


def info_url(language):
    return next(v for _, v in LANGUAGES[language]["fields"] if "esolangs.org" in v)


def cap_output(messages):
    """Cuts the replies off once together they pass MAX_OUTPUT characters."""
    capped, left = [], MAX_OUTPUT
    for message in messages:
        if len(message) > left:
            capped.append(message[:left] + OUTPUT_CUT_NOTE)
            break
        capped.append(message)
        left -= len(message)
    return capped


def run_kallisti(code):
    """The labeled scrambled message, then the exact echo. Only the scrambled reply is shortened to keep both under
    MAX_OUTPUT, and it is left out when there isn't room for its label and the cut-off note."""
    scrambled, echo = interp.kallisti(code)
    shown = KALLISTI_LABEL + scrambled
    room = MAX_OUTPUT - len(echo)
    if len(shown) > room:
        if room < len(KALLISTI_LABEL) + len(OUTPUT_CUT_NOTE):
            return [echo]
        shown = shown[:room - len(OUTPUT_CUT_NOTE)] + OUTPUT_CUT_NOTE
    return [shown, echo]


# Listed in the order the language picker shows them: alphabetical by name. `run` takes the code and returns the
# reply text or a list of replies; HQ9+ has no `run` because the engine runs it against the shared accumulator.
LANGUAGES = {
    "fivecommand": {
        "name": "5command",
        "color": "purple",
        "run": interp.fivecommand,
        "intro": "5command - Five symbols run a tape of numbers: + and - move along it, ^ and v change the current "
                 "number, and p prints it.",
        "examples": [("Print 1337", "^p+^^^p+^^^p+^^^^^^^p")],
        "about": "There are only 5 symbols allowed.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/5command"),
            ("+", "Move pointer right on the tape"),
            ("-", "Move pointer left on the tape"),
            ("^", "Increments current cell at pointer"),
            ("v", "Decrements current cell at pointer"),
            ("P", "Prints current cell at pointer"),
        ],
    },
    "bf": {
        "name": "Brainfart",
        "color": "red",
        "run": interp.brainfart,
        "intro": "Brainfart - The Safe-For-Work alternative to BrainF**K",
        "examples": [
            ("Print Hello World!", "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+."),
        ],
        "about": "There are only 8 symbols allowed. All other characters are ignored.",
        "fields": [
            ("More Information:", "https://esolangs.org/wiki/brainfuck"),
            ("English-to-Brainfart Converter:", "https://www.dcode.fr/brainfuck-language"),
            (">", "Move to Next Element"),
            ("<", "Move to Previous Element"),
            ("+", "Increment Current Element"),
            ("-", "Decrement Current Element"),
            (",", "Await Input (Not Implemented)"),
            (".", "Output Current Element (in ASCII)"),
            ("[", "Jump past matching ] if Element is 0"),
            ("]", "Jump back to matching [ if Element is not 0"),
        ],
    },
    "deadsimple": {
        "name": "DeadSimple",
        "color": "dark_blue",
        "run": interp.deadsimple,
        "intro": "DeadSimple - One number that starts at 0: + and - change it, _ resets it to 0, and S prints it as a "
                 "character (32 is a space, 65 is A).",
        "examples": [("Print hello world", "+" * 104 + "S---S+++++++SS+++S_" + "+" * 32 + "S" + "+" * 87
                      + "S--------S+++S------S--------S")],
        "about": "There are only 4 symbols allowed. Starts at 0.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/DeadSimple"),
            ("_", "Reset to 0"),
            ("+", "Increment by 1"),
            ("-", "Decrement by 1"),
            ("S", "Print the value as a character (Unicode)"),
        ],
    },
    "hatemath": {
        "name": "Hatemath",
        "color": "red",
        "run": interp.hatemath,
        "intro": "Hatemath - One variable, x, that is nothing, a letter or a number. Change its type, nudge its value "
                 "and print it with ].",
        "examples": [("Print hello world", "<" + "^" * 8 + "]///]" + "^" * 7 + "]]^^^]<]" + "^" * 23
                      + "]////////]^^^]//////]////////]")],
        "about": "There are only 8 symbols, working on 1 variable named x.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/Hatemath"),
            ("[", "Sets type of X to None"),
            ("<", "Sets type of X to ''"),
            (">", "Sets type of X to 0"),
            ("+", "Increment if it is an integer"),
            ("-", "Decrement if it is an integer"),
            ("^", "Move up the alphabet (lowercase only)"),
            ("/", "Move down the alphabet (lowercase only)"),
            ("]", "Print Value"),
        ],
    },
    "hq9plus": {
        "name": "HQ9+",
        "color": "orange",
        "intro": "HQ9+ - H says hello, Q prints your program, 9 sings 99 Bottles of Beer, and + bumps a counter shared "
                 "by everyone.",
        "examples": [("Run all four: Hello World, quine, 99 Bottles, add 1", "hq9+")],
        "about": "There are only 4 symbols allowed.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/HQ9%2B"),
            ("h", "Prints Hello World"),
            ("q", "Prints Source Code (Quine)"),
            ("9", "Starts 99 Bottles of Beer on the wall"),
            ("+", "Increments a counter shared by everyone using this chat"),
        ],
    },
    "kallisti": {
        "name": "Kallisti",
        "color": "blue",
        "run": run_kallisti,
        "intro": "Kallisti - Everything you send comes back scrambled first, then repeated back exactly.",
        "examples": [("Repeat Rule 3: Everything is true", "Everything is true")],
        "about": "<anything> ::= <anything>",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/Kallisti"),
            ("Rule 1:", "Obey as many rules as possible"),
            ("Rule 2:", "There is plenty nothing"),
            ("Rule 3:", "Everything is true"),
            ("Rule 4:", "Everything is false"),
            ("Rule 5:", "There is only nothing"),
            ("Rule 6:", "Obey as few rules as possible"),
        ],
    },
    "unnecessary": {
        "name": "Unnecessary",
        "color": "blue",
        "run": interp.unnecessary,
        "intro": "Unnecessary - A successful call is an empty program (or just #), which prints *. "
                 "Anything else prints Unsuccessful.",
        "examples": [("Successful call: prints *", "#")],
        "fields": [
            ("Official Site:", "http://yiap.nfshost.com/esoteric/unnecessary/unnecessary.html"),
            ("Esolangs.org Link:", "https://esolangs.org/wiki/unnecessary"),
            ("Rule 1:", "If a program file exists, report error and fail"),
            ("Rule 2:", "If no program file exists, create program with NOP (No Operation) instruction"),
            ("Successful call:", "An empty program, or just #, prints *. Anything else prints Unsuccessful"),
        ],
    },
}


def language_listing():
    return [{"id": key, "name": meta["name"], "intro": meta.get("intro"),
             "examples": [{"label": label, "code": code} for label, code in meta["examples"]],
             "info_url": info_url(key), "help": help_card(key)} for key, meta in LANGUAGES.items()]


class ChatEngine:
    def __init__(self):
        self.hq9_state = {"accumulator": 0}
        self._hq9_lock = threading.Lock()

    def handle(self, message, language=None):
        if not language:
            return [error("Pick a language.")]
        return self.run_language(language, message)

    def run_language(self, language, code):
        meta = LANGUAGES.get(language)
        if meta is None:
            return [error("Unknown language: %s" % language)]
        try:
            replies = meta["run"](code) if "run" in meta else self.run_hq9plus(code)
            if isinstance(replies, str):
                replies = [replies]
            return [text(m) for m in cap_output(replies)]
        except interp.InterpreterError as e:
            return [error("Invalid %s Command: %s" % (meta["name"], e))]

    def run_hq9plus(self, code):
        with self._hq9_lock:
            return interp.hq9plus(code, self.hq9_state)
