(() => {
  const ARTWORK_EDITOR_STORAGE_KEY = "caneca-garagem-artwork-editor-project-v1";
  const ARTWORK_EDITOR_FILE_VERSION = 1;

  const ARTWORK_EDITOR_PRODUCT_GUIDES = {
    mug: {
      label: "Caneca",
      width: 1200,
      height: 800,
      safeMarginX: 120,
      safeMarginY: 100,
      centerLine: true,
    },
    longDrink: {
      label: "Long Drink",
      width: 900,
      height: 1600,
      safeMarginX: 100,
      safeMarginY: 160,
      centerLine: true,
    },
    cap: {
      label: "Boné",
      width: 900,
      height: 500,
      safeMarginX: 180,
      safeMarginY: 100,
      centerLine: true,
    },
  };

  const ARTWORK_EDITOR_TEMPLATES = {
    mug: [
      {
        key: "mug-photo-title",
        label: "Foto + título",
        objects: [
          { type: "textbox", text: "MINHA CANECA", leftPct: 0.5, topPct: 0.13, widthPct: 0.72, fill: "#111827", fontSize: 72, fontWeight: "800", textAlign: "center" },
          { type: "rect", leftPct: 0.5, topPct: 0.48, widthPct: 0.5, heightPct: 0.42, fill: "rgba(255,255,255,0.76)", stroke: "#1f5fbf", strokeWidth: 5, rx: 22, ry: 22 },
          { type: "textbox", text: "Sua foto aqui", leftPct: 0.5, topPct: 0.48, widthPct: 0.38, fill: "#1f5fbf", fontSize: 48, fontWeight: "800", textAlign: "center" },
          { type: "textbox", text: "Feita na Caneca de Garagem", leftPct: 0.5, topPct: 0.82, widthPct: 0.68, fill: "#374151", fontSize: 34, fontWeight: "700", textAlign: "center" },
        ],
      },
      {
        key: "mug-center-logo",
        label: "Logo central",
        objects: [
          { type: "circle", leftPct: 0.5, topPct: 0.42, radiusPct: 0.18, fill: "#f0b429", stroke: "#111827", strokeWidth: 6 },
          { type: "textbox", text: "LOGO", leftPct: 0.5, topPct: 0.42, widthPct: 0.36, fill: "#111827", fontSize: 84, fontWeight: "900", textAlign: "center" },
          { type: "textbox", text: "Sua marca aqui", leftPct: 0.5, topPct: 0.68, widthPct: 0.58, fill: "#111827", fontSize: 42, fontWeight: "700", textAlign: "center" },
        ],
      },
      {
        key: "mug-phrase",
        label: "Frase grande",
        objects: [
          { type: "textbox", text: "CAFÉ,\nCORAGEM\nE GARAGEM", leftPct: 0.5, topPct: 0.42, widthPct: 0.72, fill: "#111827", fontSize: 72, fontWeight: "900", textAlign: "center" },
          { type: "rect", leftPct: 0.5, topPct: 0.76, widthPct: 0.38, heightPct: 0.05, fill: "#f0b429", rx: 18, ry: 18 },
          { type: "textbox", text: "assine aqui", leftPct: 0.5, topPct: 0.86, widthPct: 0.48, fill: "#374151", fontSize: 30, fontWeight: "700", textAlign: "center" },
        ],
      },
    ],
    longDrink: [
      {
        key: "longdrink-vertical-logo",
        label: "Logo vertical",
        objects: [
          { type: "rect", leftPct: 0.5, topPct: 0.42, widthPct: 0.44, heightPct: 0.42, fill: "rgba(255,255,255,0.72)", stroke: "#1f5fbf", strokeWidth: 5, rx: 28, ry: 28 },
          { type: "textbox", text: "LOGO\nAQUI", leftPct: 0.5, topPct: 0.42, widthPct: 0.34, fill: "#1f5fbf", fontSize: 76, fontWeight: "900", textAlign: "center" },
          { type: "textbox", text: "Long Drink personalizado", leftPct: 0.5, topPct: 0.72, widthPct: 0.56, fill: "#111827", fontSize: 42, fontWeight: "700", textAlign: "center" },
        ],
      },
      {
        key: "longdrink-party",
        label: "Festa",
        objects: [
          { type: "circle", leftPct: 0.24, topPct: 0.2, radiusPct: 0.06, fill: "#f0b429", opacity: 0.85 },
          { type: "circle", leftPct: 0.78, topPct: 0.33, radiusPct: 0.05, fill: "#1f5fbf", opacity: 0.8 },
          { type: "circle", leftPct: 0.28, topPct: 0.72, radiusPct: 0.04, fill: "#ef4444", opacity: 0.8 },
          { type: "textbox", text: "BRINDE\nESPECIAL", leftPct: 0.5, topPct: 0.46, widthPct: 0.62, fill: "#111827", fontSize: 88, fontWeight: "900", textAlign: "center" },
          { type: "textbox", text: "nome do evento", leftPct: 0.5, topPct: 0.68, widthPct: 0.54, fill: "#374151", fontSize: 38, fontWeight: "700", textAlign: "center" },
        ],
      },
    ],
    cap: [
      {
        key: "cap-front-logo",
        label: "Logo frontal",
        objects: [
          { type: "rect", leftPct: 0.5, topPct: 0.5, widthPct: 0.36, heightPct: 0.44, fill: "rgba(255,255,255,0.76)", stroke: "#111827", strokeWidth: 4, rx: 18, ry: 18 },
          { type: "textbox", text: "LOGO", leftPct: 0.5, topPct: 0.5, widthPct: 0.28, fill: "#111827", fontSize: 54, fontWeight: "900", textAlign: "center" },
        ],
      },
    ],
  };

  const editorCanvasElement = document.getElementById("artwork-editor-canvas");
  const widthInput = document.getElementById("artwork-editor-width");
  const heightInput = document.getElementById("artwork-editor-height");
  const imageInput = document.getElementById("artwork-editor-image-input");
  const addImageButton = document.getElementById("artwork-editor-add-image");
  const textInput = document.getElementById("artwork-editor-text-input");
  const fontSizeInput = document.getElementById("artwork-editor-font-size");
  const textColorInput = document.getElementById("artwork-editor-text-color");
  const currentProductLabel = document.getElementById("artwork-editor-current-product");
  const productSelector = document.getElementById("artwork-editor-product-selector");
  const templateSelect = document.getElementById("artwork-editor-template-select");
  const applyTemplateButton = document.getElementById("artwork-editor-apply-template");
  const toggleGuidesButton = document.getElementById("artwork-editor-toggle-guides");
  const addTextButton = document.getElementById("artwork-editor-add-text");
  const duplicateButton = document.getElementById("artwork-editor-duplicate");
  const centerButton = document.getElementById("artwork-editor-center");
  const bringForwardButton = document.getElementById("artwork-editor-bring-forward");
  const sendBackwardButton = document.getElementById("artwork-editor-send-backward");
  const removeSelectedButton = document.getElementById("artwork-editor-remove-selected");
  const clearButton = document.getElementById("artwork-editor-clear");
  const applyButton = document.getElementById("artwork-editor-apply");
  const saveLocalButton = document.getElementById("artwork-editor-save-local");
  const loadLocalButton = document.getElementById("artwork-editor-load-local");
  const downloadJsonButton = document.getElementById("artwork-editor-download-json");
  const importJsonButton = document.getElementById("artwork-editor-import-json");
  const importJsonInput = document.getElementById("artwork-editor-import-json-file");
  const downloadPngButton = document.getElementById("artwork-editor-download-png");
  const statusElement = document.getElementById("artwork-editor-status");
  const objectXInput = document.getElementById("artwork-editor-object-x");
  const objectYInput = document.getElementById("artwork-editor-object-y");
  const objectWidthInput = document.getElementById("artwork-editor-object-width");
  const objectHeightInput = document.getElementById("artwork-editor-object-height");
  const objectAngleInput = document.getElementById("artwork-editor-object-angle");
  const lockObjectButton = document.getElementById("artwork-editor-lock-object");
  const selectionStatusElement = document.getElementById("artwork-editor-selection-status");

  if (!editorCanvasElement) {
    return;
  }

  function setEditorStatus(message, type = "info") {
    if (!statusElement) {
      const logger = type === "error" ? console.error : type === "warning" ? console.warn : console.info;
      logger("[artwork-editor-2d]", message);
      return;
    }

    statusElement.textContent = message;
    statusElement.dataset.status = type;
  }

  function updateEditorStatus(message, state = "info") {
    setEditorStatus(message, state === "idle" ? "info" : state);
  }

  if (!window.fabric) {
    setEditorStatus("Fabric.js não carregou", "error");
    return;
  }

  const artworkCanvas = new window.fabric.Canvas(editorCanvasElement, {
    backgroundColor: null,
    preserveObjectStacking: true,
    selection: true,
  });
  let guideObjects = [];
  let guidesVisible = true;
  let currentProductGuideKey = "mug";
  let isUpdatingObjectProperties = false;

  function clampCanvasSize(value, fallback) {
    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return fallback;
    }

    return Math.min(Math.max(Math.round(numberValue), 200), 4000);
  }

  function clampFontSize(value) {
    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return 72;
    }

    return Math.min(Math.max(Math.round(numberValue), 8), 300);
  }

  function getGuideConfig(productKey = currentProductGuideKey) {
    return ARTWORK_EDITOR_PRODUCT_GUIDES[productKey] || ARTWORK_EDITOR_PRODUCT_GUIDES.mug;
  }

  function getUserObjects() {
    return artworkCanvas.getObjects().filter((object) => !object.isGuide);
  }

  function getActiveObject() {
    return artworkCanvas.getActiveObject();
  }

  function getActiveUserObject() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      return null;
    }

    return activeObject;
  }

  function getObjectTypeLabel(object) {
    if (!object) {
      return "Nenhum objeto selecionado";
    }

    if (object.type === "activeSelection") {
      return "Seleção";
    }

    if (object.type === "i-text" || object.type === "textbox" || object.type === "text") {
      return "Texto";
    }

    if (object.type === "image") {
      return "Imagem";
    }

    return "Objeto";
  }

  function getPropertyInputs() {
    return [objectXInput, objectYInput, objectWidthInput, objectHeightInput, objectAngleInput].filter(Boolean);
  }

  function setPropertyInputsDisabled(disabled, { disableSize = false } = {}) {
    getPropertyInputs().forEach((input) => {
      input.disabled = disabled;
    });

    if (objectWidthInput) {
      objectWidthInput.disabled = disabled || disableSize;
    }

    if (objectHeightInput) {
      objectHeightInput.disabled = disabled || disableSize;
    }

    if (lockObjectButton) {
      lockObjectButton.disabled = disabled;
    }
  }

  function updateObjectPropertiesPanel() {
    const object = getActiveUserObject();
    isUpdatingObjectProperties = true;

    if (!object) {
      setPropertyInputsDisabled(true);
      getPropertyInputs().forEach((input) => {
        input.value = "";
      });

      if (selectionStatusElement) {
        selectionStatusElement.textContent = "Nenhum objeto selecionado";
      }

      if (lockObjectButton) {
        lockObjectButton.setAttribute("aria-pressed", "false");
      }

      isUpdatingObjectProperties = false;
      return;
    }

    const isSelection = object.type === "activeSelection";
    setPropertyInputsDisabled(false, { disableSize: isSelection });

    if (objectXInput) {
      objectXInput.value = Math.round(object.left ?? 0);
    }

    if (objectYInput) {
      objectYInput.value = Math.round(object.top ?? 0);
    }

    if (objectWidthInput) {
      objectWidthInput.value = Math.round(object.getScaledWidth());
    }

    if (objectHeightInput) {
      objectHeightInput.value = Math.round(object.getScaledHeight());
    }

    if (objectAngleInput) {
      objectAngleInput.value = Math.round(object.angle || 0);
    }

    if (selectionStatusElement) {
      selectionStatusElement.textContent = getObjectTypeLabel(object);
    }

    if (lockObjectButton) {
      const isLocked = Boolean(object.isArtworkLocked);
      lockObjectButton.setAttribute("aria-pressed", String(isLocked));
      setButtonAccessibleLabel(lockObjectButton, isLocked ? "Desbloquear objeto" : "Bloquear objeto");
    }

    isUpdatingObjectProperties = false;
  }

  function setObjectScaledDimension(object, dimension, value) {
    const desiredSize = Number(value);

    if (!Number.isFinite(desiredSize) || desiredSize <= 0) {
      return;
    }

    const baseSize = dimension === "width" ? object.width : object.height;

    if (!baseSize) {
      return;
    }

    if (dimension === "width") {
      object.scaleX = desiredSize / baseSize;
    } else {
      object.scaleY = desiredSize / baseSize;
    }
  }

  function applyObjectPropertyChange() {
    if (isUpdatingObjectProperties) {
      return;
    }

    const object = getActiveUserObject();

    if (!object) {
      return;
    }

    if (objectXInput && objectXInput.value !== "") {
      object.left = Number(objectXInput.value);
    }

    if (objectYInput && objectYInput.value !== "") {
      object.top = Number(objectYInput.value);
    }

    if (object.type !== "activeSelection") {
      if (objectWidthInput && objectWidthInput.value !== "") {
        setObjectScaledDimension(object, "width", objectWidthInput.value);
      }

      if (objectHeightInput && objectHeightInput.value !== "") {
        setObjectScaledDimension(object, "height", objectHeightInput.value);
      }
    }

    if (objectAngleInput && objectAngleInput.value !== "") {
      object.angle = Number(objectAngleInput.value);
    }

    object.setCoords();
    artworkCanvas.requestRenderAll();
    updateObjectPropertiesPanel();
  }

  function setObjectLockState(object, isLocked) {
    object.isArtworkLocked = isLocked;
    object.lockMovementX = isLocked;
    object.lockMovementY = isLocked;
    object.lockScalingX = isLocked;
    object.lockScalingY = isLocked;
    object.lockRotation = isLocked;
    object.hasControls = !isLocked;
  }

  function toggleLockSelectedObject() {
    const object = getActiveUserObject();

    if (!object) {
      return;
    }

    setObjectLockState(object, !object.isArtworkLocked);
    object.setCoords();
    artworkCanvas.requestRenderAll();
    updateObjectPropertiesPanel();
    updateEditorStatus(object.isArtworkLocked ? "Objeto bloqueado" : "Objeto desbloqueado", "success");
  }

  function updateCanvasAndSelection(object) {
    if (object) {
      object.setCoords();
      artworkCanvas.setActiveObject(object);
    }

    artworkCanvas.requestRenderAll();
    updateObjectPropertiesPanel();
  }

  function setButtonAccessibleLabel(button, label) {
    if (!button) {
      return;
    }

    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);

    const srText = button.querySelector(".visual-3d-sr-only");
    if (srText) {
      srText.textContent = label;
    }
  }

  function markGuideObject(object) {
    object.set({
      selectable: false,
      evented: false,
      excludeFromExport: true,
      visible: guidesVisible,
    });
    object.isGuide = true;
    return object;
  }

  function clearGuideObjects() {
    guideObjects.forEach((object) => artworkCanvas.remove(object));
    guideObjects = [];
  }

  function addGuideObject(object) {
    const guideObject = markGuideObject(object);
    guideObjects.push(guideObject);
    artworkCanvas.add(guideObject);
    return guideObject;
  }

  function drawGuideObjects(config = getGuideConfig()) {
    const width = artworkCanvas.getWidth();
    const height = artworkCanvas.getHeight();
    const safeMarginX = Math.min(config.safeMarginX ?? 0, width / 2 - 1);
    const safeMarginY = Math.min(config.safeMarginY ?? 0, height / 2 - 1);
    const safeWidth = Math.max(width - safeMarginX * 2, 1);
    const safeHeight = Math.max(height - safeMarginY * 2, 1);

    clearGuideObjects();

    addGuideObject(new window.fabric.Rect({
      left: 0,
      top: 0,
      width,
      height,
      fill: "rgba(255, 255, 255, 0)",
      stroke: "rgba(31, 95, 191, 0.45)",
      strokeDashArray: [14, 8],
      strokeWidth: 3,
    }));

    addGuideObject(new window.fabric.Rect({
      left: safeMarginX,
      top: safeMarginY,
      width: safeWidth,
      height: safeHeight,
      fill: "rgba(240, 180, 41, 0.08)",
      stroke: "rgba(154, 95, 0, 0.75)",
      strokeDashArray: [16, 8],
      strokeWidth: 3,
    }));

    if (config.centerLine) {
      addGuideObject(new window.fabric.Line([width / 2, 0, width / 2, height], {
        stroke: "rgba(31, 95, 191, 0.48)",
        strokeDashArray: [8, 10],
        strokeWidth: 2,
      }));
      addGuideObject(new window.fabric.Line([0, height / 2, width, height / 2], {
        stroke: "rgba(31, 95, 191, 0.48)",
        strokeDashArray: [8, 10],
        strokeWidth: 2,
      }));
    }

    addGuideObject(new window.fabric.Text(`${config.label} | Área segura`, {
      left: safeMarginX + 12,
      top: Math.max(safeMarginY - 36, 12),
      fill: "rgba(124, 82, 6, 0.9)",
      fontFamily: "Arial",
      fontSize: Math.max(Math.min(width, height) * 0.028, 16),
      fontWeight: "700",
      backgroundColor: "rgba(255, 248, 232, 0.82)",
    }));

    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
    artworkCanvas.requestRenderAll();
  }

  function setGuideVisibility(visible) {
    guidesVisible = visible;
    guideObjects.forEach((object) => {
      object.visible = guidesVisible;
    });

    if (toggleGuidesButton) {
      setButtonAccessibleLabel(toggleGuidesButton, guidesVisible ? "Ocultar guias" : "Mostrar guias");
      toggleGuidesButton.setAttribute("aria-pressed", String(guidesVisible));
    }

    artworkCanvas.requestRenderAll();
  }

  function toggleGuides() {
    setGuideVisibility(!guidesVisible);
    updateEditorStatus(guidesVisible ? "Guias visíveis" : "Guias ocultas", "idle");
  }

  function resizeArtworkCanvas({ redrawGuides = true } = {}) {
    const width = clampCanvasSize(widthInput?.value, 1200);
    const height = clampCanvasSize(heightInput?.value, 800);

    artworkCanvas.setWidth(width);
    artworkCanvas.setHeight(height);

    if (widthInput) {
      widthInput.value = width;
    }

    if (heightInput) {
      heightInput.value = height;
    }

    if (redrawGuides) {
      drawGuideObjects(getGuideConfig());
    } else {
      artworkCanvas.requestRenderAll();
    }
  }

  function populateTemplateSelect() {
    if (!templateSelect) {
      return;
    }

    const templates = ARTWORK_EDITOR_TEMPLATES[currentProductGuideKey] || [];
    templateSelect.innerHTML = "";

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "Template...";
    templateSelect.appendChild(emptyOption);

    templates.forEach((template) => {
      const option = document.createElement("option");
      option.value = template.key;
      option.textContent = template.label;
      templateSelect.appendChild(option);
    });

    templateSelect.disabled = templates.length === 0;

    if (applyTemplateButton) {
      applyTemplateButton.disabled = templates.length === 0;
    }
  }

  function getSelectedTemplate() {
    const templateKey = templateSelect?.value;
    const templates = ARTWORK_EDITOR_TEMPLATES[currentProductGuideKey] || [];

    return templates.find((template) => template.key === templateKey) || null;
  }

  function resolveTemplateValue(definition, key, pctKey, canvasSize, fallback = 0) {
    if (Number.isFinite(Number(definition[pctKey]))) {
      return canvasSize * Number(definition[pctKey]);
    }

    if (Number.isFinite(Number(definition[key]))) {
      return Number(definition[key]);
    }

    return fallback;
  }

  function createFabricObjectFromTemplate(definition) {
    const canvasWidth = artworkCanvas.getWidth();
    const canvasHeight = artworkCanvas.getHeight();
    const left = resolveTemplateValue(definition, "left", "leftPct", canvasWidth, canvasWidth / 2);
    const top = resolveTemplateValue(definition, "top", "topPct", canvasHeight, canvasHeight / 2);
    const width = resolveTemplateValue(definition, "width", "widthPct", canvasWidth, undefined);
    const height = resolveTemplateValue(definition, "height", "heightPct", canvasHeight, undefined);
    const baseOptions = {
      left,
      top,
      fill: definition.fill ?? "#111111",
      stroke: definition.stroke,
      strokeWidth: definition.strokeWidth ?? 0,
      angle: definition.angle ?? 0,
      opacity: definition.opacity ?? 1,
      originX: definition.originX || "center",
      originY: definition.originY || "center",
      cornerStyle: "circle",
      transparentCorners: false,
    };

    if (definition.type === "rect") {
      return new window.fabric.Rect({
        ...baseOptions,
        width: width ?? 220,
        height: height ?? 140,
        rx: definition.rx ?? 0,
        ry: definition.ry ?? 0,
      });
    }

    if (definition.type === "circle") {
      const radius = Number.isFinite(Number(definition.radiusPct))
        ? Math.min(canvasWidth, canvasHeight) * Number(definition.radiusPct)
        : Number(definition.radius ?? 80);

      return new window.fabric.Circle({
        ...baseOptions,
        radius,
      });
    }

    if (definition.type === "text") {
      return new window.fabric.IText(definition.text || "Seu texto", {
        ...baseOptions,
        fontFamily: definition.fontFamily || "Arial",
        fontSize: definition.fontSize ?? 48,
        fontWeight: definition.fontWeight || "700",
        textAlign: definition.textAlign || "center",
      });
    }

    return new window.fabric.Textbox(definition.text || "Seu texto", {
      ...baseOptions,
      width: width ?? canvasWidth * 0.5,
      fontFamily: definition.fontFamily || "Arial",
      fontSize: definition.fontSize ?? 48,
      fontWeight: definition.fontWeight || "700",
      textAlign: definition.textAlign || "center",
    });
  }

  function applySelectedTemplate() {
    const template = getSelectedTemplate();

    if (!template) {
      updateEditorStatus("Selecione um template", "warning");
      return;
    }

    if (getUserObjects().length > 0 && !window.confirm("Aplicar este template vai limpar a prancheta. Continuar?")) {
      return;
    }

    getUserObjects().forEach((object) => artworkCanvas.remove(object));
    artworkCanvas.discardActiveObject();

    const createdObjects = template.objects
      .map(createFabricObjectFromTemplate)
      .filter(Boolean);

    createdObjects.forEach((object) => artworkCanvas.add(object));
    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));

    if (createdObjects.length) {
      updateCanvasAndSelection(createdObjects[0]);
    } else {
      artworkCanvas.requestRenderAll();
      updateObjectPropertiesPanel();
    }

    updateEditorStatus("Template aplicado.", "success");
  }

  function setArtworkEditorProduct(productKey) {
    currentProductGuideKey = ARTWORK_EDITOR_PRODUCT_GUIDES[productKey] ? productKey : "mug";
    const config = getGuideConfig(currentProductGuideKey);

    artworkCanvas.discardActiveObject();
    artworkCanvas.setWidth(config.width);
    artworkCanvas.setHeight(config.height);

    if (widthInput) {
      widthInput.value = config.width;
    }

    if (heightInput) {
      heightInput.value = config.height;
    }

    if (currentProductLabel) {
      currentProductLabel.textContent = config.label;
    }

    if (productSelector && productSelector.value !== currentProductGuideKey) {
      productSelector.value = currentProductGuideKey;
    }

    populateTemplateSelect();
    drawGuideObjects(config);
    setGuideVisibility(guidesVisible);
    updateObjectPropertiesPanel();
    updateEditorStatus(`Guias ajustadas para ${config.label}`, "idle");
  }

  function addImageFromFile(file) {
    if (!file) {
      return;
    }

    if (!file.type || !file.type.startsWith("image/")) {
      updateEditorStatus("Arquivo de imagem inválido", "error");
      return;
    }

    updateEditorStatus("Carregando imagem no editor...", "loading");

    const reader = new FileReader();

    reader.onload = () => {
      window.fabric.Image.fromURL(reader.result, (image) => {
        const maxWidth = artworkCanvas.getWidth() * 0.72;
        const maxHeight = artworkCanvas.getHeight() * 0.72;
        const scale = Math.min(maxWidth / image.width, maxHeight / image.height, 1);

        image.set({
          left: artworkCanvas.getWidth() / 2,
          top: artworkCanvas.getHeight() / 2,
          originX: "center",
          originY: "center",
          cornerStyle: "circle",
          transparentCorners: false,
        });
        image.scale(scale);

        artworkCanvas.add(image);
        updateCanvasAndSelection(image);
        guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
        updateEditorStatus("Imagem adicionada à prancheta", "success");

        if (imageInput) {
          imageInput.value = "";
        }
      }, { crossOrigin: "anonymous" });
    };

    reader.onerror = () => {
      updateEditorStatus("Não foi possível ler a imagem", "error");
    };

    reader.readAsDataURL(file);
  }

  function addTextObject() {
    const text = textInput?.value?.trim() || "Seu texto";
    const fontSize = clampFontSize(fontSizeInput?.value);
    const fill = textColorInput?.value || "#111111";
    const textObject = new window.fabric.IText(text, {
      left: artworkCanvas.getWidth() / 2,
      top: artworkCanvas.getHeight() / 2,
      originX: "center",
      originY: "center",
      fill,
      fontFamily: "Arial",
      fontSize,
      fontWeight: "700",
      textAlign: "center",
      cornerStyle: "circle",
      transparentCorners: false,
    });

    artworkCanvas.add(textObject);
    updateCanvasAndSelection(textObject);
    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
    textObject.enterEditing();
    textObject.selectAll();
    updateEditorStatus("Texto adicionado à prancheta", "success");
  }

  function duplicateSelectedObject() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    activeObject.clone((clone) => {
      artworkCanvas.discardActiveObject();

      if (clone.type === "activeSelection") {
        const clonedObjects = clone.getObjects().filter((object) => !object.isGuide);
        const selection = new window.fabric.ActiveSelection([], { canvas: artworkCanvas });

        clonedObjects.forEach((object) => {
          object.set({
            left: (object.left ?? 0) + 24,
            top: (object.top ?? 0) + 24,
            evented: true,
          });
          artworkCanvas.add(object);
          selection.addWithUpdate(object);
        });

        if (clonedObjects.length) {
          artworkCanvas.setActiveObject(selection);
        }
      } else {
        clone.set({
          left: (clone.left ?? 0) + 24,
          top: (clone.top ?? 0) + 24,
          evented: true,
        });
        artworkCanvas.add(clone);
        updateCanvasAndSelection(clone);
      }

      guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
      artworkCanvas.requestRenderAll();
      updateEditorStatus("Objeto duplicado", "success");
    });
  }

  function centerSelectedObject() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    activeObject.set({
      left: artworkCanvas.getWidth() / 2,
      top: artworkCanvas.getHeight() / 2,
      originX: "center",
      originY: "center",
    });
    updateCanvasAndSelection(activeObject);
    updateEditorStatus("Objeto centralizado", "success");
  }

  function bringSelectedForward() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    artworkCanvas.bringForward(activeObject);
    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
    artworkCanvas.requestRenderAll();
    updateEditorStatus("Objeto movido para frente", "success");
  }

  function sendSelectedBackward() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    artworkCanvas.sendBackwards(activeObject);
    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
    artworkCanvas.requestRenderAll();
    updateEditorStatus("Objeto enviado para trás", "success");
  }

  function removeSelectedObject() {
    const selectedObjects = artworkCanvas.getActiveObjects().filter((object) => !object.isGuide);

    if (!selectedObjects.length) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    selectedObjects.forEach((object) => artworkCanvas.remove(object));
    artworkCanvas.discardActiveObject();
    artworkCanvas.requestRenderAll();
    updateObjectPropertiesPanel();
    updateEditorStatus("Objeto removido", "success");
  }

  function clearArtworkCanvas() {
    getUserObjects().forEach((object) => artworkCanvas.remove(object));
    artworkCanvas.discardActiveObject();
    artworkCanvas.setBackgroundColor(null, () => {
      drawGuideObjects(getGuideConfig());
      updateObjectPropertiesPanel();
      updateEditorStatus("Prancheta limpa", "success");
    });
  }

  function withGuidesHidden(callback) {
    const previousVisibility = guideObjects.map((object) => object.visible);

    guideObjects.forEach((object) => {
      object.visible = false;
    });
    artworkCanvas.renderAll();

    try {
      return callback();
    } finally {
      guideObjects.forEach((object, index) => {
        object.visible = previousVisibility[index];
      });
      artworkCanvas.renderAll();
    }
  }

  function exportArtworkPngDataUrl() {
    artworkCanvas.discardActiveObject();

    return withGuidesHidden(() => artworkCanvas.toDataURL({
      format: "png",
      multiplier: 2,
    }));
  }

  function applyArtworkToViewer() {
    if (!getUserObjects().length) {
      updateEditorStatus("Adicione uma imagem ou texto antes de aplicar", "warning");
      return;
    }

    const dataUrl = exportArtworkPngDataUrl();
    sessionStorage.setItem("caneca-garagem-pending-artwork-data-url", dataUrl);
    sessionStorage.setItem("caneca-garagem-pending-product-key", currentProductGuideKey || "mug");
    updateEditorStatus("Composição enviada para o visualizador 3D", "success");
    window.location.href = "/visual-3d/demo/";
  }

  function exportFabricJsonWithoutGuides() {
    const wasGuidesVisible = guidesVisible;

    clearGuideObjects();
    const fabricJson = artworkCanvas.toJSON();
    drawGuideObjects(getGuideConfig());
    setGuideVisibility(wasGuidesVisible);
    return fabricJson;
  }

  function exportArtworkProjectJson() {
    return {
      version: ARTWORK_EDITOR_FILE_VERSION,
      productKey: currentProductGuideKey || "mug",
      width: artworkCanvas.getWidth(),
      height: artworkCanvas.getHeight(),
      guidesVisible,
      fabric: exportFabricJsonWithoutGuides(),
    };
  }

  function updateCanvasSizeInputs() {
    if (widthInput) {
      widthInput.value = artworkCanvas.getWidth();
    }

    if (heightInput) {
      heightInput.value = artworkCanvas.getHeight();
    }
  }

  function syncProductControlsFromProject(productKey) {
    currentProductGuideKey = ARTWORK_EDITOR_PRODUCT_GUIDES[productKey] ? productKey : "mug";
    const config = getGuideConfig(currentProductGuideKey);

    if (currentProductLabel) {
      currentProductLabel.textContent = config.label;
    }

    if (productSelector) {
      productSelector.value = currentProductGuideKey;
    }

    populateTemplateSelect();
  }

  function importArtworkProjectJson(json) {
    try {
      const project = typeof json === "string" ? JSON.parse(json) : json;

      if (!project || typeof project !== "object") {
        throw new Error("Projeto inválido.");
      }

      if (project.version !== ARTWORK_EDITOR_FILE_VERSION) {
        throw new Error("Versão de projeto incompatível.");
      }

      const fabricJson = project.fabric;

      if (!fabricJson || typeof fabricJson !== "object") {
        throw new Error("Arquivo sem dados Fabric válidos.");
      }

      guidesVisible = project.guidesVisible !== false;
      artworkCanvas.discardActiveObject();
      getUserObjects().forEach((object) => artworkCanvas.remove(object));
      clearGuideObjects();
      syncProductControlsFromProject(project.productKey || "mug");
      artworkCanvas.setWidth(clampCanvasSize(project.width, getGuideConfig().width));
      artworkCanvas.setHeight(clampCanvasSize(project.height, getGuideConfig().height));
      updateCanvasSizeInputs();

      artworkCanvas.loadFromJSON(fabricJson, () => {
        drawGuideObjects(getGuideConfig());
        setGuideVisibility(guidesVisible);
        artworkCanvas.requestRenderAll();
        updateObjectPropertiesPanel();
        setEditorStatus("Projeto carregado.", "success");
      });
      return true;
    } catch (error) {
      console.error("[artwork-editor-2d] import failed", error);
      setEditorStatus("Não foi possível importar o projeto.", "error");
      return false;
    }
  }

  function saveProjectToLocalStorage() {
    try {
      localStorage.setItem(ARTWORK_EDITOR_STORAGE_KEY, JSON.stringify(exportArtworkProjectJson()));
      setEditorStatus("Projeto salvo neste navegador.", "success");
    } catch (error) {
      console.error("[artwork-editor-2d] save local failed", error);
      setEditorStatus("Não foi possível salvar neste navegador.", "error");
    }
  }

  function loadProjectFromLocalStorage() {
    const raw = localStorage.getItem(ARTWORK_EDITOR_STORAGE_KEY);

    if (!raw) {
      setEditorStatus("Nenhum projeto salvo neste navegador.", "warning");
      return;
    }

    try {
      importArtworkProjectJson(JSON.parse(raw));
    } catch (error) {
      console.error("[artwork-editor-2d] load local failed", error);
      setEditorStatus("Projeto salvo inválido.", "error");
    }
  }

  function buildTimestampedFilename(extension) {
    const now = new Date();
    const pad = (value) => value.toString().padStart(2, "0");
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`;

    return `caneca-garagem-arte-${stamp}.${extension}`;
  }

  function downloadUrl(url, filename) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function downloadProjectJson() {
    const blob = new Blob([JSON.stringify(exportArtworkProjectJson(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    downloadUrl(url, buildTimestampedFilename("json"));
    URL.revokeObjectURL(url);
    setEditorStatus("JSON baixado.", "success");
  }

  function importProjectJsonFromFile(file) {
    if (!file) {
      return;
    }

    const reader = new FileReader();

    reader.onload = () => {
      try {
        if (importArtworkProjectJson(JSON.parse(reader.result))) {
          setEditorStatus("JSON importado.", "success");
        }
      } catch (error) {
        console.error("[artwork-editor-2d] json import failed", error);
        setEditorStatus("JSON inválido.", "error");
      }

      if (importJsonInput) {
        importJsonInput.value = "";
      }
    };

    reader.onerror = () => {
      setEditorStatus("Não foi possível ler o JSON.", "error");
    };

    reader.readAsText(file);
  }

  function downloadArtworkPng() {
    downloadUrl(exportArtworkPngDataUrl(), buildTimestampedFilename("png"));
    setEditorStatus("PNG baixado.", "success");
  }

  function isTypingTarget(target) {
    const tagName = target?.tagName?.toLowerCase();

    return Boolean(
      target?.isContentEditable ||
      ["input", "textarea", "select"].includes(tagName) ||
      getActiveObject()?.isEditing
    );
  }

  function handleEditorShortcut(event) {
    if (isTypingTarget(event.target)) {
      return;
    }

    const isModifierPressed = event.ctrlKey || event.metaKey;

    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      removeSelectedObject();
      return;
    }

    if (isModifierPressed && event.key.toLowerCase() === "d") {
      event.preventDefault();
      duplicateSelectedObject();
      return;
    }

    if (isModifierPressed && event.key === "Enter") {
      event.preventDefault();
      applyArtworkToViewer();
    }
  }

  [
    "selection:created",
    "selection:updated",
    "selection:cleared",
    "object:moving",
    "object:scaling",
    "object:rotating",
    "object:modified",
  ].forEach((eventName) => {
    artworkCanvas.on(eventName, updateObjectPropertiesPanel);
  });

  getPropertyInputs().forEach((input) => {
    input.addEventListener("input", applyObjectPropertyChange);
    input.addEventListener("change", applyObjectPropertyChange);
  });

  lockObjectButton?.addEventListener("click", toggleLockSelectedObject);
  widthInput?.addEventListener("change", () => resizeArtworkCanvas({ redrawGuides: true }));
  heightInput?.addEventListener("change", () => resizeArtworkCanvas({ redrawGuides: true }));
  imageInput?.addEventListener("change", (event) => addImageFromFile(event.target.files[0]));
  addImageButton?.addEventListener("click", () => imageInput?.click());
  applyTemplateButton?.addEventListener("click", applySelectedTemplate);
  productSelector?.addEventListener("change", () => setArtworkEditorProduct(productSelector.value));
  toggleGuidesButton?.addEventListener("click", toggleGuides);
  addTextButton?.addEventListener("click", addTextObject);
  duplicateButton?.addEventListener("click", duplicateSelectedObject);
  centerButton?.addEventListener("click", centerSelectedObject);
  bringForwardButton?.addEventListener("click", bringSelectedForward);
  sendBackwardButton?.addEventListener("click", sendSelectedBackward);
  removeSelectedButton?.addEventListener("click", removeSelectedObject);
  clearButton?.addEventListener("click", clearArtworkCanvas);
  applyButton?.addEventListener("click", applyArtworkToViewer);
  saveLocalButton?.addEventListener("click", saveProjectToLocalStorage);
  loadLocalButton?.addEventListener("click", loadProjectFromLocalStorage);
  downloadJsonButton?.addEventListener("click", downloadProjectJson);
  importJsonButton?.addEventListener("click", () => importJsonInput?.click());
  importJsonInput?.addEventListener("change", (event) => importProjectJsonFromFile(event.target.files[0]));
  downloadPngButton?.addEventListener("click", downloadArtworkPng);
  document.addEventListener("keydown", handleEditorShortcut);

  window.visual3dArtworkEditor2d = {
    setProduct: setArtworkEditorProduct,
    toggleGuides,
    populateTemplateSelect,
    applySelectedTemplate,
    addTextObject,
    duplicateSelectedObject,
    centerSelectedObject,
    bringSelectedForward,
    sendSelectedBackward,
    removeSelectedObject,
    clearArtworkCanvas,
    saveProjectToLocalStorage,
    loadProjectFromLocalStorage,
    downloadProjectJson,
    importProjectJsonFromFile,
    downloadArtworkPng,
    exportArtworkProjectJson,
    importArtworkProjectJson,
    exportArtworkPngDataUrl,
  };

  setArtworkEditorProduct("mug");
  setGuideVisibility(true);
  updateObjectPropertiesPanel();
  updateEditorStatus("Editor 2D pronto", "idle");
})();
