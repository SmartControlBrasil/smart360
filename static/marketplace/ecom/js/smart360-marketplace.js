(function () {
    "use strict";

    var STORAGE_KEY = "marketplace-theme";

    function getRoot() {
        return document.documentElement;
    }

    function applyTheme(theme) {
        var root = getRoot();
        var isDark = theme === "dark";
        root.setAttribute("data-marketplace-theme", isDark ? "dark" : "light");

        document.querySelectorAll("[data-marketplace-theme-toggle]").forEach(function (button) {
            button.setAttribute("aria-label", isDark ? "Ativar modo claro" : "Ativar modo escuro");
            button.setAttribute("title", isDark ? "Modo claro" : "Modo escuro");
            button.setAttribute("aria-pressed", isDark ? "true" : "false");

            var label = button.querySelector(".marketplace-theme-toggle__label");
            if (label) {
                label.textContent = isDark ? "Modo claro" : "Modo escuro";
            }

            var icon = button.querySelector(".marketplace-theme-toggle__icon");
            if (icon) {
                icon.textContent = isDark ? "☀" : "☾";
            }
        });
    }

    function readStoredTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function storeTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (error) {
            /* ignore quota / private mode */
        }
    }

    function initTheme() {
        var stored = readStoredTheme();
        applyTheme(stored === "dark" ? "dark" : "light");
    }

    function toggleTheme() {
        var root = getRoot();
        var current = root.getAttribute("data-marketplace-theme") === "dark" ? "dark" : "light";
        var next = current === "dark" ? "light" : "dark";
        applyTheme(next);
        storeTheme(next);
    }

    function isMarketplacePath(pathname) {
        return pathname === "/marketplace" || pathname.indexOf("/marketplace/") === 0;
    }

    function initBackLink() {
        var links = document.querySelectorAll(".marketplace-back-link, #marketplace-back-to-site");
        if (!links.length) {
            return;
        }

        var fallback = "/";
        var first = links[0];
        if (first) {
            fallback = first.getAttribute("data-fallback-href") || "/";
        }

        var targetHref = fallback;
        var referrer = document.referrer;
        if (referrer) {
            try {
                var refUrl = new URL(referrer);
                var currentUrl = new URL(window.location.href);
                if (refUrl.origin === currentUrl.origin && !isMarketplacePath(refUrl.pathname)) {
                    targetHref = refUrl.pathname + refUrl.search + refUrl.hash;
                }
            } catch (error) {
                targetHref = fallback;
            }
        }

        links.forEach(function (link) {
            link.setAttribute("href", targetHref);
        });
    }

    function bindThemeButtons() {
        document.querySelectorAll("[data-marketplace-theme-toggle]").forEach(function (button) {
            button.addEventListener("click", function (event) {
                event.preventDefault();
                toggleTheme();
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initTheme();
        initBackLink();
        bindThemeButtons();
    });
})();
