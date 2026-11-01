// Loaded in <head>, so the saved theme is on <html> before the first paint.
(() => {
  const root = document.documentElement;
  const KEY = "theme";
  const DEFAULT = "esoteric";
  const loggedIn = root.dataset.loggedIn === "1";
  const read = () => {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  };
  const write = (value) => {
    try {
      localStorage.setItem(KEY, value);
    } catch {}
  };
  const pickers = () => document.querySelectorAll("select[data-theme-picker]");
  const known = (theme) => [...pickers()].every((picker) => picker.querySelector(`option[value="${theme}"]`));
  const show = (theme) => {
    if (!known(theme)) theme = DEFAULT;
    root.dataset.theme = theme;
    for (const picker of pickers()) picker.value = theme;
  };

  // The theme saved to the portfolio account wins over this browser's, so a new device starts on it.
  const account = root.dataset.accountTheme;
  if (account) write(account);
  show(account || read() || DEFAULT);

  const set = (theme, from) => {
    write(theme);
    if (loggedIn) {
      fetch("api/theme", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme }),
      }).catch(() => {});
    }
    if (!document.startViewTransition || matchMedia("(prefers-reduced-motion: reduce)").matches) {
      show(theme);
      return;
    }
    const box = from.getBoundingClientRect();
    root.style.setProperty("--wipe-x", `${box.left + box.width / 2}px`);
    root.style.setProperty("--wipe-y", `${box.top + box.height / 2}px`);
    document.startViewTransition(() => show(theme));
  };

  // Keeps every open tab on the same theme.
  addEventListener("storage", (event) => {
    if (event.key === KEY) show(event.newValue || DEFAULT);
  });

  // The picker arrives after this script ran, so the theme is checked against it here too.
  addEventListener("DOMContentLoaded", () => {
    show(root.dataset.theme);
    for (const picker of pickers()) picker.addEventListener("change", () => set(picker.value, picker));
  });
})();
