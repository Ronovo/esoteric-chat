import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE = readFileSync(join(ROOT, 'esoteric_chat', 'templates', 'index.html'), 'utf8');
const LANGUAGES = {
  prefix: '$',
  echo_language: 'kallisti',
  languages: [
    {
      id: 'bf', name: 'Brainfart', intro: 'Brainfart - the safe-for-work one', info_url: 'https://esolangs.org/wiki/brainfuck',
      examples: [{ label: 'Print A', code: '+.' }, { label: '$hi', code: '$hi' }],
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

afterEach(() => {
  vi.unstubAllGlobals();
});

function reply(status, body) {
  return { ok: status >= 200 && status < 300, status, statusText: 'status', json: async () => body };
}

/* The page as Flask renders it, with the portfolio button only when portfolioUrl is given. */
function render(portfolioUrl) {
  const body = TEMPLATE.slice(TEMPLATE.indexOf('<body>') + 6, TEMPLATE.indexOf('<script'));
  document.body.innerHTML = body.replace(/{% if portfolio_user %}[\s\S]*?{% elif portfolio %}([\s\S]*?){% endif %}/,
    (_, button) => (portfolioUrl ? button.replace('{{ portfolio_url }}', portfolioUrl) : ''));
}

async function settle() {
  for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

async function boot({ languages = () => reply(200, LANGUAGES), chat = () => reply(200, { replies: [] }), portfolio } = {}) {
  render(portfolio && 'http://portfolio.test');
  const fetch = vi.fn(async (url, options) => {
    if (url === 'api/languages') return languages();
    if (url === 'api/chat') return chat(JSON.parse(options.body));
    return portfolio();
  });
  vi.stubGlobal('fetch', fetch);
  vi.resetModules();
  await import('../../esoteric_chat/static/app.js');
  await settle();
  return fetch;
}

const $ = (id) => document.getElementById(id);
const messages = () => [...document.querySelectorAll('.msg')].map((m) => [m.className, m.querySelector('.meta').textContent,
  m.lastElementChild.textContent]);

async function send(text) {
  $('message').value = text;
  $('composer').requestSubmit();
  await settle();
}

function choose(select, value) {
  select.value = value;
  select.dispatchEvent(new Event('change'));
}

describe('starting up', () => {
  it('lists the languages, picks the first and greets', async () => {
    await boot();
    expect([...$('language').options].map((o) => o.value)).toEqual(['bf', 'kallisti']);
    expect($('explained').href).toBe('https://esolangs.org/wiki/brainfuck');
    expect([...$('example').options].map((o) => o.textContent)).toEqual(['Try example', 'Print A', '$hi']);
    expect(messages()).toEqual([
      ['msg bot', 'Esoteric Chat', 'Welcome! Pick a language, write some code and hit Send.'],
      ['msg bot', 'Esoteric Chat', 'Brainfart - the safe-for-work one'],
    ]);
    expect(document.activeElement).toBe($('message'));
  });

  it('still greets when the server lists no languages', async () => {
    await boot({ languages: () => reply(200, { ...LANGUAGES, languages: [] }) });
    expect($('explained').hasAttribute('href')).toBe(false);
    expect([...$('example').options].map((o) => o.textContent)).toEqual(['Try example']);
    expect(messages()).toEqual([['msg bot', 'Esoteric Chat', 'Welcome! Pick a language, write some code and hit Send.']]);
  });

  it.each([
    ['the server refuses', () => reply(503, {})],
    ['the server is down', () => { throw new TypeError('offline'); }],
  ])('says when the languages cannot be loaded because %s', async (_, languages) => {
    await boot({ languages });
    expect(messages()).toEqual([['msg bot', 'Esoteric Chat', 'Could not load languages.']]);
    $('commands').click();
    expect(messages()).toHaveLength(1);
  });
});

describe('picking a language', () => {
  it('updates the link and examples, and shows an intro only when there is one', async () => {
    await boot();
    choose($('language'), 'kallisti');
    expect($('explained').href).toBe('https://esolangs.org/wiki/Kallisti');
    expect([...$('example').options].map((o) => o.textContent)).toEqual(['Try example']);
    expect(messages()).toHaveLength(2);
    choose($('language'), 'bf');
    expect(messages().at(-1)[2]).toBe('Brainfart - the safe-for-work one');
  });

  it('puts an example in the message box', async () => {
    await boot();
    choose($('example'), '1');
    expect($('message').value).toBe('$hi');
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
      ['msg bot', 'Esoteric Chat', 'A'],
      ['msg bot', 'Esoteric Chat', '(no output)'],
      ['msg bot', 'Esoteric Chat', 'Invalid Brainfart Command: unmatched'],
    ]);
    expect([...document.querySelectorAll('.bubble')].slice(-2).map((b) => b.className)).toEqual(['bubble empty', 'bubble error']);
    expect($('message').value).toBe('');
    expect($('send').disabled).toBe(false);
  });

  it('labels commands, except in the language that echoes them', async () => {
    await boot();
    await send('  $ping');
    choose($('language'), 'kallisti');
    await send('$ping');
    expect(messages().filter((m) => m[0] === 'msg user').map((m) => m[1])).toEqual(['command', 'Kallisti']);
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
    expect(messages().at(-1)).toEqual(['msg bot', 'Esoteric Chat', text]);
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
    expect(fetch.mock.calls.filter(([url]) => url === 'api/chat')).toHaveLength(1);
  });

  it('sends on Enter and adds a line on Shift+Enter', async () => {
    const fetch = await boot();
    $('message').value = '+.';
    const shifted = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true });
    $('message').dispatchEvent(shifted);
    expect(shifted.defaultPrevented).toBe(false);
    $('message').dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    expect(fetch.mock.calls.filter(([url]) => url === 'api/chat')).toHaveLength(0);
    $('message').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
    await settle();
    expect(fetch.mock.calls.filter(([url]) => url === 'api/chat')).toHaveLength(1);
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
