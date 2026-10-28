import re
import threading

from . import interpreters as interp

PREFIX = "$"
# "$name", then everything after one separating space or newline, exactly as typed.
COMMAND_RE = re.compile(r"\$(\S*)\s?(.*)", re.S)
ECHO_LANGUAGE = "kallisti"


def text(value):
    return {"type": "text", "text": value}


def error(value):
    return {"type": "error", "text": value}


def help_card(topic):
    entry = HELP[topic]
    return {"type": "help", "title": entry["title"], "color": entry["color"],
            "fields": [{"name": n, "value": v} for n, v in entry["fields"]]}


def info_url(topic):
    urls = [v for _, v in HELP[topic]["fields"] if v.startswith("http")]
    return next((u for u in urls if "esolangs.org" in u), urls[0])


# Listed in the order the language picker shows them: alphabetical by name.
LANGUAGES = {
    "fivecommand": {"name": "5command", "error": "Invalid 5command Command",
                    "examples": [("Print 1337", "^p+^^^p+^^^p+^^^^^^^p")]},
    "bf": {
        "name": "Brainfart",
        "error": "Invalid Brainfart Command",
        "intro": "Brainfart - The Safe-For-Work alternative to BrainF**K",
        "examples": [
            ("Print Hello World!", "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+."),
            ("$hi: get a program that prints Hello", "$hi"),
            ("$ping: get a program that prints Pong!", "$ping"),
        ],
    },
    "deadsimple": {"name": "DeadSimple", "error": "Invalid DeadSimple Command", "examples": [("Print AbC", "S%+S^++S")]},
    "hatemath": {"name": "Hatemath", "error": "Invalid Hatemath Command", "examples": [("Print hi", "<^^^^^^^^]^]")]},
    "hq9plus": {"name": "HQ9+", "error": "Invalid HQ9+ command!", "examples": [("Run all four: Hello World, quine, 99 Bottles, add 1", "hq9+")]},
    "kallisti": {
        "name": "Kallisti",
        "error": "Invalid Kallisti Command",
        "intro": "Kallisti - Everything you send is repeated back exactly, even messages that start with $.",
        "examples": [("Repeat Rule 3: Everything is true", "Everything is true")],
    },
    "unnecessary": {
        "name": "Unnecessary",
        "error": "Invalid Unnecessary Command",
        "intro": "Unnecessary - A successful call is an empty program (or just #), which prints *. "
                 "Anything else prints Unsuccessful.",
        "examples": [("Successful call: prints *", "#")],
    },
}

HELP = {
    "bf": {
        "title": "Brainfart",
        "color": "red",
        "fields": [
            ("More Information:", "https://esolangs.org/wiki/brainfuck"),
            ("English-to-Brainfart Converter:", "https://www.dcode.fr/brainfuck-language"),
            ("There are only 8 symbols allowed.", "-------------------------------"),
            (">", "Move to Next Element"),
            ("<", "Move to Previous Element"),
            ("+", "Increment Current Element"),
            ("-", "Decrement Current Element"),
            (",", "Await Input(Currently Not Implemented)"),
            (".", "Output Current Element(in ASCII)"),
            ("[", "Jump past matching ] if Element is 0"),
            ("]", "Jump back to matching [ if Element is not 0"),
            ("---", "All Other Commands are Ignored"),
        ],
    },
    "kallisti": {
        "title": "Kallisti",
        "color": "blue",
        "fields": [
            ("EsoLangs.org Link:", "https://bit.ly/2SdwN4b"),
            ("<anything> ::= <anything>", "-------------------------------"),
            ("Rule 1:", "Obey as many rules as possible"),
            ("Rule 2:", "There is plenty nothing"),
            ("Rule 3:", "Everything is true"),
            ("Rule 4:", "Everything is false"),
            ("Rule 5:", "There is only nothing"),
            ("Rule 6:", "Obey as few rules as possible"),
        ],
    },
    "unnecessary": {
        "title": "Unnecessary",
        "color": "blue",
        "fields": [
            ("Official Site", "http://yiap.nfshost.com/esoteric/unnecessary/unnecessary.html"),
            ("Esolangs.org Link:", "https://esolangs.org/wiki/unnecessary"),
            ("TL;DR", "-------------------------------"),
            ("Rule 1:", "If a program file exists, report error and fail"),
            ("Rule 2:", "If no program file exists, create program with NOP(No Operation) instruction"),
            ("Successful call:", "An empty program, or just #, prints *. Anything else prints Unsuccessful"),
        ],
    },
    "hq9plus": {
        "title": "HQ9+",
        "color": "orange",
        "fields": [
            ("Official Site", "https://goo.gl/jKpbSk"),
            ("Esolangs.org Link:", "https://esolangs.org/wiki/HQ9%2B"),
            ("There are only 4 symbols allowed.", "-------------------------------"),
            ("h", "Prints Hello World"),
            ("q", "Print Source Code(Quine)"),
            ("9", "Starts 99 Bottles of Beer on the wall"),
            ("+", "Increments the counter that is always running."),
        ],
    },
    "hatemath": {
        "title": "hatemath",
        "color": "red",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/Hatemath"),
            ("There are only 8 symbols, working on 1 variable named x", "-------------------------------"),
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
    "deadsimple": {
        "title": "DeadSimple",
        "color": "dark_blue",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/DeadSimple"),
            ("There are only 5 symbols allowed. Starts at A", "-------------------------------"),
            ("+", "Move up Alphabet"),
            ("-", "Move down Alphabet"),
            ("S", "Print"),
            ("^", "Start at Uppercase A"),
            ("%", "Start at Lowercase a"),
            ("Note:", "The original language resets with _. Because of message limits, ^ and % replace it here"),
        ],
    },
    "fivecommand": {
        "title": "5command",
        "color": "purple",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/5command"),
            ("There are only 5 symbols allowed.", "-------------------------------"),
            ("+", "Move pointer right on the tape"),
            ("-", "Move pointer left on the tape"),
            ("^", "Increments current cell at pointer"),
            ("v", "Decrements current cell at pointer"),
            ("P", "Prints current cell at pointer"),
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
            return [text(interp.PING_BF)]
        if name in ("hello", "hi"):
            return [text(interp.HELLO_BF)]
        if name in LANGUAGES:
            return self.run_language(name, args)
        return [error("Unknown command %s%s." % (PREFIX, name))]

    def run_language(self, language, code):
        meta = LANGUAGES.get(language)
        if meta is None:
            return [error("Unknown language: %s" % language)]
        try:
            return self._run(language, code)
        except interp.InterpreterError as e:
            return [error("%s: %s" % (meta["error"], e))]
        except Exception:
            return [error(meta["error"])]

    def _run(self, language, code):
        if language == "bf":
            return [text(interp.brainfart(code))]
        if language == "kallisti":
            return [text(interp.kallisti(code))]
        if language == "unnecessary":
            return [text(interp.unnecessary(code))]
        if language == "hq9plus":
            with self._hq9_lock:
                return [text(m) for m in interp.hq9plus(code, self.hq9_state)]
        if language == "hatemath":
            return [text(interp.hatemath(code))]
        if language == "deadsimple":
            return [text(interp.deadsimple(code))]
        return [text(interp.fivecommand(code))]
