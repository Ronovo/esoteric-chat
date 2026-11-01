const logs = document.getElementById("logs");
const chatList = document.getElementById("chat-list");
const newChatButton = document.getElementById("new-chat");
const form = document.getElementById("composer");
const languageSelect = document.getElementById("language");
const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send");
const exampleSelect = document.getElementById("example");
const commandsButton = document.getElementById("commands");
const explainedLink = document.getElementById("explained");
const clearButton = document.getElementById("clear-chat");
const clearConfirm = document.getElementById("clear-confirm");
const clearYes = document.getElementById("clear-yes");
const clearNo = document.getElementById("clear-no");

const BOT = "Esoteric Chat";
const WELCOME = "Welcome! Pick a language, write some code and hit Send.";
const SAVE_FAILED = "Could not save to your account.";
const DRAFT_DELAY = 1000;

let languages = [];
let languagesFailed = false;
let chats = [];
let active = null;
let saving = document.documentElement.dataset.loggedIn === "1";
let draftTimer = null;

function languageNamed(id) {
  return languages.find((l) => l.id === id);
}

function selectedLanguage() {
  return languageNamed(languageSelect.value);
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

function showIntro(chat) {
  const lang = selectedLanguage();
  if (lang && lang.intro) addMessage(chat, "bot", BOT, { type: "text", text: lang.intro });
}

async function api(path, method, body) {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error("Request failed (" + res.status + ")");
  return res.status === 204 ? null : res.json();
}

function saveFailed(chat) {
  addMessage(chat, "bot", BOT, { type: "error", text: SAVE_FAILED }, false);
}

function store(chat, request) {
  return request.catch(() => saveFailed(chat));
}

/* Shows a message in a chat and, when the chat is saved to a portfolio account, keeps it there too. Replies to
   api/chat are saved by the server, so send() passes keep=false. */
function addMessage(chat, role, metaText, content, keep = true) {
  const wrapper = document.createElement("div");
  wrapper.className = "msg " + role;
  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = metaText;
  wrapper.append(meta, render(content));
  chat.log.append(wrapper);
  chat.log.scrollTop = chat.log.scrollHeight;
  if (keep && saving && chat.id !== null) {
    store(chat, api("api/chats/" + chat.id + "/messages", "POST", { role, meta: metaText, content }));
  }
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
  card.append(title);
  if (reply.about) {
    const about = document.createElement("p");
    about.textContent = reply.about;
    card.append(about);
  }
  const list = document.createElement("dl");
  reply.fields.forEach((field) => {
    const dt = document.createElement("dt");
    dt.textContent = field.name;
    const dd = document.createElement("dd");
    linkify(dd, field.value);
    list.append(dt, dd);
  });
  card.append(list);
  return card;
}

function render(content) {
  if (content.type === "card") return helpCard(content);
  if (content.type === "error") return bubble(content.text, "error");
  if (content.text === "") return bubble("(no output)", "empty");
  return bubble(content.text);
}

function nextChatNumber() {
  return Math.max(0, ...chats.map((chat) => Number((/^Chat (\d+)$/.exec(chat.name) || [])[1]) || 0)) + 1;
}

function updateItem(chat) {
  const lang = languageNamed(chat.language);
  chat.title.textContent = chat.name;
  chat.subtitle.textContent = lang ? lang.name : "No language";
}

function refreshCloseButtons() {
  chats.forEach((chat) => { chat.close.hidden = chats.length < 2; });
}

function makeChat({ id = null, name, language, draft = "" }) {
  const log = document.createElement("main");
  log.className = "log";
  log.setAttribute("aria-live", "polite");
  log.hidden = true;
  logs.append(log);

  const item = document.createElement("li");
  const open = document.createElement("button");
  open.type = "button";
  open.className = "chat-open";
  const title = document.createElement("span");
  title.className = "chat-name";
  const subtitle = document.createElement("span");
  subtitle.className = "chat-language";
  open.append(title, subtitle);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "chat-close";
  close.textContent = "×";
  close.setAttribute("aria-label", "Close chat");
  item.append(open, close);
  chatList.append(item);

  const chat = { id, name, language, draft, busy: false, log, item, title, subtitle, close };
  open.addEventListener("click", () => switchTo(chat));
  close.addEventListener("click", () => closeChat(chat));
  chats.push(chat);
  updateItem(chat);
  refreshCloseButtons();
  return chat;
}

function stashDraft() {
  clearTimeout(draftTimer);
  if (messageInput.value === active.draft) return;
  active.draft = messageInput.value;
  if (saving && active.id !== null) store(active, api("api/chats/" + active.id, "PATCH", { draft: active.draft }));
}

function switchTo(chat) {
  if (active === chat) return;
  if (active) {
    stashDraft();
    active.log.hidden = true;
    active.item.classList.remove("active");
  }
  active = chat;
  chat.log.hidden = false;
  chat.item.classList.add("active");
  languageSelect.value = chat.language;
  chat.language = languageSelect.value;
  updateExplainedLink();
  updateExamples();
  messageInput.value = chat.draft;
  showBusy(chat.busy);
  chat.log.scrollTop = chat.log.scrollHeight;
  messageInput.focus();
}

async function newChat() {
  const name = "Chat " + nextChatNumber();
  const chat = makeChat({ name, language: languages.length ? languages[0].id : "" });
  switchTo(chat);
  if (saving) {
    try {
      chat.id = (await api("api/chats", "POST", { name, language: chat.language || null })).id;
    } catch (err) {
      saveFailed(chat);
    }
  }
  if (languagesFailed) return;
  addMessage(chat, "bot", BOT, { type: "text", text: WELCOME });
  showIntro(chat);
}

function closeChat(chat) {
  if (chats.length < 2) return;
  const index = chats.indexOf(chat);
  chats.splice(index, 1);
  chat.log.remove();
  chat.item.remove();
  if (active === chat) {
    active = null;
    switchTo(chats[Math.min(index, chats.length - 1)]);
  }
  refreshCloseButtons();
  if (saving && chat.id !== null) store(active, api("api/chats/" + chat.id, "DELETE"));
}

async function loadSavedChats() {
  const { chats: saved } = await api("api/chats", "GET");
  saved.forEach((entry) => {
    const chat = makeChat(entry);
    entry.messages.forEach((m) => addMessage(chat, m.role, m.meta, m.content, false));
  });
}

function showBusy(busy) {
  sendButton.disabled = busy;
  clearButton.disabled = busy;
}

function setBusy(chat, busy) {
  chat.busy = busy;
  if (chat === active) showBusy(busy);
}

function closeClearConfirm() {
  clearConfirm.hidden = true;
  clearButton.focus();
}

async function send(message) {
  const chat = active;
  const language = languageSelect.value;
  const lang = selectedLanguage();
  const meta = lang ? lang.name : language || "no language";
  addMessage(chat, "user", meta, { type: "text", text: message }, false);
  setBusy(chat, true);
  const body = { message, language };
  if (saving && chat.id !== null) Object.assign(body, { chat_id: chat.id, meta });
  try {
    const res = await fetch("api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !Array.isArray(data.replies)) {
      addMessage(chat, "bot", BOT, { type: "error", text: data.error || "Request failed (" + res.status + ")" }, false);
      return;
    }
    data.replies.forEach((reply) => addMessage(chat, "bot", BOT, reply, false));
  } catch (err) {
    addMessage(chat, "bot", BOT, { type: "error", text: "Could not reach the server." }, false);
  } finally {
    setBusy(chat, false);
    if (chat === active) messageInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sendButton.disabled) return;
  const message = messageInput.value;
  if (!message.trim()) return;
  messageInput.value = "";
  stashDraft();
  send(message);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

messageInput.addEventListener("input", () => {
  clearTimeout(draftTimer);
  draftTimer = setTimeout(stashDraft, DRAFT_DELAY);
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
  if (lang) addMessage(active, "bot", BOT, { type: "card", ...lang.help });
});

languageSelect.addEventListener("change", () => {
  active.language = languageSelect.value;
  updateItem(active);
  if (saving && active.id !== null) {
    store(active, api("api/chats/" + active.id, "PATCH", { language: active.language || null }));
  }
  updateExplainedLink();
  updateExamples();
  showIntro(active);
});

newChatButton.addEventListener("click", newChat);

clearButton.addEventListener("click", () => {
  clearConfirm.hidden = false;
  clearNo.focus();
});

clearNo.addEventListener("click", closeClearConfirm);

clearConfirm.addEventListener("click", (event) => {
  if (event.target === clearConfirm) closeClearConfirm();
});

clearConfirm.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeClearConfirm();
});

clearYes.addEventListener("click", () => {
  clearConfirm.hidden = true;
  active.log.replaceChildren();
  if (saving && active.id !== null) store(active, api("api/chats/" + active.id + "/messages", "DELETE"));
  messageInput.focus();
});

async function init() {
  const problems = [];
  try {
    const res = await fetch("api/languages");
    if (!res.ok) throw new Error(res.statusText);
    ({ languages } = await res.json());
  } catch (err) {
    languagesFailed = true;
    problems.push("Could not load languages.");
  }
  languages.forEach((lang) => {
    const option = document.createElement("option");
    option.value = lang.id;
    option.textContent = lang.name;
    languageSelect.append(option);
  });
  if (saving) {
    try {
      await loadSavedChats();
    } catch (err) {
      saving = false;
      problems.push("Could not load your saved chats, so this visit is not being saved.");
    }
  }
  if (chats.length) switchTo(chats[chats.length - 1]);
  else await newChat();
  problems.forEach((text) => addMessage(active, "bot", BOT, { type: "error", text }, false));
  messageInput.focus();
}

function namePortfolioButton() {
  const link = document.getElementById("portfolio-button");
  if (!link) return;
  fetch(`${link.dataset.portfolioUrl}/sso/me`, { credentials: "include", signal: AbortSignal.timeout(5000) })
    .then((response) => (response.ok ? response.json() : {}))
    .then((data) => {
      if (data.username) link.textContent = `Log in as ${data.username}`;
    })
    .catch(() => {});
}

init();
namePortfolioButton();
