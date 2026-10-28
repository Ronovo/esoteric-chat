const log = document.getElementById("log");
const form = document.getElementById("composer");
const languageSelect = document.getElementById("language");
const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send");
const exampleSelect = document.getElementById("example");
const commandsButton = document.getElementById("commands");
const explainedLink = document.getElementById("explained");

let languages = [];

function selectedLanguage() {
  return languages.find((l) => l.id === languageSelect.value);
}

function updateExplainedLink() {
  const lang = selectedLanguage();
  if (lang) explainedLink.href = lang.info_url;
}

function updateExamples() {
  const lang = selectedLanguage();
  exampleSelect.replaceChildren(new Option("Try example", ""));
  if (lang) lang.examples.forEach((example, i) => exampleSelect.append(new Option(example.label, i)));
}

function showIntro() {
  const lang = selectedLanguage();
  if (lang && lang.intro) addMessage("bot", "Esoteric Chat", bubble(lang.intro));
}

function addMessage(role, metaText, content) {
  const wrapper = document.createElement("div");
  wrapper.className = "msg " + role;
  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = metaText;
  wrapper.append(meta, content);
  log.append(wrapper);
  log.scrollTop = log.scrollHeight;
}

function bubble(text, extraClass) {
  const el = document.createElement("pre");
  el.className = "bubble" + (extraClass ? " " + extraClass : "");
  el.textContent = text;
  return el;
}

function linkify(parent, text) {
  const parts = text.split(/(https?:\/\/\S+)/);
  parts.forEach((part, i) => {
    if (i % 2 === 1) {
      const a = document.createElement("a");
      a.href = part;
      a.textContent = part;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      parent.append(a);
    } else if (part) {
      parent.append(document.createTextNode(part));
    }
  });
}

function helpCard(reply) {
  const card = document.createElement("div");
  card.className = "card";
  card.style.setProperty("--card-color", "var(--" + reply.color + ")");
  const title = document.createElement("h2");
  title.textContent = reply.title;
  const list = document.createElement("dl");
  reply.fields.forEach((field) => {
    const dt = document.createElement("dt");
    dt.textContent = field.name;
    const dd = document.createElement("dd");
    linkify(dd, field.value);
    list.append(dt, dd);
  });
  card.append(title, list);
  return card;
}

function renderReply(reply) {
  if (reply.type === "help") return helpCard(reply);
  if (reply.type === "error") return bubble(reply.text, "error");
  if (reply.text === "") return bubble("(no output)", "empty");
  return bubble(reply.text);
}

async function send(message) {
  const language = languageSelect.value;
  const lang = selectedLanguage();
  const isCommand = message.trim().startsWith("$") && language !== "kallisti";
  addMessage("user", isCommand ? "command" : lang ? lang.name : language, bubble(message));
  sendButton.disabled = true;
  try {
    const res = await fetch("api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, language }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      addMessage("bot", "Esoteric Chat", bubble(data.error || "Request failed (" + res.status + ")", "error"));
      return;
    }
    data.replies.forEach((reply) => addMessage("bot", "Esoteric Chat", renderReply(reply)));
  } catch (err) {
    addMessage("bot", "Esoteric Chat", bubble("Could not reach the server.", "error"));
  } finally {
    sendButton.disabled = false;
    messageInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sendButton.disabled) return;
  const message = messageInput.value;
  if (!message.trim()) return;
  messageInput.value = "";
  send(message);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

exampleSelect.addEventListener("change", () => {
  const lang = selectedLanguage();
  const example = lang && lang.examples[exampleSelect.value];
  exampleSelect.value = "";
  if (example) {
    messageInput.value = example.code;
    messageInput.focus();
  }
});

commandsButton.addEventListener("click", () => {
  const lang = selectedLanguage();
  if (lang) addMessage("bot", "Esoteric Chat", helpCard(lang.help));
});

languageSelect.addEventListener("change", () => {
  updateExplainedLink();
  updateExamples();
  showIntro();
});

async function init() {
  try {
    const res = await fetch("api/languages");
    if (!res.ok) throw new Error(res.statusText);
    languages = (await res.json()).languages;
  } catch (err) {
    addMessage("bot", "Esoteric Chat", bubble("Could not load languages.", "error"));
    return;
  }
  languages.forEach((lang) => {
    const option = document.createElement("option");
    option.value = lang.id;
    option.textContent = lang.name;
    languageSelect.append(option);
  });
  updateExplainedLink();
  updateExamples();
  addMessage("bot", "Esoteric Chat", bubble("Welcome! Pick a language, write some code and hit Send."));
  showIntro();
  messageInput.focus();
}

init();
