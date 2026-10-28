import threading

from . import interpreters as interp

PREFIX = "$"


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


LANGUAGES = {
    "bf": {
        "name": "Brainfart",
        "error": "Invalid Brainfart Command",
        "intro": "Brainfart - The Safe-For-Work alternative to BrainF**K",
        "example": "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.",
    },
    "kallisti": {"name": "Kallisti", "error": "Invalid Kallisti Command", "example": "Everything is true"},
    "unnecessary": {"name": "Unnecessary", "error": "Invalid Unnecessary Command", "example": "#"},
    "hq9plus": {"name": "HQ9+", "error": "Invalid HQ9+ command!", "example": "qhq"},
    "hatemath": {"name": "Hatemath", "error": "Invalid Hatemath Command", "example": "<^^^^^^^^]^]"},
    "deadsimple": {"name": "DeadSimple", "error": "Invalid DeadSimple Command", "example": "S%+S^++S"},
    "fivecommand": {"name": "5command", "error": "Invalid 5command Command", "example": "^p+^^^p+^^^p+^^^^^^^p"},
    "debugfivecommand": {"name": "5command (debug)", "error": "Invalid 5command Command", "example": "^^p+^p"},
}

FIVECOMMAND_FIELDS = [
    ("There are only 5 symbols allowed.", "-------------------------------"),
    ("+", "Move pointer right on the tape"),
    ("-", "Move pointer left on the tape"),
    ("^", "Increments current cell at pointer"),
    ("v", "Decrements current cell at pointer"),
    ("P", "Prints current cell at pointer"),
    ("Example: ^p+^^^p+^^^p+^^^^^^^p", "Output: 1337"),
]

HELP = {
    "help": {
        "title": "Help",
        "color": "orange",
        "fields": [
            ("Language picker", "Pick a language from the dropdown and send code to run it directly"),
            ("$ping", "Returns pong in Brainfart"),
            ("$hi", "Returns hello in Brainfart"),
            ("$bf <code>", "Interpreter that Runs Brainfart Programs"),
            ("$kallisti <code>", "Interpreter that Runs Kallisti Programs"),
            ("$unnecessary <code>", "Interpreter that Runs Unnecessary Programs"),
            ("$hq9plus <code>", "Interpreter that Runs HQ9+ Programs"),
            ("$hatemath <code>", "Interpreter that Runs hatemath Programs"),
            ("$deadsimple <code>", "Interpreter that Runs DeadSimple Programs"),
            ("$fivecommand <code>", "Interpreter that Runs 5command Programs"),
            ("$help", "Returns this help"),
            ("$help <command>", "Returns information about that commands language. ex $help bf"),
        ],
    },
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
            ("Example:", 'code: qhq prints "qhq","Hello World! :)","qhq"'),
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
            ("There are only 4 symbols allowed. Starts at A", "-------------------------------"),
            ("+", "Move up Alphabet"),
            ("-", "Move down Alphabet"),
            ("S", "Print"),
            ("_", "Reset to 0(see Note Below)"),
            ("Note:", "Because of message limits, to cut down on input, I added two replacements for _"),
            ("^", "Start at Uppercase A"),
            ("%", "Start at Lowercase a"),
            ("Example: S%+S^++S", "Output: AbC"),
        ],
    },
    "fivecommand": {
        "title": "5command",
        "color": "purple",
        "fields": [("Esolangs.org Link:", "https://esolangs.org/wiki/5command")] + FIVECOMMAND_FIELDS + [
            ("Note:", "If you want to see debug logs, call program with $debugfivecommand"),
        ],
    },
    "debugfivecommand": {
        "title": "Debug version of 5command",
        "color": "purple",
        "fields": [
            ("Esolangs.org Link:", "https://esolangs.org/wiki/5command"),
            ("-------------------------------", "Returns a Debug Log Along with a message"),
        ] + FIVECOMMAND_FIELDS,
    },
}


class ChatEngine:
    def __init__(self):
        self.hq9_state = {"accumulator": 0}
        self._hq9_lock = threading.Lock()

    def languages(self):
        return [{"id": key, "name": meta["name"], "example": meta["example"], "intro": meta.get("intro"),
                 "info_url": info_url(key), "help": help_card(key)} for key, meta in LANGUAGES.items()]

    def handle(self, message, language=None):
        stripped = message.strip()
        if stripped.startswith(PREFIX):
            parts = stripped[len(PREFIX):].split(None, 1)
            name = parts[0].lower() if parts else ""
            args = parts[1] if len(parts) > 1 else ""
            return self.command(name, args)
        if not language:
            return [error("Pick a language or send a command. Type $help for a list of commands.")]
        return self.run_language(language, message)

    def command(self, name, args):
        if name == "ping":
            return [text(interp.PING_BF)]
        if name in ("hello", "hi"):
            return [text(interp.HELLO_BF)]
        if name == "help":
            topic = args.strip().lower() or "help"
            return [help_card(topic)] if topic in HELP else [error("Invalid Command")]
        if name in LANGUAGES:
            return self.run_language(name, args)
        return [error("Unknown command %s%s. Type $help for a list of commands." % (PREFIX, name))]

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
        if language == "fivecommand":
            return [text(interp.fivecommand(code)[0])]
        output, debug = interp.fivecommand(code)
        return [text("Result : %s" % output), text("Debug : %s" % ", ".join(debug))]
