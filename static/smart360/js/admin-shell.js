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

  /**
   * Preserva scrollTop da sidebar entre navegações (sessionStorage).
   */
  function initSidebarScrollPersistence() {
    var sidebar = document.querySelector("[data-admin-shell-sidebar-scroll]");
    if (!sidebar) return;

    var storageKey = "smart360.adminShell.sidebar.scrollTop";
    var scrollSaveTimer = null;

    try {
      var saved = sessionStorage.getItem(storageKey);
      if (saved !== null) {
        var y = parseInt(saved, 10);
        if (!isNaN(y) && y >= 0) {
          function applyScrollTop() {
            var max = Math.max(0, sidebar.scrollHeight - sidebar.clientHeight);
            sidebar.scrollTop = Math.min(y, max);
          }
          applyScrollTop();
          requestAnimationFrame(applyScrollTop);
        }
      }

      function persistScroll() {
        try {
          sessionStorage.setItem(storageKey, String(sidebar.scrollTop));
        } catch (err) {}
      }

      sidebar.addEventListener(
        "scroll",
        function () {
          if (scrollSaveTimer) window.clearTimeout(scrollSaveTimer);
          scrollSaveTimer = window.setTimeout(persistScroll, 100);
        },
        { passive: true }
      );

      var links = sidebar.querySelectorAll("a[href]");
      for (var i = 0; i < links.length; i++) {
        links[i].addEventListener("click", persistScroll);
      }
    } catch (e) {
      /* sessionStorage indisponível — não bloquear UI */
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSidebarScrollPersistence);
  } else {
    initSidebarScrollPersistence();
  }

  function initSidebarAccordion() {
    var sidebar = document.querySelector("[data-sidebar]");
    if (!sidebar || sidebar.dataset.accordionBound === "1") return;

    sidebar.dataset.accordionBound = "1";

    var triggers = sidebar.querySelectorAll("[data-nav-accordion-trigger]");

    function setExpanded(trigger, expanded) {
      var panelId = trigger.getAttribute("aria-controls");
      var panel = panelId ? document.getElementById(panelId) : null;

      trigger.setAttribute("aria-expanded", expanded ? "true" : "false");

      if (panel) {
        if (expanded) {
          panel.classList.add("is-expanded");
        } else {
          panel.classList.remove("is-expanded");
        }
      }
    }

    for (var i = 0; i < triggers.length; i++) {
      triggers[i].addEventListener("click", function (e) {
        e.preventDefault();

        var trigger = e.currentTarget;
        var willExpand = trigger.getAttribute("aria-expanded") !== "true";
        var section = trigger.closest(".nav-section");

        if (section) {
          var sectionTriggers = section.querySelectorAll("[data-nav-accordion-trigger]");
          for (var j = 0; j < sectionTriggers.length; j++) {
            if (sectionTriggers[j] !== trigger) {
              setExpanded(sectionTriggers[j], false);
            }
          }
        }

        setExpanded(trigger, willExpand);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSidebarAccordion);
  } else {
    initSidebarAccordion();
  }

})();
