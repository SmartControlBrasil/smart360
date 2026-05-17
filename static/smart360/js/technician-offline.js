(function () {
    const DB_NAME = "smart360-technician-offline";
    const DB_VERSION = 1;
    const STORE_BUNDLES = "serviceBundles";
    const STORE_DRAFTS = "serviceDrafts";
    const STORE_QUEUE = "pendingOps";
    const STORE_META = "syncMeta";
    const APP_VERSION = "technician-pwa-offline-v1";
    const ACTION_SEQUENCE = {
        start_execution: 10,
        save_execution: 20,
        save_checklist: 30,
        save_materials: 40,
        upload_evidence: 50,
        capture_signature: 60,
        complete_execution: 70,
    };

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

    function openDatabase() {
        return new Promise((resolve, reject) => {
            const request = window.indexedDB.open(DB_NAME, DB_VERSION);
            request.onerror = () => reject(request.error);
            request.onupgradeneeded = function () {
                const db = request.result;
                if (!db.objectStoreNames.contains(STORE_BUNDLES)) {
                    db.createObjectStore(STORE_BUNDLES, {keyPath: "scopeKey"});
                }
                if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
                    const store = db.createObjectStore(STORE_DRAFTS, {keyPath: "draftKey"});
                    store.createIndex("byOrderCode", "orderCode", {unique: false});
                }
                if (!db.objectStoreNames.contains(STORE_QUEUE)) {
                    const store = db.createObjectStore(STORE_QUEUE, {keyPath: "operationId"});
                    store.createIndex("byScopeKey", "scopeKey", {unique: false});
                    store.createIndex("byOrderCode", "orderCode", {unique: false});
                }
                if (!db.objectStoreNames.contains(STORE_META)) {
                    db.createObjectStore(STORE_META, {keyPath: "key"});
                }
            };
            request.onsuccess = () => resolve(request.result);
        });
    }

    async function withStore(storeName, mode, callback) {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, mode);
            const store = transaction.objectStore(storeName);
            let callbackResult;
            try {
                callbackResult = callback(store, transaction);
            } catch (error) {
                reject(error);
                return;
            }
            transaction.oncomplete = () => resolve(callbackResult);
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async function idbGet(storeName, key) {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, "readonly");
            const request = transaction.objectStore(storeName).get(key);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function idbGetAll(storeName) {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, "readonly");
            const request = transaction.objectStore(storeName).getAll();
            request.onsuccess = () => resolve(request.result || []);
            request.onerror = () => reject(request.error);
        });
    }

    async function idbPut(storeName, value) {
        return withStore(storeName, "readwrite", function (store) {
            store.put(value);
        });
    }

    async function idbDelete(storeName, key) {
        return withStore(storeName, "readwrite", function (store) {
            store.delete(key);
        });
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function randomId() {
        return Math.random().toString(36).slice(2, 10);
    }

    function scopeKey(user, tenant) {
        const companyId = tenant && tenant.company ? tenant.company.id : "all-companies";
        const siteId = tenant && tenant.site ? tenant.site.id : "all-sites";
        return [user && user.id ? user.id : "anon", companyId, siteId].join(":");
    }

    const bootstrap = readJsonScript("technician-offline-bootstrap", {});
    const mobileUser = readJsonScript("technician-mobile-user", {});
    const mobileTenant = readJsonScript("technician-mobile-tenant", {});
    const syncEndpoints = readJsonScript("technician-mobile-sync-endpoints", {});
    const currentScopeKey = scopeKey(mobileUser, mobileTenant);
    const deviceIdKey = "smart360-technician-device-id";
    let deviceId = window.localStorage.getItem(deviceIdKey);
    if (!deviceId) {
        deviceId = "device-" + randomId();
        window.localStorage.setItem(deviceIdKey, deviceId);
    }
    let syncInFlight = false;

    async function persistBootstrap() {
        const existing = (await idbGet(STORE_BUNDLES, currentScopeKey)) || {
            scopeKey: currentScopeKey,
            services: [],
            serviceDetails: [],
            checklists: [],
            history: [],
            generatedAt: "",
        };
        if (bootstrap.screen === "services" && bootstrap.services) {
            existing.services = bootstrap.services;
        } else if (bootstrap.screen === "service_detail" && bootstrap.service) {
            existing.services = upsertService(existing.services || [], bootstrap.service);
            existing.serviceDetails = upsertServiceDetail(existing.serviceDetails || [], bootstrap);
        } else if (bootstrap.screen === "execution" && bootstrap.service) {
            existing.services = upsertService(existing.services || [], bootstrap.service);
            existing.serviceDetails = upsertServiceDetail(existing.serviceDetails || [], bootstrap);
        } else if (bootstrap.screen === "checklists") {
            existing.checklists = bootstrap.checklists || [];
        } else if (bootstrap.screen === "history") {
            existing.history = bootstrap.history || [];
        }
        existing.generatedAt = nowIso();
        await idbPut(STORE_BUNDLES, existing);
    }

    function upsertService(services, service) {
        const next = (services || []).filter((item) => item.code !== service.code);
        next.unshift(service);
        return next;
    }

    function upsertServiceDetail(details, payload) {
        const next = (details || []).filter((item) => item.service.code !== payload.service.code);
        next.unshift(payload);
        return next;
    }

    function updateConnectivityBanner() {
        const banner = document.querySelector("[data-connection-banner]");
        const stateLabel = document.querySelector("[data-offline-state-label]");
        if (!banner || !stateLabel) {
            return;
        }
        if (navigator.onLine) {
            banner.hidden = true;
            stateLabel.textContent = syncInFlight ? "Sincronizando" : "Online";
        } else {
            banner.hidden = false;
            stateLabel.textContent = "Offline";
        }
    }

    async function getPendingOperations(includeConflicts) {
        const all = await idbGetAll(STORE_QUEUE);
        return all
            .filter((item) => item.scopeKey === currentScopeKey && (includeConflicts ? true : item.status !== "conflict"))
            .sort((left, right) => {
                const sequenceDelta = (left.sequence || 999) - (right.sequence || 999);
                if (sequenceDelta !== 0) {
                    return sequenceDelta;
                }
                return String(left.recordedAt).localeCompare(String(right.recordedAt));
            });
    }

    async function getDraft(orderCode) {
        return idbGet(STORE_DRAFTS, currentScopeKey + ":" + orderCode);
    }

    async function saveDraft(orderCode, draft) {
        const existing = (await getDraft(orderCode)) || {};
        await idbPut(STORE_DRAFTS, {
            draftKey: currentScopeKey + ":" + orderCode,
            scopeKey: currentScopeKey,
            orderCode: orderCode,
            draft: {
                ...(existing.draft || {}),
                ...draft,
            },
            updatedAt: nowIso(),
        });
        await updateOrderPendingPills(orderCode);
    }

    async function replaceQueueOperation(action, orderCode, payload, replaceKey) {
        const pending = await getPendingOperations(false);
        for (const operation of pending) {
            if (
                operation.orderCode === orderCode &&
                (operation.replaceKey || operation.action) === (replaceKey || action) &&
                operation.status === "pending"
            ) {
                await idbDelete(STORE_QUEUE, operation.operationId);
            }
        }
        const operation = {
            operationId: [orderCode, action, Date.now(), randomId()].join(":"),
            scopeKey: currentScopeKey,
            orderCode: orderCode,
            action: action,
            replaceKey: replaceKey || action,
            sequence: ACTION_SEQUENCE[action] || 999,
            recordedAt: nowIso(),
            deviceId: deviceId,
            appVersion: APP_VERSION,
            status: "pending",
            attempts: 0,
            payload: payload,
        };
        await idbPut(STORE_QUEUE, operation);
        await setMeta("lastPendingAt", nowIso());
        await updateSyncStateUI();
        return operation;
    }

    async function enqueueSignature(form) {
        const orderCode = currentOrderCode();
        if (!orderCode) {
            return;
        }
        const signatureKind = form.dataset.signatureKind || "technician";
        const payload = {
            signatureKind: signatureKind,
            signerName: valueOf(form, "signer_name"),
            signerTitle: valueOf(form, "signer_title"),
            signerDocument: valueOf(form, "signer_document"),
            signatureData: valueOf(form, "signature_data"),
            acceptanceNotes: valueOf(form, "acceptance_notes"),
            missingReason: valueOf(form, "missing_reason"),
            missingReasonNotes: valueOf(form, "missing_reason_notes"),
            recordedAt: nowIso(),
        };
        await replaceQueueOperation("capture_signature", orderCode, payload, "capture_signature:" + signatureKind);
        await saveDraft(orderCode, {
            signatures: {
                ...(await currentDraftSignatures(orderCode)),
                [signatureKind]: payload,
            },
        });
    }

    async function currentDraftSignatures(orderCode) {
        const draft = await getDraft(orderCode);
        return (draft && draft.draft && draft.draft.signatures) || {};
    }

    function valueOf(form, name) {
        const field = form.querySelector('[name="' + name + '"]');
        return field ? field.value : "";
    }

    function currentOrderCode() {
        const form = document.querySelector("[data-execution-form]");
        if (form) {
            return form.dataset.orderCode;
        }
        const startForm = document.querySelector('[data-offline-form="start_execution"]');
        if (startForm) {
            return startForm.dataset.orderCode;
        }
        const bootstrapService = bootstrap.service;
        return bootstrapService ? bootstrapService.code : "";
    }

    function serializeChecklist() {
        const items = Array.from(document.querySelectorAll("[data-checklist-item]")).map(function (item, index) {
            const checked = item.querySelector('input[type="radio"]:checked');
            const notes = item.querySelector("[data-checklist-notes]");
            return {
                code: item.dataset.itemCode || "item-" + index,
                order: index + 1,
                title: item.querySelector("strong") ? item.querySelector("strong").textContent.trim() : "",
                response: checked ? checked.value : "",
                notes: notes ? notes.value : "",
            };
        });
        const responded = items.filter((item) => item.response).length;
        const okCount = items.filter((item) => item.response === "OK").length;
        const nokCount = items.filter((item) => item.response === "NOK").length;
        const naCount = items.filter((item) => item.response === "N/A").length;
        const total = items.length;
        return {
            items: items,
            total_items: total,
            responded_count: responded,
            pending_count: Math.max(total - responded, 0),
            ok_count: okCount,
            nok_count: nokCount,
            na_count: naCount,
            progress: total ? Math.round((responded / total) * 100) : 0,
        };
    }

    function serializeMaterials() {
        return Array.from(document.querySelectorAll("[data-material-item]")).map(function (item) {
            return {
                code: (item.querySelector("[data-material-code]") || {}).value || "",
                name: (item.querySelector("[data-material-name]") || {}).value || "",
                quantity: (item.querySelector("[data-material-quantity]") || {}).value || "",
                notes: (item.querySelector("[data-material-notes]") || {}).value || "",
            };
        }).filter(function (item) {
            return item.code || item.name || item.quantity || item.notes;
        });
    }

    function serializeEvidenceCards() {
        return Array.from(document.querySelectorAll("[data-evidence-item]")).map(function (item) {
            return {
                type: (item.querySelector("[data-evidence-type]") || {}).value || "Foto",
                description: (item.querySelector("[data-evidence-description]") || {}).value || "",
                timestamp: (item.querySelector("span") || {}).textContent || "",
                localOnly: true,
            };
        }).filter(function (item) {
            return item.description || item.type;
        });
    }

    function serializeExecutionDraft() {
        const form = document.querySelector("[data-execution-form]");
        if (!form) {
            return {};
        }
        const checklist = serializeChecklist();
        const progress = Math.max(
            checklist.progress,
            document.querySelector('[name="technical_diagnosis"]') && document.querySelector('[name="technical_diagnosis"]').value ? 55 : 0
        );
        return {
            recordedAt: nowIso(),
            progress: progress,
            executionStatus: document.querySelector('[name="final_status"]') ? document.querySelector('[name="final_status"]').value : "Em execucao",
            checklist: checklist,
            diagnosis: {
                symptoms: valueByName("symptoms"),
                technical_diagnosis: valueByName("technical_diagnosis"),
                analysis: valueByName("analysis"),
            },
            executedAction: {
                intervention: valueByName("intervention"),
                adjustments: valueByName("adjustments"),
                result: valueByName("result"),
            },
            materials: serializeMaterials(),
            evidence: serializeEvidenceCards(),
            finalization: {
                finalStatus: valueByName("final_status"),
                recommendation: valueByName("recommendation"),
                finalNotes: valueByName("final_notes"),
            },
        };
    }

    function valueByName(name) {
        const field = document.querySelector('[name="' + name + '"]');
        return field ? field.value : "";
    }

    async function queueExecutionSave() {
        const orderCode = currentOrderCode();
        if (!orderCode) {
            return;
        }
        const draft = serializeExecutionDraft();
        await saveDraft(orderCode, draft);
        await replaceQueueOperation("save_checklist", orderCode, {
            recordedAt: draft.recordedAt,
            checklist: draft.checklist,
            progress: draft.progress,
        });
        await replaceQueueOperation("save_execution", orderCode, draft);
    }

    async function queueExecutionCompletion() {
        const orderCode = currentOrderCode();
        if (!orderCode) {
            return;
        }
        const draft = serializeExecutionDraft();
        await saveDraft(orderCode, draft);
        await replaceQueueOperation("save_execution", orderCode, draft);
        await replaceQueueOperation("complete_execution", orderCode, {
            recordedAt: nowIso(),
            completedAt: nowIso(),
            finalization: draft.finalization,
        });
    }

    async function processQueue() {
        if (!navigator.onLine || syncInFlight) {
            return;
        }
        const operations = await getPendingOperations();
        if (!operations.length || !syncEndpoints.sync) {
            await updateSyncStateUI();
            return;
        }
        syncInFlight = true;
        updateConnectivityBanner();
        try {
            const response = await fetch(syncEndpoints.sync, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({operations: operations}),
            });
            const data = await response.json();
            const results = data.processed || [];
            for (const result of results) {
                const existing = operations.find((item) => item.operationId === result.operation_id);
                if (!existing) {
                    continue;
                }
                if (result.status === "processed") {
                    await idbDelete(STORE_QUEUE, existing.operationId);
                    if (existing.orderCode && result.snapshot_state) {
                        const draft = await getDraft(existing.orderCode);
                        if (draft) {
                            draft.draft = {
                                ...(draft.draft || {}),
                                sync: {
                                    state: result.snapshot_state,
                                    lastServerSyncAt: nowIso(),
                                },
                            };
                            await idbPut(STORE_DRAFTS, draft);
                        }
                    }
                } else {
                    await idbPut(STORE_QUEUE, {
                        ...existing,
                        status: result.status,
                        error: result.message,
                        conflictCode: result.conflict_code || "",
                        lastAttemptAt: nowIso(),
                    });
                }
            }
            await setMeta("lastSuccessfulSyncAt", nowIso());
        } catch (error) {
            await setMeta("lastSyncError", String(error));
        } finally {
            syncInFlight = false;
            updateConnectivityBanner();
            await updateSyncStateUI();
        }
    }

    async function fetchOfflineBundle() {
        if (!navigator.onLine || !syncEndpoints.bundle) {
            return;
        }
        try {
            const response = await fetch(syncEndpoints.bundle, {credentials: "same-origin"});
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            await idbPut(STORE_BUNDLES, {
                scopeKey: currentScopeKey,
                ...payload,
                generatedAt: nowIso(),
            });
            await setMeta("lastBundleSyncAt", nowIso());
        } catch (error) {
            await setMeta("lastBundleError", String(error));
        }
    }

    async function setMeta(key, value) {
        await idbPut(STORE_META, {key: currentScopeKey + ":" + key, value: value});
    }

    async function getMeta(key) {
        const payload = await idbGet(STORE_META, currentScopeKey + ":" + key);
        return payload ? payload.value : "";
    }

    async function updateSyncStateUI() {
        const pending = await getPendingOperations(false);
        const allQueue = await getPendingOperations(true);
        const errors = allQueue.filter((item) => item.status === "error" || item.status === "conflict");
        const pendingCountNode = document.querySelector("[data-sync-pending-count]");
        if (pendingCountNode) {
            pendingCountNode.textContent = String(pending.length);
        }
        const summaryPending = document.querySelector("[data-sync-summary-pending]");
        if (summaryPending) {
            summaryPending.textContent = String(pending.length);
        }
        const summaryErrors = document.querySelector("[data-sync-summary-errors]");
        if (summaryErrors) {
            summaryErrors.textContent = String(errors.length);
        }
        const lastSync = await getMeta("lastSuccessfulSyncAt");
        const lastSyncNode = document.querySelector("[data-sync-summary-last-sync]");
        if (lastSyncNode) {
            lastSyncNode.textContent = lastSync ? new Date(lastSync).toLocaleTimeString("pt-BR") : "--";
        }
        renderSyncQueue(allQueue, pending);
        await updateOrderPendingPills(currentOrderCode());
    }

    async function updateOrderPendingPills(orderCode) {
        if (!orderCode) {
            return;
        }
        const pending = await getPendingOperations(false);
        const orderPending = pending.filter((item) => item.orderCode === orderCode);
        const pendingNode = document.querySelector("[data-order-pending-summary]");
        if (pendingNode) {
            pendingNode.textContent = "Pendencias locais: " + orderPending.length;
        }
        const syncStateNode = document.querySelector("[data-order-sync-state]");
        if (syncStateNode) {
            const draft = await getDraft(orderCode);
            const state = draft && draft.draft && draft.draft.sync && draft.draft.sync.state ? draft.draft.sync.state : (orderPending.length ? "local_pending" : "synced");
            syncStateNode.textContent = state;
        }
    }

    function renderSyncQueue(queue, pendingQueue) {
        const queueRoot = document.querySelector("[data-sync-queue-list]");
        if (queueRoot) {
            if (!pendingQueue.length) {
                queueRoot.innerHTML = '<p class="empty-state">Nenhuma pendencia local identificada.</p>';
            } else {
                queueRoot.innerHTML = pendingQueue.map(function (item) {
                    return '<article class="technician-mini-card">' +
                        '<strong>' + escapeHtml(item.orderCode) + " • " + escapeHtml(item.action) + '</strong>' +
                        '<p>' + escapeHtml(item.status || "pending") + '</p>' +
                        '<span>' + escapeHtml(item.error || item.recordedAt || "") + '</span>' +
                        '</article>';
                }).join("");
            }
        }
        const conflictRoot = document.querySelector("[data-sync-conflict-list]");
        if (conflictRoot) {
            const conflicts = queue.filter((item) => item.status === "conflict" || item.status === "error");
            if (!conflicts.length) {
                conflictRoot.innerHTML = '<p class="empty-state">Nenhum conflito registrado.</p>';
            } else {
                conflictRoot.innerHTML = conflicts.map(function (item) {
                    return '<article class="stack-card tone-critical"><strong>' +
                        escapeHtml(item.orderCode) + '</strong><p>' + escapeHtml(item.error || "Conflito de sincronizacao") + '</p></article>';
                }).join("");
            }
        }
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
    }

    async function hydrateExecutionDraft() {
        const orderCode = currentOrderCode();
        const form = document.querySelector("[data-execution-form]");
        if (!orderCode || !form) {
            return;
        }
        const draftRecord = await getDraft(orderCode);
        const draft = draftRecord && draftRecord.draft ? draftRecord.draft : {};
        if (draft.diagnosis) {
            assignValue("symptoms", draft.diagnosis.symptoms);
            assignValue("technical_diagnosis", draft.diagnosis.technical_diagnosis);
            assignValue("analysis", draft.diagnosis.analysis);
        }
        if (draft.executedAction) {
            assignValue("intervention", draft.executedAction.intervention);
            assignValue("adjustments", draft.executedAction.adjustments);
            assignValue("result", draft.executedAction.result);
        }
        if (draft.finalization) {
            assignValue("final_status", draft.finalization.finalStatus);
            assignValue("recommendation", draft.finalization.recommendation);
            assignValue("final_notes", draft.finalization.finalNotes);
        }
        if (draft.checklist && Array.isArray(draft.checklist.items)) {
            draft.checklist.items.forEach(function (item) {
                const node = document.querySelector('[data-item-code="' + item.code + '"]');
                if (!node) {
                    return;
                }
                const radio = node.querySelector('input[type="radio"][value="' + item.response + '"]');
                if (radio) {
                    radio.checked = true;
                }
                const notes = node.querySelector("[data-checklist-notes]");
                if (notes) {
                    notes.value = item.notes || "";
                }
            });
        }
        if (draft.materials && draft.materials.length) {
            const root = document.querySelector("[data-material-list]");
            if (root) {
                root.innerHTML = "";
                draft.materials.forEach(function (material) {
                    root.appendChild(buildMaterialCard(material));
                });
            }
        }
        if (draft.evidence && draft.evidence.length) {
            const root = document.querySelector("[data-evidence-list]");
            if (root) {
                root.innerHTML = "";
                draft.evidence.forEach(function (evidence) {
                    root.appendChild(buildEvidenceCard(evidence));
                });
            }
        }
        await updateOrderPendingPills(orderCode);
    }

    function assignValue(name, value) {
        const field = document.querySelector('[name="' + name + '"]');
        if (field && value !== undefined && value !== null) {
            field.value = value;
        }
    }

    function buildMaterialCard(material) {
        const article = document.createElement("article");
        article.className = "technician-mini-card technician-material-editor";
        article.dataset.materialItem = "1";
        article.innerHTML = '' +
            '<input type="text" placeholder="Codigo da peca" data-material-code>' +
            '<input type="text" placeholder="Descricao" data-material-name>' +
            '<input type="text" placeholder="Quantidade" data-material-quantity>' +
            '<textarea rows="2" placeholder="Observacao" data-material-notes></textarea>';
        article.querySelector("[data-material-code]").value = material.code || "";
        article.querySelector("[data-material-name]").value = material.name || "";
        article.querySelector("[data-material-quantity]").value = material.quantity || "";
        article.querySelector("[data-material-notes]").value = material.notes || "";
        return article;
    }

    function buildEvidenceCard(evidence) {
        const article = document.createElement("article");
        article.className = "technician-mini-card technician-evidence-editor";
        article.dataset.evidenceItem = "1";
        article.innerHTML = '' +
            '<input type="text" placeholder="Tipo" data-evidence-type>' +
            '<textarea rows="2" placeholder="Descricao" data-evidence-description></textarea>' +
            '<span></span>';
        article.querySelector("[data-evidence-type]").value = evidence.type || "Foto";
        article.querySelector("[data-evidence-description]").value = evidence.description || "";
        article.querySelector("span").textContent = evidence.timestamp || "offline";
        return article;
    }

    function bindExecutionForm() {
        const executionForm = document.querySelector("[data-execution-form]");
        if (!executionForm) {
            return;
        }
        executionForm.addEventListener("input", async function () {
            const orderCode = currentOrderCode();
            if (!orderCode) {
                return;
            }
            await saveDraft(orderCode, serializeExecutionDraft());
        });
        const addMaterial = document.querySelector("[data-add-material]");
        if (addMaterial) {
            addMaterial.addEventListener("click", function () {
                const root = document.querySelector("[data-material-list]");
                if (root) {
                    root.appendChild(buildMaterialCard({}));
                }
            });
        }
        const fileInput = document.querySelector("[data-evidence-file-input]");
        if (fileInput) {
            fileInput.addEventListener("change", function (event) {
                const file = event.target.files && event.target.files[0];
                if (!file) {
                    return;
                }
                const reader = new FileReader();
                reader.onload = async function () {
                    const root = document.querySelector("[data-evidence-list]");
                    const evidence = {
                        type: "Foto",
                        description: file.name,
                        timestamp: "aguardando sync",
                        dataUrl: reader.result,
                        filename: file.name,
                    };
                    if (root) {
                        root.appendChild(buildEvidenceCard(evidence));
                    }
                    const orderCode = currentOrderCode();
                    const currentDraft = serializeExecutionDraft();
                    currentDraft.evidence = currentDraft.evidence.concat([evidence]);
                    await saveDraft(orderCode, currentDraft);
                    await replaceQueueOperation("upload_evidence", orderCode, {
                        evidences: currentDraft.evidence.filter((item) => item.dataUrl),
                        recordedAt: nowIso(),
                    });
                };
                reader.readAsDataURL(file);
            });
        }
        const saveButton = document.querySelector("[data-execution-save]");
        if (saveButton) {
            saveButton.addEventListener("click", async function () {
                await queueExecutionSave();
                await processQueue();
            });
        }
        const syncButton = document.querySelector("[data-execution-sync-now]");
        if (syncButton) {
            syncButton.addEventListener("click", async function () {
                await queueExecutionSave();
                await processQueue();
            });
        }
        const completeButton = document.querySelector("[data-execution-complete]");
        if (completeButton) {
            completeButton.addEventListener("click", async function () {
                await queueExecutionCompletion();
                await processQueue();
                if (navigator.onLine) {
                    window.location.href = "/field/services/" + currentOrderCode() + "/";
                }
            });
        }
    }

    function bindOfflineForms() {
        document.querySelectorAll("[data-offline-form]").forEach(function (form) {
            form.addEventListener("submit", async function (event) {
                event.preventDefault();
                const type = form.dataset.offlineForm;
                const orderCode = form.dataset.orderCode || currentOrderCode();
                if (type === "start_execution") {
                    await replaceQueueOperation("start_execution", orderCode, {
                        startedAt: nowIso(),
                        progress: 5,
                        recordedAt: nowIso(),
                    });
                    await processQueue();
                    window.location.href = "/field/services/" + orderCode + "/execute/";
                    return;
                }
                if (type === "capture_signature") {
                    await enqueueSignature(form);
                    await processQueue();
                    if (navigator.onLine) {
                        window.location.reload();
                    }
                }
            });
        });
    }

    function bindSyncCenter() {
        const syncNow = document.querySelector("[data-sync-now]");
        if (syncNow) {
            syncNow.addEventListener("click", async function () {
                await processQueue();
            });
        }
        const refreshBundle = document.querySelector("[data-refresh-offline-bundle]");
        if (refreshBundle) {
            refreshBundle.addEventListener("click", async function () {
                await fetchOfflineBundle();
                await updateSyncStateUI();
            });
        }
    }

    async function initialize() {
        try {
            await persistBootstrap();
            await fetchOfflineBundle();
            await hydrateExecutionDraft();
            bindOfflineForms();
            bindExecutionForm();
            bindSyncCenter();
            updateConnectivityBanner();
            await updateSyncStateUI();
            window.addEventListener("online", async function () {
                updateConnectivityBanner();
                await processQueue();
            });
            window.addEventListener("offline", function () {
                updateConnectivityBanner();
            });
            setInterval(processQueue, 30000);
        } catch (error) {
            console.error("SMART360 technician offline init failed", error);
        }
    }

    if (window.indexedDB) {
        initialize();
    }
})();
