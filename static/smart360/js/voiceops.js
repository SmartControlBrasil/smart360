(function () {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#39;");
    }

    function readBootstrap(id) {
        const node = document.getElementById(id);
        if (!node || !node.textContent) {
            return null;
        }
        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return null;
        }
    }

    function appendResponse(feed, payload, action) {
        if (!feed) {
            return;
        }
        const bullets = Array.isArray(payload.bullets) ? payload.bullets : [];
        const bulletMarkup = bullets.length
            ? `<ul class="copilot-inline-list">${bullets.map(function (item) { return `<li>${escapeHtml(item)}</li>`; }).join("")}</ul>`
            : "";
        const article = document.createElement("article");
        article.className = "event-row tone-neutral";
        article.innerHTML = `
            <strong>${escapeHtml(payload.summary || "VoiceOps")}</strong>
            ${bulletMarkup}
            <small>${escapeHtml((action && action.status) || "response_only")}</small>
        `;
        feed.prepend(article);
    }

    function speak(text) {
        if (!text || !window.speechSynthesis) {
            return;
        }
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "pt-BR";
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    function initWidget(root) {
        const configId = root.getAttribute("data-voiceops-config-id");
        const config = readBootstrap(configId);
        if (!config) {
            return;
        }
        const transcriptField = root.querySelector("[data-voiceops-transcript]");
        const recordButton = root.querySelector("[data-voiceops-record]");
        const stopButton = root.querySelector("[data-voiceops-stop]");
        const sendButton = root.querySelector("[data-voiceops-send]");
        const statusNode = root.querySelector("[data-voiceops-status]");
        const ttsCheckbox = root.querySelector("[data-voiceops-tts]");
        const feed = root.querySelector("[data-voiceops-response-feed]");
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;

        async function processTranscript() {
            const transcript = (transcriptField.value || "").trim();
            if (!transcript) {
                return;
            }
            statusNode.textContent = "Processando comando de voz...";
            sendButton.disabled = true;
            const response = await fetch(config.processUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    persona: config.persona,
                    channel: config.channel,
                    input_mode: transcriptField.dataset.voiceopsAudioUsed === "true" ? "hybrid" : "text",
                    transcript_text: transcript,
                    audio_metadata: {
                        provider: transcriptField.dataset.voiceopsAudioUsed === "true" ? "browser_speech_recognition" : "manual",
                        browser_transcript: transcript,
                    },
                    context_seed: config.contextSeed || {},
                }),
            });
            sendButton.disabled = false;
            if (!response.ok) {
                statusNode.textContent = "Falha ao processar o comando.";
                return;
            }
            const data = await response.json();
            statusNode.textContent = "Comando processado";
            appendResponse(feed, data.response || {}, data.action || {});
            if (ttsCheckbox && ttsCheckbox.checked && data.response && data.response.tts && data.response.tts.enabled) {
                speak(data.response.tts.text || data.response.summary);
            }
            if (data.action && data.action.status === "executed" && config.refreshOnSuccess) {
                window.setTimeout(function () {
                    window.location.reload();
                }, 800);
            }
        }

        if (Recognition) {
            recognition = new Recognition();
            recognition.lang = config.locale || "pt-BR";
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;
            recognition.onstart = function () {
                statusNode.textContent = "Ouvindo...";
                stopButton.hidden = false;
                transcriptField.dataset.voiceopsAudioUsed = "true";
            };
            recognition.onresult = function (event) {
                let text = "";
                for (let i = event.resultIndex; i < event.results.length; i += 1) {
                    text += event.results[i][0].transcript + " ";
                }
                transcriptField.value = text.trim();
            };
            recognition.onerror = function () {
                statusNode.textContent = "Nao foi possivel transcrever no navegador.";
                stopButton.hidden = true;
            };
            recognition.onend = function () {
                statusNode.textContent = "Pronto para ouvir";
                stopButton.hidden = true;
            };
        } else {
            statusNode.textContent = "Seu navegador nao oferece STT nativo. Digite ou use outro browser.";
            if (recordButton) {
                recordButton.disabled = true;
            }
        }

        if (recordButton) {
            recordButton.addEventListener("click", function () {
                if (recognition) {
                    recognition.start();
                }
            });
        }
        if (stopButton) {
            stopButton.addEventListener("click", function () {
                if (recognition) {
                    recognition.stop();
                }
            });
        }
        if (sendButton) {
            sendButton.addEventListener("click", processTranscript);
        }
    }

    document.querySelectorAll("[data-voiceops][data-voiceops-config-id]").forEach(initWidget);
})();
