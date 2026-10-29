import re
import threading

from . import interpreters as interp

PREFIX = "$"
# "$name", then everything after one separating space or newline, exactly as typed.
COMMAND_RE = re.compile(r"\$(\S*)\s?(.*)", re.S)
ECHO_LANGUAGE = "kallisti"
MAX_OUTPUT = 64 * 1024
OUTPUT_CUT_NOTE = "\n... (output cut off at 64 KB)"

PING_BF = '++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++++++++++.>+++++++++++.-.-------.<<+++.'
HELLO_BF = '++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.'


def text(value):
    return {"type": "text", "text": value}


def error(value):
    return {"type": "error", "text": value}


def help_card(language):
    meta = LANGUAGES[language]
    return {"type": "help", "title": meta["name"], "color": meta["color"], "about": meta.get("about"),
            "fields": [{"name": n, "value": v} for n, v in meta["fields"]]}


def info_url(language):
    urls = [v for _, v in LANGUAGES[language]["fields"] if v.startswith("http")]
    return next((u for u in urls if "esolangs.org" in u), urls[0])


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


# Listed in the order the language picker shows them: alphabetical by name. `run` takes the engine and the code and
# returns the reply texts.
LANGUAGES = {
    "fivecommand": {
        "name": "5command",
        "color": "purple",
        "run": lambda engine, code: [interp.fivecommand(code)],
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
        "run": lambda engine, code: [interp.brainfart(code)],
        "intro": "Brainfart - The Safe-For-Work alternative to BrainF**K",
        "examples": [
            ("Print Hello World!", "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+."),
            ("$hi: get a program that prints Hello", "$hi"),
            ("$ping: get a program that prints Pong!", "$ping"),
        ],
        "about": "There are only 8 symbols allowed. All other characters are ignored.",
        "fields": [
            ("More Information:", "https://esolangs.org/wiki/brainfuck"),
            ("English-to-Brainfart Converter:", "https://www.dcode.fr/brainfuck-language"),
            (">", "Move to Next Element"),
            ("<", "Move to Previous Element"),
            ("+", "Increment Current Element"),
            ("-", "Decrement Current Element"),
            (",", "Await Input(Currently Not Implemented)"),
            (".", "Output Current Element(in ASCII)"),
            ("[", "Jump past matching ] if Element is 0"),
            ("]", "Jump back to matching [ if Element is not 0"),
        ],
    },
    "deadsimple": {
        "name": "DeadSimple",
        "color": "dark_blue",
        "run": lambda engine, code: [interp.deadsimple(code)],
        "examples": [("Print AbC", "S%+S^++S")],
        "about": "There are only 5 symbols allowed. Starts at A.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/DeadSimple"),
            ("+", "Move up Alphabet"),
            ("-", "Move down Alphabet"),
            ("S", "Print"),
            ("^", "Start at Uppercase A"),
            ("%", "Start at Lowercase a"),
            ("Note:", "The original language resets with _. Here ^ and % reset instead, and pick the case"),
        ],
    },
    "hatemath": {
        "name": "Hatemath",
        "color": "red",
        "run": lambda engine, code: [interp.hatemath(code)],
        "examples": [("Print hi", "<^^^^^^^^]^]")],
        "about": "There are only 8 symbols, working on 1 variable named x.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/Hatemath"),
            ("[", "Sets type of X to None"),
            ("<", "Sets type of X to ''"),
            (">", "Sets type of X to 0"),
            ("+", "Increment if it is an integer"),
            ("-", "Decrement if it is an integer"),
            ("^", "Move forward in alphabet(Only lowercase supported)"),
            ("/", "Move down the alphabet(Only lowercase supported)"),
            ("]", "Print Value"),
        ],
    },
    "hq9plus": {
        "name": "HQ9+",
        "color": "orange",
        "run": lambda engine, code: engine.run_hq9plus(code),
        "examples": [("Run all four: Hello World, quine, 99 Bottles, add 1", "hq9+")],
        "about": "There are only 4 symbols allowed.",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/HQ9%2B"),
            ("h", "Prints Hello World"),
            ("q", "Print Source Code(Quine)"),
            ("9", "Starts 99 Bottles of Beer on the wall"),
            ("+", "Increments the counter that is always running."),
        ],
    },
    "kallisti": {
        "name": "Kallisti",
        "color": "blue",
        "run": lambda engine, code: [interp.kallisti(code)],
        "intro": "Kallisti - Everything you send is repeated back exactly, even messages that start with $.",
        "examples": [("Repeat Rule 3: Everything is true", "Everything is true")],
        "about": "<anything> ::= <anything>",
        "fields": [
            ("EsoLangs.org Link:", "https://esolangs.org/wiki/Kallisti"),
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
        "run": lambda engine, code: [interp.unnecessary(code)],
        "intro": "Unnecessary - A successful call is an empty program (or just #), which prints *. "
                 "Anything else prints Unsuccessful.",
        "examples": [("Successful call: prints *", "#")],
        "fields": [
            ("Official Site", "http://yiap.nfshost.com/esoteric/unnecessary/unnecessary.html"),
            ("Esolangs.org Link:", "https://esolangs.org/wiki/unnecessary"),
            ("Rule 1:", "If a program file exists, report error and fail"),
            ("Rule 2:", "If no program file exists, create program with NOP(No Operation) instruction"),
            ("Successful call:", "An empty program, or just #, prints *. Anything else prints Unsuccessful"),
        ],
    },
}


class ChatEngine:
    def __init__(self):
        self.hq9_state = {"accumulator": 0}
        self._hq9_lock = threading.Lock()

    def languages(self):
        return [{"id": key, "name": meta["name"], "intro": meta.get("intro"),
                 "examples": [{"label": label, "code": code} for label, code in meta["examples"]],
                 "info_url": info_url(key), "help": help_card(key)} for key, meta in LANGUAGES.items()]

    def handle(self, message, language=None):
        stripped = message.lstrip()
        if stripped.startswith(PREFIX) and language != ECHO_LANGUAGE:
            name, args = COMMAND_RE.match(stripped).groups()
            return self.command(name.lower(), args)
        if not language:
            return [error("Pick a language or send a command.")]
        return self.run_language(language, message)

    def command(self, name, args):
        if name == "ping":
            return [text(PING_BF)]
        if name in ("hello", "hi"):
            return [text(HELLO_BF)]
        if name in LANGUAGES:
            return self.run_language(name, args)
        return [error("Unknown command %s%s." % (PREFIX, name))]

    def run_language(self, language, code):
        meta = LANGUAGES.get(language)
        if meta is None:
            return [error("Unknown language: %s" % language)]
        try:
            return [text(m) for m in cap_output(meta["run"](self, code))]
        except interp.InterpreterError as e:
            return [error("Invalid %s Command: %s" % (meta["name"], e))]

    def run_hq9plus(self, code):
        with self._hq9_lock:
            return interp.hq9plus(code, self.hq9_state)
