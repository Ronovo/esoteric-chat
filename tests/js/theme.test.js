import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const root = document.documentElement;
const PICKER = '<select data-theme-picker><option value="esoteric">Esoteric</option>'
  + '<option value="chalkboard">Chalkboard</option><option value="light">Light</option></select>';
const listeners = [];

/* Every listener the script adds to window is removed after each test, so one test's page cannot answer the next
   test's events. */
beforeEach(() => {
  const listen = window.addEventListener;
  vi.spyOn(window, 'addEventListener').mockImplementation(function track(type, listener, options) {
    listeners.push([type, listener, options]);
    return listen.call(this, type, listener, options);
  });
});

afterEach(() => {
  for (const [type, listener, options] of listeners.splice(0)) window.removeEventListener(type, listener, options);
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  delete document.startViewTransition;
  for (const name of ['theme', 'accountTheme', 'loggedIn']) delete root.dataset[name];
  root.style.cssText = '';
  document.body.innerHTML = '';
});

const theme = () => root.dataset.theme;
const select = () => document.querySelector('select');

/* As on the real page: the script runs in <head>, before the picker exists, with the attributes Flask put on
   <html>. */
async function load({ saved, account = '', loggedIn = false } = {}) {
  if (saved) localStorage.setItem('theme', saved);
  root.dataset.theme = account || 'esoteric';
  root.dataset.accountTheme = account;
  root.dataset.loggedIn = loggedIn ? '1' : '';
  vi.resetModules();
  await import('../../esoteric_chat/static/theme.js');
  document.body.innerHTML = PICKER;
  document.dispatchEvent(new Event('DOMContentLoaded', { bubbles: true }));
}

function pick(value) {
  select().value = value;
  select().dispatchEvent(new Event('change'));
}

describe('on load', () => {
  it('starts on Esoteric when nothing is saved', async () => {
    await load();
    expect([theme(), select().value]).toEqual(['esoteric', 'esoteric']);
  });

  it("uses this browser's saved theme and shows it in the picker", async () => {
    await load({ saved: 'chalkboard' });
    expect([theme(), select().value]).toEqual(['chalkboard', 'chalkboard']);
  });

  it('falls back to Esoteric when the saved theme is no longer offered', async () => {
    await load({ saved: 'hud' });
    expect([theme(), select().value]).toEqual(['esoteric', 'esoteric']);
  });

  it("prefers the account's theme and copies it to this browser", async () => {
    await load({ saved: 'chalkboard', account: 'light', loggedIn: true });
    expect([theme(), select().value, localStorage.getItem('theme')]).toEqual(['light', 'light', 'light']);
  });
});

describe('picking a theme', () => {
  it('saves it in this browser only when logged out', async () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    await load();
    pick('chalkboard');
    expect([theme(), localStorage.getItem('theme')]).toEqual(['chalkboard', 'chalkboard']);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('also saves it to the account when logged in', async () => {
    const fetch = vi.fn(async () => ({ ok: true, status: 204 }));
    vi.stubGlobal('fetch', fetch);
    await load({ loggedIn: true });
    pick('light');
    expect(fetch).toHaveBeenCalledWith('api/theme', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: '{"theme":"light"}',
    });
    expect([theme(), localStorage.getItem('theme')]).toEqual(['light', 'light']);
  });

  it('keeps the theme on this device when the account cannot be reached', async () => {
    const fetch = vi.fn(() => Promise.reject(new TypeError('offline')));
    vi.stubGlobal('fetch', fetch);
    await load({ loggedIn: true });
    pick('chalkboard');
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect([theme(), localStorage.getItem('theme')]).toEqual(['chalkboard', 'chalkboard']);
  });

  it('wipes the new theme in from the picker', async () => {
    document.startViewTransition = vi.fn((update) => update());
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })));
    await load();
    vi.spyOn(select(), 'getBoundingClientRect').mockReturnValue({ left: 100, top: 20, width: 80, height: 30 });
    pick('chalkboard');
    expect(document.startViewTransition).toHaveBeenCalledTimes(1);
    expect([root.style.getPropertyValue('--wipe-x'), root.style.getPropertyValue('--wipe-y')]).toEqual(['140px', '35px']);
    expect(theme()).toBe('chalkboard');
  });

  it('switches at once when the reader asks for reduced motion', async () => {
    document.startViewTransition = vi.fn();
    vi.stubGlobal('matchMedia', vi.fn((query) => ({ matches: query === '(prefers-reduced-motion: reduce)' })));
    await load();
    pick('light');
    expect(document.startViewTransition).not.toHaveBeenCalled();
    expect(theme()).toBe('light');
  });

  it('still works when the browser blocks storage', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
    await load();
    expect(theme()).toBe('esoteric');
    pick('light');
    expect(theme()).toBe('light');
  });
});

describe('other tabs', () => {
  it('follow a theme picked in another tab', async () => {
    await load();
    window.dispatchEvent(new StorageEvent('storage', { key: 'theme', newValue: 'chalkboard' }));
    expect([theme(), select().value]).toEqual(['chalkboard', 'chalkboard']);
    window.dispatchEvent(new StorageEvent('storage', { key: 'other', newValue: 'light' }));
    expect(theme()).toBe('chalkboard');
    window.dispatchEvent(new StorageEvent('storage', { key: 'theme', newValue: null }));
    expect(theme()).toBe('esoteric');
  });
});
