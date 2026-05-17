(function () {
  var STORAGE_KEY = "admin-shell-theme";

  function applyStoredTheme() {
    try {
      if (localStorage.getItem(STORAGE_KEY) !== "light") {
        document.documentElement.setAttribute("data-theme", "dark");
      } else {
        document.documentElement.removeAttribute("data-theme");
      }
    } catch (e) {}
  }

  function syncThemeToggleButton() {
    var btn = document.getElementById("shell-theme-toggle");
    if (!btn) return;
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    var glyph = btn.querySelector(".theme-toggle-glyph");
    var label = btn.querySelector(".theme-toggle-label");
    btn.setAttribute("aria-pressed", isDark ? "true" : "false");
    btn.setAttribute(
      "aria-label",
      isDark ? "Alternar para tema claro" : "Alternar para tema escuro"
    );
    btn.setAttribute("title", isDark ? "Tema escuro ativo" : "Tema claro ativo");
    if (glyph) glyph.textContent = isDark ? "☀" : "☾";
    if (label) label.textContent = "Tema";
  }

  function toggleTheme() {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    var nextDark = !isDark;
    if (nextDark) {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem(STORAGE_KEY, nextDark ? "dark" : "light");
    } catch (err) {}
    syncThemeToggleButton();
  }

  function bindThemeToggle() {
    var btn = document.getElementById("shell-theme-toggle");
    if (!btn || btn.dataset.themeBound === "1") return;
    btn.dataset.themeBound = "1";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      toggleTheme();
    });
  }

  function initThemeToggle() {
    applyStoredTheme();
    bindThemeToggle();
    syncThemeToggleButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initThemeToggle);
  } else {
    initThemeToggle();
  }

  document.addEventListener("click", function (e) {
    var target = e.target;
    if (!target || !target.closest) return;
    var sidebarToggle = target.closest("[data-sidebar-toggle]");
    if (!sidebarToggle) return;
    if (window.innerWidth <= 980) {
      document.body.classList.toggle("sidebar-open");
      return;
    }
    document.body.classList.toggle("sidebar-collapsed");
  });
})();
