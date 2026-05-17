(function () {
    function readJsonScript(id, fallback) {
        const node = document.getElementById(id);
        if (!node || !node.textContent) {
            return fallback;
        }
        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return fallback;
        }
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (const rawCookie of cookies) {
            const cookie = rawCookie.trim();
            if (cookie.startsWith(name + "=")) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }
        return "";
    }

    const config = readJsonScript("technician-mobile-copilot", {enabled: true, allow_offline_fallback: true});
    if (!config.enabled) {
        return;
    }

    const bootstrap = readJsonScript("technician-copilot-bootstrap", {});
    const tenant = readJsonScript("technician-mobile-tenant", {});
    const endpoints = readJsonScript("technician-mobile-sync-endpoints", {});
    const drawer = document.querySelector("[data-tech-copilot-drawer]");
    const openButtons = document.querySelectorAll("[data-tech-copilot-open]");
    const closeButtons = document.querySelectorAll("[data-tech-copilot-close]");
    const form = document.querySelector("[data-tech-copilot-form]");
    const queryInput = document.querySelector("[data-tech-copilot-query]");
    const messagesRoot = document.querySelector("[data-tech-copilot-messages]");
    const suggestionsRoot = document.querySelector("[data-tech-copilot-suggestions]");
    const statusNode = document.querySelector("[data-tech-copilot-status]");
    const connectivityNode = document.querySelector("[data-tech-copilot-connectivity]");
    const orderNode = document.querySelector("[data-tech-copilot-order]");
    const storageKey = "smart360-tech-copilot:" + (bootstrap && bootstrap.context && bootstrap.context.order_code ? bootstrap.context.order_code : "general");

    if (!drawer || !openButtons.length || !form || !queryInput || !messagesRoot || !suggestionsRoot) {
        return;
    }

    function currentState() {
        try {
            return JSON.parse(window.localStorage.getItem(storageKey) || "{}");
        } catch (error) {
            return {};
        }
    }

    function persistState(nextState) {
        window.localStorage.setItem(storageKey, JSON.stringify(nextState));
    }

    function orderCode() {
        return bootstrap && bootstrap.context ? bootstrap.context.order_code || "" : "";
    }

    function renderMessage(role, content, structuredPayload) {
        const article = document.createElement("article");
        article.className = "technician-copilot-message " + (role === "assistant" ? "is-assistant" : "is-user");
        article.innerHTML = "<strong>" + (role === "assistant" ? "SMART360 Copilot" : "Voce") + "</strong><p></p>";
        article.querySelector("p").textContent = content;
        if (structuredPayload && structuredPayload.bullets && structuredPayload.bullets.length) {
            const list = document.createElement("ul");
            list.className = "technician-copilot-bullets";
            structuredPayload.bullets.forEach(function (item) {
                const li = document.createElement("li");
                li.textContent = item;
                list.appendChild(li);
            });
            article.appendChild(list);
        }
        if (structuredPayload && structuredPayload.steps && structuredPayload.steps.length) {
            const list = document.createElement("ol");
            list.className = "technician-copilot-steps";
            structuredPayload.steps.forEach(function (item) {
                const li = document.createElement("li");
                li.textContent = item;
                list.appendChild(li);
            });
            article.appendChild(list);
        }
        messagesRoot.appendChild(article);
        messagesRoot.scrollTop = messagesRoot.scrollHeight;
    }

    function renderSuggestions(items) {
        suggestionsRoot.innerHTML = "";
        if (!items || !items.length) {
            suggestionsRoot.innerHTML = '<span class="empty-state">Sem sugestoes carregadas.</span>';
            return;
        }
        items.forEach(function (item) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "quick-action-button quick-action-button--ghost";
            button.textContent = item;
            button.addEventListener("click", function () {
                queryInput.value = item;
                form.dispatchEvent(new Event("submit"));
            });
            suggestionsRoot.appendChild(button);
        });
    }

    function renderStoredMessages() {
        const state = currentState();
        const messages = state.messages || [];
        messagesRoot.innerHTML = "";
        if (!messages.length) {
            renderMessage("assistant", "Pergunte sobre historico, diagnostico, checklist, pecas ou como registrar a OS.");
            return;
        }
        messages.forEach(function (item) {
            renderMessage(item.role, item.content, item.structured_payload);
        });
    }

    function mergeState(patch) {
        const state = currentState();
        const nextState = {
            ...state,
            ...patch,
        };
        persistState(nextState);
        return nextState;
    }

    function appendStoredMessage(message) {
        const state = currentState();
        const messages = (state.messages || []).concat([message]).slice(-12);
        persistState({
            ...state,
            messages: messages,
            context: state.context || (bootstrap.context || {}),
        });
        renderStoredMessages();
    }

    function openDrawer() {
        drawer.hidden = false;
        document.body.classList.add("technician-copilot-open");
        renderStoredMessages();
        renderSuggestions((currentState().suggestions || bootstrap.suggestions || []));
    }

    function closeDrawer() {
        drawer.hidden = true;
        document.body.classList.remove("technician-copilot-open");
    }

    function setConnectivityStatus() {
        const offline = !navigator.onLine;
        if (statusNode) {
            statusNode.textContent = offline ? "Modo offline com contexto local" : "Contexto sincronizado";
        }
        if (connectivityNode) {
            connectivityNode.textContent = offline ? "Offline" : "Online";
        }
        if (orderNode) {
            orderNode.textContent = orderCode() ? "OS " + orderCode() : "Sem OS ativa";
        }
    }

    async function syncOfflineConversation() {
        const state = currentState();
        if (!navigator.onLine || !endpoints.copilot_sync || !state.messages || !state.messages.length || !orderCode()) {
            return;
        }
        const offlineMessages = state.messages.filter(function (item) {
            return item.offline === true;
        });
        if (!offlineMessages.length) {
            return;
        }
        try {
            await fetch(endpoints.copilot_sync, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({
                    order_code: orderCode(),
                    context: state.context || bootstrap.context || {},
                    messages: offlineMessages,
                }),
            });
            const syncedMessages = (state.messages || []).map(function (item) {
                return {...item, offline: false};
            });
            persistState({...state, messages: syncedMessages});
        } catch (error) {
            return;
        }
    }

    function offlineResponse(query) {
        const context = (currentState().context || bootstrap.context || {});
        const lower = (query || "").toLowerCase();
        const bullets = [];
        if (lower.includes("historico") || lower.includes("problema")) {
            (context.recent_failures || []).slice(0, 3).forEach(function (item) {
                bullets.push(item.summary);
            });
        }
        if (lower.includes("checklist") || lower.includes("nok")) {
            if (typeof context.checklist_nok_count === "number") {
                bullets.push("Itens NOK atuais: " + context.checklist_nok_count);
            }
            if (typeof context.checklist_pending_count === "number") {
                bullets.push("Itens pendentes: " + context.checklist_pending_count);
            }
        }
        if (lower.includes("peca") || lower.includes("componente")) {
            (bootstrap.recommended_parts || []).slice(0, 3).forEach(function (item) {
                bullets.push(item.code + " - " + item.name + ": " + item.reason);
            });
        }
        if (!bullets.length) {
            bullets.push("Usando contexto local salvo da OS atual.");
            bullets.push("Confirme sintoma, checklist e ultimo diagnostico antes de concluir.");
        }
        return {
            response_type: "offline_fallback",
            summary: "Resposta local gerada com o ultimo contexto sincronizado da OS.",
            bullets: bullets,
            steps: ["Continue registrando a execucao.", "Sincronize quando a conexao voltar."],
            quick_suggestions: bootstrap.suggestions || [],
            offline: true,
        };
    }

    async function sendQuery(query) {
        if (!query) {
            return;
        }
        appendStoredMessage({role: "user", content: query, structured_payload: null, offline: !navigator.onLine});
        queryInput.value = "";
        if (!navigator.onLine || !endpoints.copilot_query) {
            const response = offlineResponse(query);
            mergeState({
                context: bootstrap.context || {},
                suggestions: response.quick_suggestions || bootstrap.suggestions || [],
            });
            appendStoredMessage({role: "assistant", content: response.summary, structured_payload: response, offline: true});
            return;
        }
        if (statusNode) {
            statusNode.textContent = "Consultando contexto tecnico...";
        }
        try {
            const response = await fetch(endpoints.copilot_query, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({
                    order_code: orderCode(),
                    query: query,
                    offline: false,
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Falha ao consultar o copiloto.");
            }
            mergeState({
                session_public_id: data.session_public_id,
                context: data.context,
                suggestions: data.response.quick_suggestions || bootstrap.suggestions || [],
            });
            appendStoredMessage({role: "assistant", content: data.response.summary, structured_payload: data.response, offline: false});
            renderSuggestions(data.response.quick_suggestions || bootstrap.suggestions || []);
        } catch (error) {
            const fallback = offlineResponse(query);
            appendStoredMessage({role: "assistant", content: fallback.summary, structured_payload: fallback, offline: true});
        } finally {
            setConnectivityStatus();
        }
    }

    openButtons.forEach(function (button) {
        button.addEventListener("click", openDrawer);
    });
    closeButtons.forEach(function (button) {
        button.addEventListener("click", closeDrawer);
    });
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        sendQuery(queryInput.value.trim());
    });

    mergeState({
        context: bootstrap.context || {},
        suggestions: bootstrap.suggestions || [],
    });
    renderSuggestions(bootstrap.suggestions || []);
    renderStoredMessages();
    setConnectivityStatus();
    window.addEventListener("online", function () {
        setConnectivityStatus();
        syncOfflineConversation();
    });
    window.addEventListener("offline", setConnectivityStatus);
})();
