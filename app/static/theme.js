// Light / dark toggle shared by both pages. Runs in <head> so the saved theme applies
// before first paint. No saved choice = follow the system setting.
(function () {
  const KEY = "firstslip-theme";
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked: follow the system */ }
  if (saved === "light" || saved === "dark") root.dataset.theme = saved;

  const current = () => root.dataset.theme ||
    (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

  function sync() {
    const t = current();
    document.querySelectorAll(".seg [data-set-theme]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.setTheme === t)));
    // MathLive's on-screen keyboard follows a class on <body>.
    if (document.body) document.body.classList.toggle("theme-dark", t === "dark");
  }

  window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".seg [data-set-theme]").forEach((b) => b.addEventListener("click", () => {
      root.dataset.theme = b.dataset.setTheme;
      try { localStorage.setItem(KEY, b.dataset.setTheme); } catch (e) { /* not remembered */ }
      sync();
    }));
    if (window.matchMedia) matchMedia("(prefers-color-scheme: dark)").addEventListener("change", sync);
    sync();
  });
})();
