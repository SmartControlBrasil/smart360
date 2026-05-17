(function () {
    const form = document.getElementById("client-portal-copilot-form");
    const queryInput = document.getElementById("client-portal-copilot-query");
    const submitButton = document.getElementById("client-portal-copilot-submit");
    const statusEl = document.getElementById("client-portal-copilot-status");
    const conversationEl = document.getElementById("client-portal-copilot-conversation");
    const bootstrapEl = document.getElementById("client-portal-copilot-bootstrap");

    if (!form || !queryInput || !submitButton || !statusEl || !conversationEl || !bootstrapEl) {
        return;
    }

    const bootstrap = JSON.parse(bootstrapEl.textContent || "{}");
    const suggestions = document.querySelectorAll(".client-portal-copilot-suggestion");

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#39;");
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function appendMessage(author, content, bullets) {
        const article = document.createElement("article");
        article.className = `copilot-message copilot-message--${author === "Cliente" ? "user" : "assistant"}`;
        const bulletMarkup = Array.isArray(bullets) && bullets.length
            ? `<ul class="copilot-inline-list">${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
            : "";
        article.innerHTML = `
            <header><strong>${escapeHtml(author)}</strong></header>
            <p>${escapeHtml(content)}</p>
            ${bulletMarkup}
        `;
        conversationEl.appendChild(article);
        conversationEl.scrollTop = conversationEl.scrollHeight;
    }

    async function sendQuery(query) {
        if (!query) {
            return;
        }
        appendMessage("Cliente", query, []);
        statusEl.hidden = false;
        statusEl.textContent = "Consultando contexto seguro do portal...";
        submitButton.disabled = true;
        queryInput.disabled = true;

        const response = await fetch(bootstrap.queryUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify({
                query: query,
                session_public_id: bootstrap.sessionPublicId,
                context_seed: bootstrap.seedContext || {},
            }),
        });

        submitButton.disabled = false;
        queryInput.disabled = false;
        statusEl.hidden = true;

        if (!response.ok) {
            statusEl.hidden = false;
            statusEl.textContent = "Nao foi possivel consultar o copiloto agora.";
            return;
        }

        const data = await response.json();
        bootstrap.sessionPublicId = data.session.public_id;
        appendMessage("SMART360 Portal Copilot", data.response.summary, data.response.bullets || []);
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        const query = queryInput.value.trim();
        if (!query) {
            return;
        }
        queryInput.value = "";
        sendQuery(query);
    });

    suggestions.forEach(function (button) {
        button.addEventListener("click", function () {
            const query = button.getAttribute("data-query") || "";
            if (!query) {
                return;
            }
            queryInput.value = query;
            sendQuery(query);
        });
    });

    if (queryInput.value.trim()) {
        const initialQuery = queryInput.value.trim();
        queryInput.value = "";
        sendQuery(initialQuery);
    }
})();
