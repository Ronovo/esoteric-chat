import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE = readFileSync(join(ROOT, 'esoteric_chat', 'templates', 'index.html'), 'utf8');
const LANGUAGES = {
  languages: [
    {
      id: 'bf', name: 'Brainfart', intro: 'Brainfart - the safe-for-work one', info_url: 'https://esolangs.org/wiki/brainfuck',
      examples: [{ label: 'Print A', code: '+.' }, { label: 'Print hello world', code: '+++.' }],
      help: { title: 'Brainfart', color: 'red', about: 'Eight symbols.', fields: [
        { name: 'More Information:', value: 'https://esolangs.org/wiki/brainfuck' }, { name: '>', value: 'Move right' }] },
    },
    {
      id: 'kallisti', name: 'Kallisti', intro: null, info_url: 'https://esolangs.org/wiki/Kallisti', examples: [],
      help: { title: 'Kallisti', color: 'blue', about: null, fields: [
        { name: 'Rule 1:', value: 'see https://example.com/rules for more' }] },
    },
  ],
};
const BOT = 'Esoteric Chat';
const WELCOME = 'Welcome! Pick a language, write some code and hit Send.';
const INTRO = 'Brainfart - the safe-for-work one';
const SAVE_FAILED = 'Could not save to your account.';

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function reply(status, body) {
  return { ok: status >= 200 && status < 300, status, statusText: 'status', json: async () => body };
}

/* The page as Flask renders it, with the portfolio button only when portfolioUrl is given. */
function render(portfolioUrl, loggedIn) {
  const start = TEMPLATE.indexOf('>', TEMPLATE.indexOf('<body')) + 1;
  const body = TEMPLATE.slice(start, TEMPLATE.indexOf('<script', start));
  document.body.innerHTML = body.replace(/{% if logged_in %}[\s\S]*?{% elif portfolio %}([\s\S]*?){% endif %}/,
    (_, button) => (portfolioUrl ? button.replace('{{ portfolio_url }}', portfolioUrl) : ''))
    .replace(/{% include "_theme_picker.html" %}/, '')
    .replace(/{% for message in get_flashed_messages\(\) %}[\s\S]*?{% endfor %}/, '');
  document.documentElement.dataset.loggedIn = loggedIn ? '1' : '';
}

async function settle() {
  for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

/* A stand-in for the saved-chats API of one portfolio account. `fail(method, url)` makes a request answer 500. */
function account(saved = [], fail = () => false) {
  const state = { chats: saved.map((c) => ({ language: 'bf', draft: '', messages: [], ...c })), next: 100, calls: [] };
  state.handle = (url, method, body) => {
    state.calls.push([method, url, body]);
    if (fail(method, url)) return reply(500, { error: 'broken' });
    const [, id, messages] = /^api\/chats(?:\/(\d+)(\/messages)?)?$/.exec(url);
    if (!id) {
      if (method === 'GET') return reply(200, { chats: state.chats });
      state.chats.push({ ...body, id: state.next, draft: '', messages: [] });
      return reply(201, { id: state.next++ });
    }
    const chat = state.chats.find((c) => c.id === Number(id));
    if (!chat) return reply(404, { error: 'No such chat' });
    if (messages) chat.messages = method === 'DELETE' ? [] : [...chat.messages, body];
    else if (method === 'DELETE') state.chats.splice(state.chats.indexOf(chat), 1);
    else Object.assign(chat, body);
    return reply(204, null);
  };
  return state;
}

async function boot({ languages = () => reply(200, LANGUAGES), chat = () => reply(200, { replies: [] }), portfolio, saved } = {}) {
  render(portfolio && 'http://portfolio.test', saved);
  const fetch = vi.fn(async (url, options) => {
    if (url === 'api/languages') return languages();
    if (url === 'api/chat') return chat(JSON.parse(options.body));
    if (url.startsWith('api/chats')) return saved.handle(url, options.method, options.body && JSON.parse(options.body));
    return portfolio();
  });
  vi.stubGlobal('fetch', fetch);
  vi.resetModules();
  await import('../../esoteric_chat/static/app.js');
  await settle();
  return fetch;
}

const $ = (id) => document.getElementById(id);
const messages = () => [...document.querySelectorAll('.log:not([hidden]) .msg')].map((m) => [m.className, m.querySelector('.meta').textContent,
  m.lastElementChild.textContent]);
const tabs = () => [...document.querySelectorAll('#chat-list li')].map((li) => [li.querySelector('.chat-name').textContent,
  li.querySelector('.chat-language').textContent, li.classList.contains('active')]);
const tab = (name) => [...document.querySelectorAll('.chat-name')].find((el) => el.textContent === name).parentElement;
const closeButton = (name) => tab(name).parentElement.querySelector('.chat-close');
const chatCalls = (fetch) => fetch.mock.calls.filter(([url]) => url === 'api/chat').map(([, options]) => JSON.parse(options.body));

async function send(text) {
  $('message').value = text;
  $('composer').requestSubmit();
  await settle();
}

function choose(select, value) {
  select.value = value;
  select.dispatchEvent(new Event('change'));
}

function type(text) {
  $('message').value = text;
  $('message').dispatchEvent(new Event('input'));
}

async function newChat() {
  $('new-chat').click();
  await settle();
}

describe('starting up', () => {
  it('lists the languages, picks the first and greets in a first chat', async () => {
    await boot();
    expect([...$('language').options].map((o) => o.value)).toEqual(['bf', 'kallisti']);
    expect($('explained').href).toBe('https://esolangs.org/wiki/brainfuck');
    expect([...$('example').options].map((o) => o.textContent)).toEqual(['Try example', 'Print A', 'Print hello world']);
    expect(messages()).toEqual([['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO]]);
    expect(tabs()).toEqual([['Chat 1', 'Brainfart', true]]);
    expect(closeButton('Chat 1').hidden).toBe(true);
    expect(document.activeElement).toBe($('message'));
  });

  it('still greets when the server lists no languages', async () => {
    await boot({ languages: () => reply(200, { ...LANGUAGES, languages: [] }) });
    expect($('explained').hasAttribute('href')).toBe(false);
    expect([...$('example').options].map((o) => o.textContent)).toEqual(['Try example']);
    expect(messages()).toEqual([['msg bot', BOT, WELCOME]]);
    expect(tabs()).toEqual([['Chat 1', 'No language', true]]);
  });

  it.each([
    ['the server refuses', () => reply(503, {})],
    ['the server is down', () => { throw new TypeError('offline'); }],
  ])('says when the languages cannot be loaded because %s', async (_, languages) => {
    await boot({ languages });
    expect(messages()).toEqual([['msg bot', BOT, 'Could not load languages.']]);
    $('commands').click();
    expect(messages()).toHaveLength(1);
    await newChat();
    expect(messages()).toEqual([]);
  });
});

describe('picking a language', () => {
  it('updates the link, examples and tab, and shows an intro only when there is one', async () => {
    await boot();
    choose($('language'), 'kallisti');
    expect($('explained').href).toBe('https://esolangs.org/wiki/Kallisti');
    expect([...$('example').options].map((o) => o.textContent)).toEqual(['Try example']);
    expect(messages()).toHaveLength(2);
    expect(tabs()).toEqual([['Chat 1', 'Kallisti', true]]);
    choose($('language'), 'bf');
    expect(messages().at(-1)[2]).toBe(INTRO);
  });

  it('puts an example in the message box', async () => {
    await boot();
    choose($('example'), '1');
    expect($('message').value).toBe('+++.');
    expect($('example').value).toBe('');
    $('message').value = 'kept';
    choose($('example'), '');
    expect($('message').value).toBe('kept');
  });

  it('shows the help card, linking any address in it', async () => {
    await boot();
    $('commands').click();
    const card = document.querySelector('.card');
    expect(card.style.getPropertyValue('--card-color')).toBe('var(--red)');
    expect(card.querySelector('h2').textContent).toBe('Brainfart');
    expect(card.querySelector('p').textContent).toBe('Eight symbols.');
    const link = card.querySelector('dd a');
    expect([link.href, link.target, link.rel]).toEqual(['https://esolangs.org/wiki/brainfuck', '_blank', 'noopener noreferrer']);
    choose($('language'), 'kallisti');
    $('commands').click();
    const rules = document.querySelectorAll('.card')[1];
    expect(rules.querySelector('p')).toBeNull();
    expect([...rules.querySelector('dd').childNodes].map((n) => n.textContent)).toEqual(['see ', 'https://example.com/rules', ' for more']);
  });
});

describe('sending', () => {
  it('posts the code and shows each kind of reply', async () => {
    const fetch = await boot({ chat: () => reply(200, { replies: [{ type: 'text', text: 'A' }, { type: 'text', text: '' },
      { type: 'error', text: 'Invalid Brainfart Command: unmatched' }] }) });
    await send('+.');
    expect(fetch).toHaveBeenCalledWith('api/chat', expect.objectContaining({ method: 'POST', body: '{"message":"+.","language":"bf"}' }));
    expect(messages().slice(2)).toEqual([
      ['msg user', 'Brainfart', '+.'],
      ['msg bot', BOT, 'A'],
      ['msg bot', BOT, '(no output)'],
      ['msg bot', BOT, 'Invalid Brainfart Command: unmatched'],
    ]);
    expect([...document.querySelectorAll('.bubble')].slice(-2).map((b) => b.className)).toEqual(['bubble empty', 'bubble error']);
    expect($('message').value).toBe('');
    expect($('send').disabled).toBe(false);
  });

  it('labels $ messages with the language like any other message', async () => {
    await boot();
    await send('  $unnecessary');
    choose($('language'), 'kallisti');
    await send('$unnecessary');
    expect(messages().filter((m) => m[0] === 'msg user').map((m) => m[1])).toEqual(['Brainfart', 'Kallisti']);
  });

  it('labels messages sent without a known language', async () => {
    await boot({ languages: () => reply(503, {}) });
    await send('hello');
    $('language').append(new Option('Retired', 'retired', true, true));
    await send('hello');
    expect(messages().filter((m) => m[0] === 'msg user').map((m) => m[1])).toEqual(['no language', 'retired']);
  });

  it.each([
    ['a refusal with a reason', () => reply(400, { error: "'language' must be a string" }), "'language' must be a string"],
    ['a refusal without one', () => ({ ok: false, status: 500, json: async () => { throw new SyntaxError('html'); } }),
      'Request failed (500)'],
    ['a reply without replies', () => reply(200, { replies: 'nope' }), 'Request failed (200)'],
    ['the server being down', () => { throw new TypeError('offline'); }, 'Could not reach the server.'],
  ])('reports %s', async (_, chat, text) => {
    await boot({ chat });
    await send('+.');
    expect(messages().at(-1)).toEqual(['msg bot', BOT, text]);
    expect($('send').disabled).toBe(false);
  });

  it('ignores blank messages and a second send while one is on its way', async () => {
    let answer;
    const fetch = await boot({ chat: () => new Promise((resolve) => { answer = resolve; }) });
    await send('   ');
    $('message').value = '+.';
    $('composer').requestSubmit();
    expect($('send').disabled).toBe(true);
    $('message').value = '-.';
    $('composer').requestSubmit();
    answer(reply(200, { replies: [] }));
    await settle();
    expect(chatCalls(fetch)).toHaveLength(1);
  });

  it('sends on Enter and adds a line on Shift+Enter', async () => {
    const fetch = await boot();
    $('message').value = '+.';
    const shifted = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true });
    $('message').dispatchEvent(shifted);
    expect(shifted.defaultPrevented).toBe(false);
    $('message').dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    expect(chatCalls(fetch)).toHaveLength(0);
    $('message').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
    await settle();
    expect(chatCalls(fetch)).toHaveLength(1);
  });
});

describe('several chats', () => {
  it('opens a fresh chat and switches back to the draft, language and messages left behind', async () => {
    await boot();
    choose($('language'), 'kallisti');
    $('message').value = 'unsent';
    await newChat();
    expect(tabs()).toEqual([['Chat 1', 'Kallisti', false], ['Chat 2', 'Brainfart', true]]);
    expect(messages()).toEqual([['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO]]);
    expect($('message').value).toBe('');
    expect($('language').value).toBe('bf');
    expect(closeButton('Chat 1').hidden).toBe(false);
    expect(document.activeElement).toBe($('message'));

    tab('Chat 1').click();
    expect(tabs()).toEqual([['Chat 1', 'Kallisti', true], ['Chat 2', 'Brainfart', false]]);
    expect($('message').value).toBe('unsent');
    expect($('language').value).toBe('kallisti');
    expect($('explained').href).toBe('https://esolangs.org/wiki/Kallisti');
    expect([...$('example').options]).toHaveLength(1);
    expect(messages()).toEqual([['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO]]);
    tab('Chat 1').click();
    expect($('message').value).toBe('unsent');
  });

  it('delivers replies to the chat they were sent from and keeps Send per chat', async () => {
    const answers = [];
    const fetch = await boot({ chat: () => new Promise((resolve) => { answers.push(resolve); }) });
    await send('+.');
    expect($('send').disabled).toBe(true);
    await newChat();
    expect($('send').disabled).toBe(false);
    await send('-.');
    expect(chatCalls(fetch).map((c) => c.message)).toEqual(['+.', '-.']);
    answers[0](reply(200, { replies: [{ type: 'text', text: 'A' }] }));
    await settle();
    expect(messages()).toEqual([['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO], ['msg user', 'Brainfart', '-.']]);
    expect($('send').disabled).toBe(true);
    tab('Chat 1').click();
    expect(messages().slice(2)).toEqual([['msg user', 'Brainfart', '+.'], ['msg bot', BOT, 'A']]);
    expect($('send').disabled).toBe(false);
    answers[1](reply(200, { replies: [] }));
    await settle();
    tab('Chat 2').click();
    expect($('send').disabled).toBe(false);
  });

  it('closes chats, except the last one, and numbers new ones past the highest', async () => {
    await boot();
    closeButton('Chat 1').click();
    expect(tabs()).toHaveLength(1);
    await newChat();
    await newChat();
    closeButton('Chat 2').click();
    expect(tabs()).toEqual([['Chat 1', 'Brainfart', false], ['Chat 3', 'Brainfart', true]]);
    expect(document.querySelectorAll('.log')).toHaveLength(2);
    closeButton('Chat 3').click();
    expect(tabs()).toEqual([['Chat 1', 'Brainfart', true]]);
    expect(closeButton('Chat 1').hidden).toBe(true);
    await newChat();
    expect(tabs().map((t) => t[0])).toEqual(['Chat 1', 'Chat 2']);
    closeButton('Chat 1').click();
    expect(tabs()).toEqual([['Chat 2', 'Brainfart', true]]);
  });
});

describe('chats saved to the portfolio account', () => {
  const SAVED = [
    { id: 3, name: 'Loops', language: 'bf', draft: '', messages: [
      { role: 'user', meta: 'Brainfart', content: { type: 'text', text: '+.' } },
      { role: 'bot', meta: BOT, content: { type: 'text', text: '' } },
      { role: 'bot', meta: BOT, content: { type: 'error', text: 'bad' } },
      { role: 'bot', meta: BOT, content: { type: 'card', title: 'Kallisti', color: 'blue', about: null, fields: [] } }] },
    { id: 5, name: 'Chat 4', language: 'retired', draft: 'half done', messages: [] },
  ];

  it('loads the saved chats and opens the newest without saving anything', async () => {
    const saved = account(SAVED);
    const fetch = await boot({ saved });
    expect(saved.calls).toEqual([['GET', 'api/chats', undefined]]);
    expect(tabs()).toEqual([['Loops', 'Brainfart', false], ['Chat 4', 'No language', true]]);
    expect($('message').value).toBe('half done');
    expect($('language').value).toBe('');
    expect(messages()).toEqual([]);
    tab('Loops').click();
    expect(messages()).toEqual([['msg user', 'Brainfart', '+.'], ['msg bot', BOT, '(no output)'], ['msg bot', BOT, 'bad'],
      ['msg bot', BOT, 'Kallisti']]);
    expect(document.querySelector('.card').style.getPropertyValue('--card-color')).toBe('var(--blue)');
    await newChat();
    expect(tabs().at(-1)[0]).toBe('Chat 5');
    expect(saved.calls[1]).toEqual(['POST', 'api/chats', { name: 'Chat 5', language: 'bf' }]);
    expect(chatCalls(fetch)).toEqual([]);
  });

  it('saves a new chat, its messages, language, help cards and drafts, and deletes closed chats', async () => {
    const saved = account();
    const fetch = await boot({ saved });
    expect(saved.calls).toEqual([
      ['GET', 'api/chats', undefined],
      ['POST', 'api/chats', { name: 'Chat 1', language: 'bf' }],
      ['POST', 'api/chats/100/messages', { role: 'bot', meta: BOT, content: { type: 'text', text: WELCOME } }],
      ['POST', 'api/chats/100/messages', { role: 'bot', meta: BOT, content: { type: 'text', text: INTRO } }],
    ]);
    saved.calls.length = 0;

    choose($('language'), 'kallisti');
    $('commands').click();
    await settle();
    expect(saved.calls).toEqual([
      ['PATCH', 'api/chats/100', { language: 'kallisti' }],
      ['POST', 'api/chats/100/messages', { role: 'bot', meta: BOT, content: { type: 'card', ...LANGUAGES.languages[1].help } }],
    ]);
    saved.calls.length = 0;

    vi.useFakeTimers();
    type('half');
    type('half done');
    vi.advanceTimersByTime(999);
    expect(saved.calls).toEqual([]);
    vi.advanceTimersByTime(1);
    vi.useRealTimers();
    await settle();
    expect(saved.calls).toEqual([['PATCH', 'api/chats/100', { draft: 'half done' }]]);
    saved.calls.length = 0;

    await send('half done');
    expect(chatCalls(fetch)).toEqual([{ message: 'half done', language: 'kallisti', chat_id: 100, meta: 'Kallisti' }]);
    expect(saved.calls).toEqual([['PATCH', 'api/chats/100', { draft: '' }]]);
    saved.calls.length = 0;

    type('next');
    await newChat();
    expect(saved.calls).toEqual([
      ['PATCH', 'api/chats/100', { draft: 'next' }],
      ['POST', 'api/chats', { name: 'Chat 2', language: 'bf' }],
      ['POST', 'api/chats/101/messages', { role: 'bot', meta: BOT, content: { type: 'text', text: WELCOME } }],
      ['POST', 'api/chats/101/messages', { role: 'bot', meta: BOT, content: { type: 'text', text: INTRO } }],
    ]);
    saved.calls.length = 0;

    closeButton('Chat 1').click();
    await settle();
    expect(saved.calls).toEqual([['DELETE', 'api/chats/100', undefined]]);
    expect(saved.chats.map((c) => c.id)).toEqual([101]);
  });

  it('sends a language of null when a saved chat has none', async () => {
    const saved = account();
    await boot({ saved, languages: () => reply(200, { ...LANGUAGES, languages: [] }) });
    expect(saved.calls[1]).toEqual(['POST', 'api/chats', { name: 'Chat 1', language: null }]);
    $('language').append(new Option('Retired', 'retired', true, true));
    choose($('language'), '');
    await settle();
    expect(saved.calls.at(-1)).toEqual(['PATCH', 'api/chats/100', { language: null }]);
  });

  it('keeps working in memory when the saved chats cannot be loaded', async () => {
    const saved = account([], (method) => method === 'GET');
    const fetch = await boot({ saved });
    expect(messages()).toEqual([['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO],
      ['msg bot', BOT, 'Could not load your saved chats, so this visit is not being saved.']]);
    await send('+.');
    expect(chatCalls(fetch)).toEqual([{ message: '+.', language: 'bf' }]);
    expect(saved.calls).toEqual([['GET', 'api/chats', undefined]]);
  });

  it('says when a chat cannot be created and keeps it in memory', async () => {
    const saved = account([], (method, url) => method === 'POST' && url === 'api/chats');
    const fetch = await boot({ saved });
    expect(messages()).toEqual([['msg bot', BOT, SAVE_FAILED], ['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO]]);
    choose($('language'), 'kallisti');
    await send('+.');
    expect(chatCalls(fetch)).toEqual([{ message: '+.', language: 'kallisti' }]);
    expect(saved.calls.map(([method, url]) => [method, url])).toEqual([['GET', 'api/chats'], ['POST', 'api/chats']]);
  });

  it('says when a change cannot be saved', async () => {
    const saved = account([{ id: 1, name: 'Chat 1' }, { id: 2, name: 'Chat 2' }], (method) => method !== 'GET');
    await boot({ saved });
    choose($('language'), 'kallisti');
    await settle();
    expect(messages()).toEqual([['msg bot', BOT, SAVE_FAILED]]);
    $('commands').click();
    await settle();
    expect(messages().at(-1)).toEqual(['msg bot', BOT, SAVE_FAILED]);
    closeButton('Chat 1').click();
    await settle();
    expect(messages().at(-1)).toEqual(['msg bot', BOT, SAVE_FAILED]);
    expect(tabs()).toEqual([['Chat 2', 'Kallisti', true]]);
  });
});

describe('clearing a chat', () => {
  const asking = () => !$('clear-confirm').hidden;

  it('asks first, and Yes empties only the open chat', async () => {
    await boot();
    await newChat();
    await send('+.');
    $('message').value = 'unsent';
    $('clear-chat').click();
    expect(asking()).toBe(true);
    expect(document.activeElement).toBe($('clear-no'));
    expect(messages()).toHaveLength(3);
    $('clear-yes').click();
    expect(asking()).toBe(false);
    expect(messages()).toEqual([]);
    expect($('message').value).toBe('unsent');
    expect(document.activeElement).toBe($('message'));
    expect(tabs()).toEqual([['Chat 1', 'Brainfart', false], ['Chat 2', 'Brainfart', true]]);
    tab('Chat 1').click();
    expect(messages()).toEqual([['msg bot', BOT, WELCOME], ['msg bot', BOT, INTRO]]);
  });

  it.each([
    ['No', () => $('clear-no').click()],
    ['Escape', () => $('clear-no').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))],
    ['a click outside the question', () => $('clear-confirm').click()],
  ])('keeps the chat on %s', async (_, answer) => {
    await boot();
    $('clear-chat').click();
    $('clear-no').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    document.querySelector('.confirm-box').click();
    expect(asking()).toBe(true);
    answer();
    expect(asking()).toBe(false);
    expect(document.activeElement).toBe($('clear-chat'));
    expect(messages()).toHaveLength(2);
  });

  it('cannot be used while the chat waits for a reply', async () => {
    let answer;
    await boot({ chat: () => new Promise((resolve) => { answer = resolve; }) });
    await send('+.');
    expect($('clear-chat').disabled).toBe(true);
    await newChat();
    expect($('clear-chat').disabled).toBe(false);
    tab('Chat 1').click();
    expect($('clear-chat').disabled).toBe(true);
    answer(reply(200, { replies: [] }));
    await settle();
    expect($('clear-chat').disabled).toBe(false);
  });

  it('empties the saved chat too, and says when that fails', async () => {
    const saved = account([{ id: 1, name: 'Chat 1', messages: [{ role: 'bot', meta: BOT, content: { type: 'text', text: 'A' } }] }]);
    await boot({ saved });
    $('clear-chat').click();
    $('clear-yes').click();
    await settle();
    expect(saved.calls.at(-1)).toEqual(['DELETE', 'api/chats/1/messages', undefined]);
    expect(saved.chats[0].messages).toEqual([]);
    expect(messages()).toEqual([]);

    const broken = account([{ id: 1, name: 'Chat 1' }], (method) => method === 'DELETE');
    await boot({ saved: broken });
    $('clear-chat').click();
    $('clear-yes').click();
    await settle();
    expect(messages()).toEqual([['msg bot', BOT, SAVE_FAILED]]);
  });

  it('only clears the screen for a chat that could not be saved', async () => {
    const saved = account([], (method, url) => method === 'POST' && url === 'api/chats');
    await boot({ saved });
    $('clear-chat').click();
    $('clear-yes').click();
    await settle();
    expect(messages()).toEqual([]);
    expect(saved.calls.map(([method]) => method)).toEqual(['GET', 'POST']);
  });
});

describe('the portfolio button', () => {
  it('names the portfolio account this browser is logged in to', async () => {
    const fetch = await boot({ portfolio: () => reply(200, { username: 'Gambler' }) });
    expect($('portfolio-button').textContent).toBe('Log in as Gambler');
    expect(fetch).toHaveBeenCalledWith('http://portfolio.test/sso/me', expect.objectContaining({ credentials: 'include' }));
  });

  it.each([
    ['logged out of the portfolio', () => reply(401, {})],
    ['without a name', () => reply(200, { username: null })],
    ['unreachable', () => { throw new TypeError('offline'); }],
  ])('keeps the plain label when the portfolio is %s', async (_, portfolio) => {
    await boot({ portfolio });
    expect($('portfolio-button').textContent).toBe('Log in with portfolio account');
  });

  it('is not there when portfolio login is off', async () => {
    const fetch = await boot();
    expect($('portfolio-button')).toBeNull();
    expect(fetch.mock.calls.map(([url]) => url)).toEqual(['api/languages']);
  });
});
