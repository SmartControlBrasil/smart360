(() => {
  const ARTWORK_EDITOR_STORAGE_KEY = "caneca-garagem-artwork-editor-project-v1";
  const ARTWORK_EDITOR_SESSION_PROJECT_KEY = "caneca-garagem-artwork-editor-session-project-v1";
  const PENDING_ARTWORK_DATA_URL_KEY = "caneca-garagem-pending-artwork-data-url";
  const PENDING_ARTWORK_PROJECT_KEY = "caneca-garagem-pending-artwork-project-v1";
  const PENDING_PRODUCT_KEY = "caneca-garagem-pending-product-key";
  const ARTWORK_EDITOR_FILE_VERSION = 1;
  const ARTWORK_EDITOR_HISTORY_LIMIT = 50;
  const EDITOR_ZOOM_MIN = 0.15;
  const EDITOR_ZOOM_MAX = 3;
  const EDITOR_ZOOM_STEP = 0.1;
  const ARTWORK_EDITOR_ELEMENTS = {
    decorativeStripe: { label: "Faixa decorativa" },
    simpleFrame: { label: "Moldura simples" },
    roundedFrame: { label: "Moldura arredondada" },
    circleBadge: { label: "Selo circular" },
    promoBadge: { label: "Selo promoção" },
    heart: { label: "Coração" },
    lightning: { label: "Raio" },
    speechBubble: { label: "Balão de fala" },
    dividerLine: { label: "Linha divisória" },
    textBadge: { label: "Badge com texto" },
  };
  const ARTWORK_EDITOR_FONT_FAMILIES = [
    "Arial",
    "Helvetica",
    "Georgia",
    "Times New Roman",
    "Courier New",
    "Impact",
    "Verdana",
    "Trebuchet MS",
    "Comic Sans MS",
  ];
  const ARTWORK_EDITOR_COLOR_PALETTE = [
    "#000000", "#1f2937", "#374151", "#4b5563", "#6b7280", "#9ca3af", "#d1d5db", "#ffffff",
    "#7f1d1d", "#dc2626", "#f97316", "#facc15", "#84cc16", "#22c55e", "#14b8a6", "#06b6d4",
    "#2563eb", "#4f46e5", "#7c3aed", "#c026d3", "#db2777", "#f43f5e",
    "#78350f", "#92400e", "#b45309", "#d97706", "#f59e0b",
    "#052e16", "#166534", "#15803d", "#16a34a", "#bbf7d0",
    "#0c4a6e", "#0369a1", "#0284c7", "#38bdf8", "#bae6fd",
    "#312e81", "#4338ca", "#6366f1", "#c4b5fd"
  ];

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
  const fontFamilySelect = document.getElementById("artwork-editor-font-family");
  const currentProductLabel = document.getElementById("artwork-editor-current-product");
  const productSelector = document.getElementById("artwork-editor-product-selector");
  const templateSelect = document.getElementById("artwork-editor-template-select");
  const applyTemplateButton = document.getElementById("artwork-editor-apply-template");
  const zoomOutButton = document.getElementById("artwork-editor-zoom-out");
  const zoomLabel = document.getElementById("artwork-editor-zoom-label");
  const zoomInButton = document.getElementById("artwork-editor-zoom-in");
  const zoomResetButton = document.getElementById("artwork-editor-zoom-reset");
  const zoomFitButton = document.getElementById("artwork-editor-zoom-fit");
  const canvasScrollArea = document.getElementById("artwork-editor-scroll-area");
  const canvasStageElement = document.getElementById("artwork-editor-canvas-stage");
  const canvasSpacerElement = document.getElementById("artwork-editor-canvas-spacer");
  const canvasScaleElement = document.getElementById("artwork-editor-canvas-scale");
  const toggleGuidesButton = document.getElementById("artwork-editor-toggle-guides");
  const addTextButton = document.getElementById("artwork-editor-add-text");
  const undoButton = document.getElementById("artwork-editor-undo");
  const redoButton = document.getElementById("artwork-editor-redo");
  const copyButton = document.getElementById("artwork-editor-copy");
  const pasteButton = document.getElementById("artwork-editor-paste");
  const duplicateButton = document.getElementById("artwork-editor-duplicate");
  const centerButton = document.getElementById("artwork-editor-center");
  const alignLeftButton = document.getElementById("artwork-editor-align-left");
  const alignCenterButton = document.getElementById("artwork-editor-align-center");
  const alignRightButton = document.getElementById("artwork-editor-align-right");
  const alignTopButton = document.getElementById("artwork-editor-align-top");
  const alignMiddleButton = document.getElementById("artwork-editor-align-middle");
  const alignBottomButton = document.getElementById("artwork-editor-align-bottom");
  const toggleGridButton = document.getElementById("artwork-editor-toggle-grid");
  const toggleSnapButton = document.getElementById("artwork-editor-toggle-snap");
  const bringForwardButton = document.getElementById("artwork-editor-bring-forward");
  const sendBackwardButton = document.getElementById("artwork-editor-send-backward");
  const removeSelectedButton = document.getElementById("artwork-editor-remove-selected");
  const clearButton = document.getElementById("artwork-editor-clear");
  const applyButton = document.getElementById("artwork-editor-apply");
  const textBoldButton = document.getElementById("artwork-editor-text-bold");
  const textItalicButton = document.getElementById("artwork-editor-text-italic");
  const textAlignLeftButton = document.getElementById("artwork-editor-text-align-left");
  const textAlignCenterButton = document.getElementById("artwork-editor-text-align-center");
  const textAlignRightButton = document.getElementById("artwork-editor-text-align-right");
  const textUppercaseButton = document.getElementById("artwork-editor-text-uppercase");
  const elementDecorativeStripeButton = document.getElementById("artwork-editor-element-decorative-stripe");
  const elementSimpleFrameButton = document.getElementById("artwork-editor-element-simple-frame");
  const elementRoundedFrameButton = document.getElementById("artwork-editor-element-rounded-frame");
  const elementCircleBadgeButton = document.getElementById("artwork-editor-element-circle-badge");
  const elementPromoBadgeButton = document.getElementById("artwork-editor-element-promo-badge");
  const elementHeartButton = document.getElementById("artwork-editor-element-heart");
  const elementLightningButton = document.getElementById("artwork-editor-element-lightning");
  const elementSpeechBubbleButton = document.getElementById("artwork-editor-element-speech-bubble");
  const elementDividerLineButton = document.getElementById("artwork-editor-element-divider-line");
  const elementTextBadgeButton = document.getElementById("artwork-editor-element-text-badge");
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
  const propertiesPanel = document.querySelector(".visual-3d-editor-properties");
  const editorToolButtons = Array.from(document.querySelectorAll(".visual-3d-tool-button"));
  const colorStripElement = document.getElementById("artwork-editor-color-strip");
  const fillStatusElement = document.getElementById("artwork-editor-fill-status");
  const strokeStatusElement = document.getElementById("artwork-editor-stroke-status");
  let activeEditorTool = "select";

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

  function getEditorToolLabel(toolName) {
    const labels = {
      select: "Selecionar",
      image: "Adicionar imagem",
      text: "Adicionar texto",
      rect: "Retângulo",
      circle: "Círculo",
      star: "Estrela",
      spiral: "Espiral",
      "color-picker": "Conta-gotas",
      grid: "Grade",
      "zoom-fit": "Zoom fit",
      copy: "Copiar",
      remove: "Remover",
    };
    return labels[toolName] || "Selecionar";
  }

  function setActiveEditorTool(toolName) {
    activeEditorTool = toolName || "select";
    editorToolButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.tool === activeEditorTool);
    });
    setEditorStatus(`Ferramenta: ${getEditorToolLabel(activeEditorTool)}`, "info");
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
  let gridObjects = [];
  let guidesVisible = true;
  let copiedArtworkObject = null;
  let gridVisible = false;
  let snapEnabled = true;
  const GRID_SIZE = 50;
  const SNAP_THRESHOLD = 8;
  let currentProductGuideKey = "mug";
  let isUpdatingObjectProperties = false;
  let undoStack = [];
  let redoStack = [];
  let isRestoringHistory = false;
  let isPushingHistory = false;
  let autoSaveTimer = null;
  let autoSaveEnabled = false;
  let editorZoom = 1;
  let resizeZoomTimer = null;
  let defaultTextFontFamily = "Arial";

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

  function populateFontFamilySelect() {
    if (!fontFamilySelect) {
      return;
    }

    fontFamilySelect.innerHTML = "";
    ARTWORK_EDITOR_FONT_FAMILIES.forEach((fontFamily) => {
      const option = document.createElement("option");
      option.value = fontFamily;
      option.textContent = fontFamily;
      fontFamilySelect.appendChild(option);
    });

    if (!ARTWORK_EDITOR_FONT_FAMILIES.includes(defaultTextFontFamily)) {
      defaultTextFontFamily = "Arial";
    }
    fontFamilySelect.value = defaultTextFontFamily;
  }

  function clampEditorZoom(value) {
    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return 1;
    }

    return Math.min(Math.max(numberValue, EDITOR_ZOOM_MIN), EDITOR_ZOOM_MAX);
  }

  function updateZoomLabel() {
    if (zoomLabel) {
      zoomLabel.textContent = `${Math.round(editorZoom * 100)}%`;
    }
  }

  function updateCanvasScaledLayout() {
    if (!canvasSpacerElement || !canvasScaleElement || !artworkCanvas) return;

    const canvasWidth = artworkCanvas.getWidth();
    const canvasHeight = artworkCanvas.getHeight();
    const scaledWidth = Math.ceil(canvasWidth * editorZoom);
    const scaledHeight = Math.ceil(canvasHeight * editorZoom);

    canvasSpacerElement.style.width = `${scaledWidth}px`;
    canvasSpacerElement.style.height = `${scaledHeight}px`;

    canvasScaleElement.style.width = `${canvasWidth}px`;
    canvasScaleElement.style.height = `${canvasHeight}px`;
    canvasScaleElement.style.transform = `scale(${editorZoom})`;

    if (canvasStageElement) {
      canvasStageElement.style.minWidth = "100%";
      canvasStageElement.style.minHeight = "100%";
    }

    artworkCanvas.calcOffset();
  }

  function setEditorZoom(nextZoom) {
    editorZoom = Math.max(EDITOR_ZOOM_MIN, Math.min(EDITOR_ZOOM_MAX, nextZoom));
    updateCanvasScaledLayout();
    updateZoomLabel();
  }

  function zoomInEditor() {
    setEditorZoom(editorZoom + EDITOR_ZOOM_STEP);
  }

  function zoomOutEditor() {
    setEditorZoom(editorZoom - EDITOR_ZOOM_STEP);
  }

  function resetEditorZoom() {
    setEditorZoom(1);
  }

  function fitEditorZoomToScreen() {
    if (!canvasScrollArea || !artworkCanvas) return;

    const availableWidth = canvasScrollArea.clientWidth - 48;
    const availableHeight = canvasScrollArea.clientHeight - 48;
    const canvasWidth = artworkCanvas.getWidth();
    const canvasHeight = artworkCanvas.getHeight();

    const scale = Math.min(
      availableWidth / canvasWidth,
      availableHeight / canvasHeight,
      1
    );

    setEditorZoom(scale);
  }

  function closeAllEditorMenus() {
    document.querySelectorAll(".visual-3d-menu.is-open").forEach((menu) => {
      menu.classList.remove("is-open");
    });
  }

  function toggleEditorMenu(menu) {
    const shouldOpen = !menu.classList.contains("is-open");
    closeAllEditorMenus();

    if (shouldOpen) {
      menu.classList.add("is-open");
    }
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

  function isTextObject(object) {
    return Boolean(object && (object.type === "i-text" || object.type === "textbox" || object.type === "text"));
  }

  function getActiveTextObjects() {
    const activeObject = getActiveUserObject();

    if (!activeObject) {
      return [];
    }

    if (activeObject.type === "activeSelection") {
      return activeObject.getObjects().filter((item) => isTextObject(item) && !item.isGuide);
    }

    return isTextObject(activeObject) ? [activeObject] : [];
  }

  function updateTextControlsFromSelection() {
    const textObjects = getActiveTextObjects();
    const first = textObjects[0] || null;

    if (textBoldButton) {
      textBoldButton.classList.toggle("is-active", first?.fontWeight === "bold");
    }
    if (textItalicButton) {
      textItalicButton.classList.toggle("is-active", first?.fontStyle === "italic");
    }

    [textAlignLeftButton, textAlignCenterButton, textAlignRightButton].forEach((button) => {
      button?.classList.remove("is-active");
    });
    if (first?.textAlign === "left") textAlignLeftButton?.classList.add("is-active");
    if (first?.textAlign === "center") textAlignCenterButton?.classList.add("is-active");
    if (first?.textAlign === "right") textAlignRightButton?.classList.add("is-active");

    if (first?.fontFamily) {
      defaultTextFontFamily = first.fontFamily;
    }
    if (fontFamilySelect) {
      fontFamilySelect.value = defaultTextFontFamily;
    }
    if (fontSizeInput && first?.fontSize) {
      fontSizeInput.value = clampFontSize(first.fontSize);
    }
  }

  function applyTextStyleToSelection(stylePatch) {
    const textObjects = getActiveTextObjects();

    if (!textObjects.length) {
      if (stylePatch && stylePatch.fontFamily) {
        defaultTextFontFamily = stylePatch.fontFamily;
      }
      if (stylePatch && stylePatch.fontSize && fontSizeInput) {
        fontSizeInput.value = clampFontSize(stylePatch.fontSize);
      }
      updateEditorStatus("Selecione um texto para aplicar o estilo.", "warning");
      updateTextControlsFromSelection();
      return;
    }

    textObjects.forEach((object) => {
      Object.entries(stylePatch || {}).forEach(([key, value]) => {
        object.set(key, value);
      });
      object.setCoords();
    });

    if (stylePatch && stylePatch.fontFamily) {
      defaultTextFontFamily = stylePatch.fontFamily;
    }
    if (stylePatch && stylePatch.fontSize && fontSizeInput) {
      fontSizeInput.value = clampFontSize(stylePatch.fontSize);
    }

    artworkCanvas.requestRenderAll();
    pushHistorySnapshot("text-style");
    scheduleAutoSaveArtworkProject("text-style");
    updateObjectPropertiesPanel();
    updateTextControlsFromSelection();
  }

  function toggleTextBold() {
    const textObjects = getActiveTextObjects();
    const shouldBeBold = textObjects.length ? textObjects[0].fontWeight !== "bold" : true;
    applyTextStyleToSelection({ fontWeight: shouldBeBold ? "bold" : "normal" });
  }

  function toggleTextItalic() {
    const textObjects = getActiveTextObjects();
    const shouldBeItalic = textObjects.length ? textObjects[0].fontStyle !== "italic" : true;
    applyTextStyleToSelection({ fontStyle: shouldBeItalic ? "italic" : "normal" });
  }

  function setSelectedTextAlign(align) {
    applyTextStyleToSelection({ textAlign: align });
  }

  function applyUppercaseToText() {
    const textObjects = getActiveTextObjects();

    if (!textObjects.length) {
      updateEditorStatus("Selecione um texto para aplicar o estilo.", "warning");
      return;
    }

    textObjects.forEach((object) => {
      object.set("text", String(object.text || "").toUpperCase());
      object.setCoords();
    });

    artworkCanvas.requestRenderAll();
    pushHistorySnapshot("text-uppercase");
    scheduleAutoSaveArtworkProject("text-uppercase");
    updateObjectPropertiesPanel();
    updateTextControlsFromSelection();
    updateEditorStatus("Texto convertido para caixa alta.", "success");
  }

  function isImageObject(object) {
    return object && object.type === "image";
  }

  function updateColorStatusFromSelection() {
    const object = getActiveUserObject();

    if (!fillStatusElement || !strokeStatusElement) {
      return;
    }

    if (!object) {
      fillStatusElement.textContent = "N/D";
      strokeStatusElement.textContent = "N/D";
      return;
    }

    if (object.type === "activeSelection") {
      const objects = object.getObjects().filter((item) => !item.isGuide);
      const first = objects[0];
      fillStatusElement.textContent = first?.fill || "N/D";
      strokeStatusElement.textContent = first?.stroke || "N/D";
      return;
    }

    fillStatusElement.textContent = object.fill || "N/D";
    strokeStatusElement.textContent = object.stroke || "N/D";
  }

  function applyFillColorToObject(object, color) {
    if (!object || object.isGuide) return false;
    if (isImageObject(object)) return false;
    if (typeof object.fill === "undefined") return false;
    object.set("fill", color);
    object.setCoords();
    return true;
  }

  function applyStrokeColorToObject(object, color) {
    if (!object || object.isGuide) return false;
    if (isImageObject(object)) return false;
    if (typeof object.stroke === "undefined" && typeof object.strokeWidth === "undefined") return false;
    object.set("stroke", color);
    if (!object.strokeWidth || Number(object.strokeWidth) <= 0) {
      object.set("strokeWidth", 2);
    }
    object.setCoords();
    return true;
  }

  function applyFillColorToSelection(color) {
    const activeObject = getActiveUserObject();

    if (!activeObject) {
      setEditorStatus("Selecione um objeto para aplicar a cor.", "warning");
      return;
    }

    let changed = false;
    let imageBlocked = false;

    if (activeObject.type === "activeSelection") {
      activeObject.getObjects().forEach((object) => {
        if (isImageObject(object)) imageBlocked = true;
        changed = applyFillColorToObject(object, color) || changed;
      });
    } else {
      if (isImageObject(activeObject)) imageBlocked = true;
      changed = applyFillColorToObject(activeObject, color) || changed;
    }

    if (!changed && imageBlocked) {
      setEditorStatus("Imagens não aceitam preenchimento direto.", "warning");
      updateColorStatusFromSelection();
      return;
    }

    if (!changed) {
      setEditorStatus("Objeto selecionado não aceita preenchimento.", "warning");
      updateColorStatusFromSelection();
      return;
    }

    artworkCanvas.requestRenderAll();
    pushHistorySnapshot();
    updateObjectPropertiesPanel();
    updateColorStatusFromSelection();
    setEditorStatus(imageBlocked ? "Cor aplicada. Imagens não aceitam preenchimento direto." : `Preenchimento aplicado: ${color}`, "success");
  }

  function applyStrokeColorToSelection(color) {
    const activeObject = getActiveUserObject();

    if (!activeObject) {
      setEditorStatus("Selecione um objeto para aplicar contorno.", "warning");
      return;
    }

    let changed = false;

    if (activeObject.type === "activeSelection") {
      activeObject.getObjects().forEach((object) => {
        changed = applyStrokeColorToObject(object, color) || changed;
      });
    } else {
      changed = applyStrokeColorToObject(activeObject, color) || changed;
    }

    if (!changed) {
      setEditorStatus("Objeto selecionado não aceita contorno.", "warning");
      updateColorStatusFromSelection();
      return;
    }

    artworkCanvas.requestRenderAll();
    pushHistorySnapshot();
    updateObjectPropertiesPanel();
    updateColorStatusFromSelection();
    setEditorStatus(`Contorno aplicado: ${color}`, "success");
  }

  function renderColorPalette() {
    if (!colorStripElement) return;

    colorStripElement.innerHTML = "";
    ARTWORK_EDITOR_COLOR_PALETTE.forEach((color) => {
      const button = document.createElement("button");
      button.className = "visual-3d-color-swatch";
      button.type = "button";
      button.style.backgroundColor = color;
      button.title = color;
      button.setAttribute("aria-label", `Aplicar cor ${color}`);
      button.dataset.color = color;
      button.addEventListener("click", (event) => {
        if (event.shiftKey) {
          applyStrokeColorToSelection(color);
        } else {
          applyFillColorToSelection(color);
        }
      });
      colorStripElement.appendChild(button);
    });
  }

  function updateHistoryButtons() {
    if (undoButton) {
      undoButton.disabled = undoStack.length < 2;
    }

    if (redoButton) {
      redoButton.disabled = redoStack.length === 0;
    }
  }

  function serializeCanvasForHistory() {
    return {
      version: ARTWORK_EDITOR_FILE_VERSION,
      productKey: currentProductGuideKey || "mug",
      width: artworkCanvas.getWidth(),
      height: artworkCanvas.getHeight(),
      guidesVisible,
      gridVisible,
      snapEnabled,
      fabric: exportFabricJsonWithoutGuides(),
    };
  }

  function stringifyHistorySnapshot(snapshot) {
    return JSON.stringify(snapshot);
  }

  function autoSaveArtworkProject(reason = "auto") {
    if (!autoSaveEnabled || isRestoringHistory || isPushingHistory) {
      return;
    }

    try {
      const project = exportArtworkProjectJson();
      const serializedProject = JSON.stringify(project);
      localStorage.setItem(ARTWORK_EDITOR_STORAGE_KEY, serializedProject);
      sessionStorage.setItem(ARTWORK_EDITOR_SESSION_PROJECT_KEY, serializedProject);
    } catch (error) {
      console.warn(`[artwork-editor-2d] autosave failed (${reason})`, error);
    }
  }

  function scheduleAutoSaveArtworkProject(reason = "change") {
    if (!autoSaveEnabled || isRestoringHistory || isPushingHistory) {
      return;
    }

    window.clearTimeout(autoSaveTimer);
    autoSaveTimer = window.setTimeout(() => {
      autoSaveArtworkProject(reason);
    }, 500);
  }

  function pushHistorySnapshot(reason = "") {
    if (isRestoringHistory || isPushingHistory) {
      return;
    }

    let didPushSnapshot = false;
    isPushingHistory = true;

    try {
      const snapshot = serializeCanvasForHistory();
      const previousSnapshot = undoStack[undoStack.length - 1];

      if (previousSnapshot && stringifyHistorySnapshot(snapshot) === stringifyHistorySnapshot(previousSnapshot)) {
        updateHistoryButtons();
        return;
      }

      undoStack.push(snapshot);
      didPushSnapshot = true;

      if (undoStack.length > ARTWORK_EDITOR_HISTORY_LIMIT) {
        undoStack.shift();
      }

      redoStack = [];
      updateHistoryButtons();
    } finally {
      isPushingHistory = false;
    }

    if (didPushSnapshot) {
      scheduleAutoSaveArtworkProject(reason || "history");
    }
  }

  function resetHistoryWithCurrentState() {
    undoStack = [];
    redoStack = [];
    pushHistorySnapshot("reset");
  }

  function restoreHistorySnapshot(snapshot) {
    isRestoringHistory = true;
    const restored = importArtworkProjectJson(snapshot, {
      preserveHistory: true,
      onComplete: () => {
        isRestoringHistory = false;
        updateHistoryButtons();
      },
    });

    if (!restored) {
      isRestoringHistory = false;
      updateHistoryButtons();
    }
  }

  function undoEditorChange() {
    if (undoStack.length < 2) {
      updateHistoryButtons();
      return;
    }

    const currentSnapshot = undoStack.pop();
    redoStack.push(currentSnapshot);
    restoreHistorySnapshot(undoStack[undoStack.length - 1]);
  }

  function redoEditorChange() {
    if (!redoStack.length) {
      updateHistoryButtons();
      return;
    }

    const snapshot = redoStack.pop();
    undoStack.push(snapshot);
    restoreHistorySnapshot(snapshot);
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
      propertiesPanel?.classList.add("is-empty");
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

    propertiesPanel?.classList.remove("is-empty");
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

  function applyObjectPropertyChange(event) {
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

    if (event?.type === "change") {
      pushHistorySnapshot();
    }
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
    pushHistorySnapshot();
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

  function clearGridObjects() {
    gridObjects.forEach((object) => artworkCanvas.remove(object));
    gridObjects = [];
  }

  function addGridObject(object) {
    object.set({
      selectable: false,
      evented: false,
      excludeFromExport: true,
      visible: gridVisible,
    });
    object.isGuide = true;
    object.isGrid = true;
    gridObjects.push(object);
    artworkCanvas.add(object);
    artworkCanvas.sendToBack(object);
    return object;
  }

  function arrangeGuideLayers() {
    gridObjects.forEach((object) => artworkCanvas.sendToBack(object));
    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));
  }

  function drawGridObjects() {
    clearGridObjects();

    if (!gridVisible) {
      artworkCanvas.requestRenderAll();
      return;
    }

    const width = artworkCanvas.getWidth();
    const height = artworkCanvas.getHeight();
    const gridStroke = "rgba(148, 163, 184, 0.32)";

    for (let x = GRID_SIZE; x < width; x += GRID_SIZE) {
      addGridObject(new window.fabric.Line([x, 0, x, height], {
        stroke: gridStroke,
        strokeWidth: 1,
      }));
    }

    for (let y = GRID_SIZE; y < height; y += GRID_SIZE) {
      addGridObject(new window.fabric.Line([0, y, width, y], {
        stroke: gridStroke,
        strokeWidth: 1,
      }));
    }

    arrangeGuideLayers();
    artworkCanvas.requestRenderAll();
  }

  function updateGridButtonLabel() {
    if (!toggleGridButton) {
      return;
    }

    toggleGridButton.textContent = gridVisible ? "Ocultar grade" : "Mostrar grade";
    toggleGridButton.setAttribute("aria-pressed", String(gridVisible));
  }

  function updateSnapButtonLabel() {
    if (!toggleSnapButton) {
      return;
    }

    toggleSnapButton.textContent = snapEnabled ? "Desativar snap" : "Ativar snap";
    toggleSnapButton.setAttribute("aria-pressed", String(snapEnabled));
  }

  function toggleGrid() {
    gridVisible = !gridVisible;
    updateGridButtonLabel();
    drawGridObjects();
    pushHistorySnapshot("toggle-grid");
    updateEditorStatus(gridVisible ? "Grade ativada." : "Grade ocultada.", gridVisible ? "success" : "idle");
  }

  function toggleSnap() {
    snapEnabled = !snapEnabled;
    updateSnapButtonLabel();
    pushHistorySnapshot("toggle-snap");
    updateEditorStatus(snapEnabled ? "Snap ativado." : "Snap desativado.", snapEnabled ? "success" : "idle");
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

    drawGridObjects();

    if (redrawGuides) {
      drawGuideObjects(getGuideConfig());
    } else {
      artworkCanvas.requestRenderAll();
    }

    fitEditorZoomToScreen();
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

    isRestoringHistory = true;
    getUserObjects().forEach((object) => artworkCanvas.remove(object));
    artworkCanvas.discardActiveObject();

    const createdObjects = template.objects
      .map(createFabricObjectFromTemplate)
      .filter(Boolean);

    createdObjects.forEach((object) => artworkCanvas.add(object));
    isRestoringHistory = false;
    guideObjects.forEach((object) => artworkCanvas.bringToFront(object));

    if (createdObjects.length) {
      updateCanvasAndSelection(createdObjects[0]);
    } else {
      artworkCanvas.requestRenderAll();
      updateObjectPropertiesPanel();
    }

    pushHistorySnapshot();
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
    drawGridObjects();
    drawGuideObjects(config);
    setGuideVisibility(guidesVisible);
    updateObjectPropertiesPanel();
    requestAnimationFrame(fitEditorZoomToScreen);
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
        pushHistorySnapshot();
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
      fontFamily: defaultTextFontFamily,
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
    pushHistorySnapshot();
    updateTextControlsFromSelection();
    updateEditorStatus("Texto adicionado à prancheta", "success");
  }

  function addRectangleObject() {
    const object = new window.fabric.Rect({
      left: artworkCanvas.getWidth() / 2,
      top: artworkCanvas.getHeight() / 2,
      originX: "center",
      originY: "center",
      width: 240,
      height: 140,
      fill: "rgba(249, 115, 22, 0.9)",
      stroke: "#9a3412",
      strokeWidth: 2,
      rx: 14,
      ry: 14,
      cornerStyle: "circle",
      transparentCorners: false,
    });
    artworkCanvas.add(object);
    updateCanvasAndSelection(object);
    arrangeGuideLayers();
    pushHistorySnapshot();
    updateEditorStatus("Retângulo adicionado.", "success");
  }

  function addCircleObject() {
    const object = new window.fabric.Circle({
      left: artworkCanvas.getWidth() / 2,
      top: artworkCanvas.getHeight() / 2,
      originX: "center",
      originY: "center",
      radius: 80,
      fill: "rgba(236, 72, 153, 0.9)",
      stroke: "#9d174d",
      strokeWidth: 2,
      cornerStyle: "circle",
      transparentCorners: false,
    });
    artworkCanvas.add(object);
    updateCanvasAndSelection(object);
    arrangeGuideLayers();
    pushHistorySnapshot();
    updateEditorStatus("Círculo adicionado.", "success");
  }

  function createStarPoints(outerRadius = 90, innerRadius = 42, points = 5) {
    const starPoints = [];
    const step = Math.PI / points;
    for (let i = 0; i < points * 2; i += 1) {
      const radius = i % 2 === 0 ? outerRadius : innerRadius;
      const angle = (i * step) - Math.PI / 2;
      starPoints.push({
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      });
    }
    return starPoints;
  }

  function addStarObject() {
    const object = new window.fabric.Polygon(createStarPoints(), {
      left: artworkCanvas.getWidth() / 2,
      top: artworkCanvas.getHeight() / 2,
      originX: "center",
      originY: "center",
      fill: "rgba(250, 204, 21, 0.95)",
      stroke: "#a16207",
      strokeWidth: 2,
      cornerStyle: "circle",
      transparentCorners: false,
    });
    artworkCanvas.add(object);
    updateCanvasAndSelection(object);
    arrangeGuideLayers();
    pushHistorySnapshot();
    updateEditorStatus("Estrela adicionada.", "success");
  }

  function addSpiralObject() {
    const object = new window.fabric.Path("M 0 0 C 20 -18 54 -12 50 18 C 45 54 -8 62 -34 28 C -60 -8 -24 -58 38 -54", {
      left: artworkCanvas.getWidth() / 2,
      top: artworkCanvas.getHeight() / 2,
      originX: "center",
      originY: "center",
      fill: "transparent",
      stroke: "#0f766e",
      strokeWidth: 6,
      strokeLineCap: "round",
      strokeLineJoin: "round",
      scaleX: 1.4,
      scaleY: 1.4,
      cornerStyle: "circle",
      transparentCorners: false,
    });
    artworkCanvas.add(object);
    updateCanvasAndSelection(object);
    arrangeGuideLayers();
    pushHistorySnapshot();
    updateEditorStatus("Espiral adicionada.", "success");
  }

  function addObjectToCenter(object, statusMessage) {
    if (!object) return;

    if (!object.group) {
      object.set({
        left: artworkCanvas.getWidth() / 2,
        top: artworkCanvas.getHeight() / 2,
        originX: "center",
        originY: "center",
      });
    }

    artworkCanvas.add(object);
    updateCanvasAndSelection(object);
    arrangeGuideLayers();
    pushHistorySnapshot("creative-element");
    scheduleAutoSaveArtworkProject("creative-element");
    updateEditorStatus(statusMessage || "Elemento adicionado.", "success");
  }

  function createHeartPath() {
    return new window.fabric.Path("M 0 -28 C -22 -52 -58 -34 -58 -6 C -58 22 -30 38 0 60 C 30 38 58 22 58 -6 C 58 -34 22 -52 0 -28 Z", {
      fill: "#ef4444",
      stroke: "#991b1b",
      strokeWidth: 3,
      cornerStyle: "circle",
      transparentCorners: false,
    });
  }

  function createSpeechBubblePath() {
    return new window.fabric.Path("M -110 -70 H 90 A 24 24 0 0 1 114 -46 V 34 A 24 24 0 0 1 90 58 H -18 L -58 94 L -52 58 H -110 A 24 24 0 0 1 -134 34 V -46 A 24 24 0 0 1 -110 -70 Z", {
      fill: "#ffffff",
      stroke: "#111827",
      strokeWidth: 4,
      cornerStyle: "circle",
      transparentCorners: false,
    });
  }

  function addCreativeElement(elementKey) {
    const key = ARTWORK_EDITOR_ELEMENTS[elementKey] ? elementKey : null;

    if (!key) {
      updateEditorStatus("Elemento não encontrado.", "warning");
      return;
    }

    const label = ARTWORK_EDITOR_ELEMENTS[key].label;
    let elementObject = null;

    if (key === "decorativeStripe") {
      elementObject = new window.fabric.Rect({
        width: 600,
        height: 80,
        rx: 12,
        ry: 12,
        fill: "#facc15",
        stroke: "#a16207",
        strokeWidth: 2,
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "simpleFrame") {
      elementObject = new window.fabric.Rect({
        width: 700,
        height: 420,
        fill: "transparent",
        stroke: "#111827",
        strokeWidth: 8,
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "roundedFrame") {
      elementObject = new window.fabric.Rect({
        width: 700,
        height: 420,
        rx: 28,
        ry: 28,
        fill: "transparent",
        stroke: "#111827",
        strokeWidth: 8,
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "circleBadge") {
      elementObject = new window.fabric.Group([
        new window.fabric.Circle({
          radius: 90,
          fill: "#f97316",
          stroke: "#111827",
          strokeWidth: 4,
          originX: "center",
          originY: "center",
        }),
        new window.fabric.IText("NOVO", {
          textAlign: "center",
          fontFamily: "Arial",
          fontSize: 44,
          fontWeight: "900",
          fill: "#111827",
          originX: "center",
          originY: "center",
        }),
      ], {
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "promoBadge") {
      elementObject = new window.fabric.Group([
        new window.fabric.Polygon(createStarPoints(100, 56, 8), {
          fill: "#f43f5e",
          stroke: "#881337",
          strokeWidth: 3,
          originX: "center",
          originY: "center",
        }),
        new window.fabric.IText("PROMO", {
          textAlign: "center",
          fontFamily: "Arial",
          fontSize: 34,
          fontWeight: "900",
          fill: "#ffffff",
          originX: "center",
          originY: "center",
        }),
      ], {
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "heart") {
      elementObject = createHeartPath();
    } else if (key === "lightning") {
      elementObject = new window.fabric.Polygon([
        { x: -35, y: -84 },
        { x: 18, y: -84 },
        { x: -6, y: -20 },
        { x: 46, y: -20 },
        { x: -30, y: 86 },
        { x: -4, y: 10 },
        { x: -52, y: 10 },
      ], {
        fill: "#facc15",
        stroke: "#a16207",
        strokeWidth: 3,
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "speechBubble") {
      elementObject = new window.fabric.Group([
        createSpeechBubblePath(),
        new window.fabric.IText("Sua frase", {
          left: -10,
          top: -6,
          textAlign: "center",
          fontFamily: "Arial",
          fontSize: 30,
          fontWeight: "700",
          fill: "#111827",
          originX: "center",
          originY: "center",
        }),
      ], {
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "dividerLine") {
      elementObject = new window.fabric.Line([-330, 0, 330, 0], {
        stroke: "#111827",
        strokeWidth: 6,
        strokeLineCap: "round",
        cornerStyle: "circle",
        transparentCorners: false,
      });
    } else if (key === "textBadge") {
      elementObject = new window.fabric.Group([
        new window.fabric.Rect({
          width: 300,
          height: 96,
          rx: 18,
          ry: 18,
          fill: "#2563eb",
          stroke: "#1e3a8a",
          strokeWidth: 3,
          originX: "center",
          originY: "center",
        }),
        new window.fabric.IText("Seu texto", {
          textAlign: "center",
          fontFamily: "Arial",
          fontSize: 34,
          fontWeight: "800",
          fill: "#ffffff",
          originX: "center",
          originY: "center",
        }),
      ], {
        cornerStyle: "circle",
        transparentCorners: false,
      });
    }

    addObjectToCenter(elementObject, `${label} adicionado.`);
  }

  function triggerEditorClickTarget(targetId) {
    if (!targetId) return false;
    const target = document.getElementById(targetId);
    if (!target) return false;
    target.click();
    return true;
  }

  function handleToolButtonAction(button) {
    const tool = button.dataset.tool || "select";
    const targetId = button.dataset.editorClick;

    setActiveEditorTool(tool);

    if (tool === "rect") {
      addRectangleObject();
      setActiveEditorTool("select");
      return;
    }
    if (tool === "circle") {
      addCircleObject();
      setActiveEditorTool("select");
      return;
    }
    if (tool === "star") {
      addStarObject();
      setActiveEditorTool("select");
      return;
    }
    if (tool === "spiral") {
      addSpiralObject();
      setActiveEditorTool("select");
      return;
    }
    if (tool === "color-picker") {
      updateEditorStatus("Conta-gotas disponível em breve.", "info");
      setActiveEditorTool("select");
      return;
    }
    if (tool === "image") {
      imageInput?.click();
      setActiveEditorTool("select");
      return;
    }
    if (tool === "text") {
      addTextObject();
      setActiveEditorTool("select");
      return;
    }
    if (tool === "grid") {
      toggleGrid();
      return;
    }
    if (tool === "zoom-fit") {
      fitEditorZoomToScreen();
      return;
    }
    if (tool === "copy") {
      copySelectedObject();
      return;
    }
    if (tool === "remove") {
      removeSelectedObject();
      return;
    }
    if (tool === "select") {
      return;
    }

    if (targetId) {
      triggerEditorClickTarget(targetId);
    }

    if (!["grid", "zoom-fit", "copy", "remove"].includes(tool)) {
      setActiveEditorTool("select");
    }
  }

  function copySelectedObject() {
    const activeObject = getActiveUserObject();

    if (!activeObject) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    activeObject.clone((clone) => {
      copiedArtworkObject = clone;
      updateEditorStatus("Objeto copiado.", "success");
    }, ["isArtworkLocked"]);
  }

  function pasteCopiedObject() {
    if (!copiedArtworkObject) {
      updateEditorStatus("Nenhum objeto copiado.", "warning");
      return;
    }

    copiedArtworkObject.clone((clone) => {
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

      arrangeGuideLayers();
      artworkCanvas.requestRenderAll();
      pushHistorySnapshot();
      updateEditorStatus("Objeto colado.", "success");
    }, ["isArtworkLocked"]);
  }

  function alignSelectedObject(horizontal, vertical, statusMessage) {
    const object = getActiveUserObject();

    if (!object) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    const scaledWidth = object.getScaledWidth();
    const scaledHeight = object.getScaledHeight();
    const currentCenter = object.getCenterPoint();
    let nextCenterX = currentCenter.x;
    let nextCenterY = currentCenter.y;

    if (horizontal === "left") {
      nextCenterX = scaledWidth / 2;
    } else if (horizontal === "center") {
      nextCenterX = artworkCanvas.getWidth() / 2;
    } else if (horizontal === "right") {
      nextCenterX = artworkCanvas.getWidth() - scaledWidth / 2;
    }

    if (vertical === "top") {
      nextCenterY = scaledHeight / 2;
    } else if (vertical === "middle") {
      nextCenterY = artworkCanvas.getHeight() / 2;
    } else if (vertical === "bottom") {
      nextCenterY = artworkCanvas.getHeight() - scaledHeight / 2;
    }

    object.setPositionByOrigin(new window.fabric.Point(nextCenterX, nextCenterY), "center", "center");
    object.setCoords();
    artworkCanvas.requestRenderAll();
    updateObjectPropertiesPanel();
    pushHistorySnapshot();
    updateEditorStatus(statusMessage, "success");
  }

  function alignSelectedLeft() {
    alignSelectedObject("left", null, "Objeto alinhado à esquerda.");
  }

  function alignSelectedCenter() {
    alignSelectedObject("center", null, "Objeto alinhado ao centro.");
  }

  function alignSelectedRight() {
    alignSelectedObject("right", null, "Objeto alinhado à direita.");
  }

  function alignSelectedTop() {
    alignSelectedObject(null, "top", "Objeto alinhado ao topo.");
  }

  function alignSelectedMiddle() {
    alignSelectedObject(null, "middle", "Objeto alinhado ao meio.");
  }

  function alignSelectedBottom() {
    alignSelectedObject(null, "bottom", "Objeto alinhado à base.");
  }

  function snapObjectDuringMove(object) {
    if (!snapEnabled || !object || object.isGuide) {
      return;
    }

    const nearestLeft = Math.round((object.left ?? 0) / GRID_SIZE) * GRID_SIZE;
    const nearestTop = Math.round((object.top ?? 0) / GRID_SIZE) * GRID_SIZE;

    if (Math.abs((object.left ?? 0) - nearestLeft) <= SNAP_THRESHOLD) {
      object.left = nearestLeft;
    }

    if (Math.abs((object.top ?? 0) - nearestTop) <= SNAP_THRESHOLD) {
      object.top = nearestTop;
    }

    const centerPoint = object.getCenterPoint();
    const canvasCenterX = artworkCanvas.getWidth() / 2;
    const canvasCenterY = artworkCanvas.getHeight() / 2;
    let nextCenterX = centerPoint.x;
    let nextCenterY = centerPoint.y;
    let shouldSnapCenter = false;

    if (Math.abs(centerPoint.x - canvasCenterX) <= SNAP_THRESHOLD) {
      nextCenterX = canvasCenterX;
      shouldSnapCenter = true;
    }

    if (Math.abs(centerPoint.y - canvasCenterY) <= SNAP_THRESHOLD) {
      nextCenterY = canvasCenterY;
      shouldSnapCenter = true;
    }

    if (shouldSnapCenter) {
      object.setPositionByOrigin(new window.fabric.Point(nextCenterX, nextCenterY), "center", "center");
    }

    object.setCoords();
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

      arrangeGuideLayers();
      artworkCanvas.requestRenderAll();
      pushHistorySnapshot();
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
    pushHistorySnapshot();
    updateEditorStatus("Objeto centralizado", "success");
  }

  function bringSelectedForward() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    artworkCanvas.bringForward(activeObject);
    arrangeGuideLayers();
    artworkCanvas.requestRenderAll();
    pushHistorySnapshot();
    updateEditorStatus("Objeto movido para frente", "success");
  }

  function sendSelectedBackward() {
    const activeObject = getActiveObject();

    if (!activeObject || activeObject.isGuide) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    artworkCanvas.sendBackwards(activeObject);
    arrangeGuideLayers();
    artworkCanvas.requestRenderAll();
    pushHistorySnapshot();
    updateEditorStatus("Objeto enviado para trás", "success");
  }

  function removeSelectedObject() {
    const selectedObjects = artworkCanvas.getActiveObjects().filter((object) => !object.isGuide);

    if (!selectedObjects.length) {
      updateEditorStatus("Nenhum objeto selecionado", "warning");
      return;
    }

    isRestoringHistory = true;
    selectedObjects.forEach((object) => artworkCanvas.remove(object));
    isRestoringHistory = false;
    artworkCanvas.discardActiveObject();
    artworkCanvas.requestRenderAll();
    updateObjectPropertiesPanel();
    pushHistorySnapshot();
    updateEditorStatus("Objeto removido", "success");
  }

  function clearArtworkCanvas() {
    isRestoringHistory = true;
    getUserObjects().forEach((object) => artworkCanvas.remove(object));
    isRestoringHistory = false;
    artworkCanvas.discardActiveObject();
    artworkCanvas.setBackgroundColor(null, () => {
      drawGridObjects();
      drawGuideObjects(getGuideConfig());
      updateObjectPropertiesPanel();
      pushHistorySnapshot();
      updateEditorStatus("Prancheta limpa", "success");
    });
  }

  function withGuidesHidden(callback) {
    const hiddenObjects = [...guideObjects, ...gridObjects];
    const previousVisibility = hiddenObjects.map((object) => object.visible);

    hiddenObjects.forEach((object) => {
      object.visible = false;
    });
    artworkCanvas.renderAll();

    try {
      return callback();
    } finally {
      hiddenObjects.forEach((object, index) => {
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
    const project = exportArtworkProjectJson();
    const productKey = currentProductGuideKey || "mug";

    autoSaveArtworkProject("apply-3d");
    sessionStorage.setItem(PENDING_ARTWORK_DATA_URL_KEY, dataUrl);
    sessionStorage.setItem(PENDING_ARTWORK_PROJECT_KEY, JSON.stringify(project));
    sessionStorage.setItem(PENDING_PRODUCT_KEY, productKey);
    updateEditorStatus("Arte enviada para visualização 3D.", "success");
    window.location.href = "/visual-3d/demo/";
  }

  function exportFabricJsonWithoutGuides() {
    return artworkCanvas.toJSON(["isArtworkLocked"]);
  }

  function exportArtworkProjectJson() {
    return {
      version: ARTWORK_EDITOR_FILE_VERSION,
      productKey: currentProductGuideKey || "mug",
      width: artworkCanvas.getWidth(),
      height: artworkCanvas.getHeight(),
      guidesVisible,
      gridVisible,
      snapEnabled,
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

  function importArtworkProjectJson(json, options = {}) {
    const preserveHistory = options.preserveHistory === true;
    const resetHistory = options.resetHistory ?? !preserveHistory;
    const onComplete = options.onComplete ?? null;

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

      const previousHistoryRestoreState = isRestoringHistory;
      isRestoringHistory = true;
      guidesVisible = project.guidesVisible !== false;

      if (typeof project.gridVisible === "boolean") {
        gridVisible = project.gridVisible;
      }

      if (typeof project.snapEnabled === "boolean") {
        snapEnabled = project.snapEnabled;
      }

      updateGridButtonLabel();
      updateSnapButtonLabel();
      artworkCanvas.discardActiveObject();
      getUserObjects().forEach((object) => artworkCanvas.remove(object));
      clearGuideObjects();
      clearGridObjects();
      syncProductControlsFromProject(project.productKey || "mug");
      artworkCanvas.setWidth(clampCanvasSize(project.width, getGuideConfig().width));
      artworkCanvas.setHeight(clampCanvasSize(project.height, getGuideConfig().height));
      updateCanvasSizeInputs();

      artworkCanvas.loadFromJSON(fabricJson, () => {
        drawGridObjects();
        drawGuideObjects(getGuideConfig());
        setGuideVisibility(guidesVisible);
        artworkCanvas.requestRenderAll();
        updateObjectPropertiesPanel();
        requestAnimationFrame(fitEditorZoomToScreen);

        if (resetHistory) {
          isRestoringHistory = false;
          resetHistoryWithCurrentState();
        } else {
          isRestoringHistory = previousHistoryRestoreState;
          updateHistoryButtons();
        }

        if (typeof onComplete === "function") {
          onComplete();
        }

        setEditorStatus("Projeto carregado.", "success");
      });
      return true;
    } catch (error) {
      console.error("[artwork-editor-2d] import failed", error);
      isRestoringHistory = false;
      updateHistoryButtons();
      setEditorStatus("Não foi possível importar o projeto.", "error");

      if (typeof onComplete === "function") {
        onComplete();
      }

      return false;
    }
  }

  function saveProjectToLocalStorage() {
    try {
      const serializedProject = JSON.stringify(exportArtworkProjectJson());
      localStorage.setItem(ARTWORK_EDITOR_STORAGE_KEY, serializedProject);
      sessionStorage.setItem(ARTWORK_EDITOR_SESSION_PROJECT_KEY, serializedProject);
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

  function restoreInitialArtworkProject() {
    const sessionProject = sessionStorage.getItem(ARTWORK_EDITOR_SESSION_PROJECT_KEY);
    const localProject = localStorage.getItem(ARTWORK_EDITOR_STORAGE_KEY);
    const raw = sessionProject || localProject;

    if (!raw) {
      return false;
    }

    try {
      const project = JSON.parse(raw);
      const restored = importArtworkProjectJson(project, {
        preserveHistory: false,
        resetHistory: false,
        onComplete: () => {
          if (typeof resetHistoryWithCurrentState === "function") {
            resetHistoryWithCurrentState();
          }

          setEditorStatus("Projeto restaurado.", "success");
        },
      });

      return restored;
    } catch (error) {
      console.warn("[artwork-editor-2d] não foi possível restaurar projeto", error);
      return false;
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
    if (event.key === "Escape") {
      closeAllEditorMenus();
      return;
    }

    if (isTypingTarget(event.target)) {
      return;
    }

    const isModifierPressed = event.ctrlKey || event.metaKey;
    const key = event.key.toLowerCase();

    if (isModifierPressed && key === "z" && event.shiftKey) {
      event.preventDefault();
      redoEditorChange();
      return;
    }

    if (isModifierPressed && key === "z") {
      event.preventDefault();
      undoEditorChange();
      return;
    }

    if (isModifierPressed && key === "y") {
      event.preventDefault();
      redoEditorChange();
      return;
    }

    if (isModifierPressed && key === "c") {
      event.preventDefault();
      copySelectedObject();
      return;
    }

    if (isModifierPressed && key === "v") {
      event.preventDefault();
      pasteCopiedObject();
      return;
    }

    if (isModifierPressed && (key === "+" || key === "=")) {
      event.preventDefault();
      zoomInEditor();
      return;
    }

    if (isModifierPressed && key === "-") {
      event.preventDefault();
      zoomOutEditor();
      return;
    }

    if (isModifierPressed && key === "0") {
      event.preventDefault();
      resetEditorZoom();
      return;
    }

    if (isModifierPressed && key === "1") {
      event.preventDefault();
      fitEditorZoomToScreen();
      return;
    }

    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      removeSelectedObject();
      return;
    }

    if (isModifierPressed && key === "d") {
      event.preventDefault();
      duplicateSelectedObject();
      return;
    }

    if (isModifierPressed && event.key === "Enter") {
      event.preventDefault();
      applyArtworkToViewer();
    }
  }

  artworkCanvas.on("object:moving", (event) => {
    snapObjectDuringMove(event.target);
  });

  [
    "selection:created",
    "selection:updated",
    "selection:cleared",
    "object:moving",
    "object:scaling",
    "object:rotating",
    "object:modified",
  ].forEach((eventName) => {
    artworkCanvas.on(eventName, () => {
      updateObjectPropertiesPanel();
      updateTextControlsFromSelection();
      updateColorStatusFromSelection();
    });
  });

  ["object:added", "object:removed", "object:modified"].forEach((eventName) => {
    artworkCanvas.on(eventName, (event) => {
      if (event.target?.isGuide) {
        return;
      }

      pushHistorySnapshot(eventName);
      scheduleAutoSaveArtworkProject(eventName);
    });
  });

  document.querySelectorAll(".visual-3d-menu-trigger").forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const menu = trigger.closest(".visual-3d-menu");

      if (menu) {
        toggleEditorMenu(menu);
      }
    });
  });

  document.querySelectorAll("[data-editor-click]").forEach((item) => {
    item.addEventListener("click", () => {
      triggerEditorClickTarget(item.dataset.editorClick);
    });
  });

  editorToolButtons.forEach((button) => {
    button.addEventListener("click", () => handleToolButtonAction(button));
  });

  document.querySelectorAll(".visual-3d-menu-dropdown button, .visual-3d-menu-dropdown a").forEach((item) => {
    item.addEventListener("click", () => {
      window.setTimeout(closeAllEditorMenus, 0);
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".visual-3d-menu")) {
      closeAllEditorMenus();
    }
  });

  getPropertyInputs().forEach((input) => {
    input.addEventListener("input", applyObjectPropertyChange);
    input.addEventListener("change", applyObjectPropertyChange);
  });

  zoomOutButton?.addEventListener("click", zoomOutEditor);
  zoomInButton?.addEventListener("click", zoomInEditor);
  zoomResetButton?.addEventListener("click", resetEditorZoom);
  zoomFitButton?.addEventListener("click", fitEditorZoomToScreen);
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeZoomTimer);
    resizeZoomTimer = window.setTimeout(fitEditorZoomToScreen, 120);
  });
  lockObjectButton?.addEventListener("click", toggleLockSelectedObject);
  undoButton?.addEventListener("click", undoEditorChange);
  redoButton?.addEventListener("click", redoEditorChange);
  copyButton?.addEventListener("click", copySelectedObject);
  pasteButton?.addEventListener("click", pasteCopiedObject);
  alignLeftButton?.addEventListener("click", alignSelectedLeft);
  alignCenterButton?.addEventListener("click", alignSelectedCenter);
  alignRightButton?.addEventListener("click", alignSelectedRight);
  alignTopButton?.addEventListener("click", alignSelectedTop);
  alignMiddleButton?.addEventListener("click", alignSelectedMiddle);
  alignBottomButton?.addEventListener("click", alignSelectedBottom);
  toggleGridButton?.addEventListener("click", toggleGrid);
  toggleSnapButton?.addEventListener("click", toggleSnap);
  widthInput?.addEventListener("change", () => {
    resizeArtworkCanvas({ redrawGuides: true });
    pushHistorySnapshot();
  });
  heightInput?.addEventListener("change", () => {
    resizeArtworkCanvas({ redrawGuides: true });
    pushHistorySnapshot();
  });
  imageInput?.addEventListener("change", (event) => addImageFromFile(event.target.files[0]));
  addImageButton?.addEventListener("click", () => imageInput?.click());
  applyTemplateButton?.addEventListener("click", applySelectedTemplate);
  productSelector?.addEventListener("change", () => {
    setArtworkEditorProduct(productSelector.value);

    if (!getUserObjects().length) {
      resetHistoryWithCurrentState();
    } else {
      pushHistorySnapshot();
    }
  });
  toggleGuidesButton?.addEventListener("click", toggleGuides);
  addTextButton?.addEventListener("click", addTextObject);
  textBoldButton?.addEventListener("click", toggleTextBold);
  textItalicButton?.addEventListener("click", toggleTextItalic);
  textAlignLeftButton?.addEventListener("click", () => setSelectedTextAlign("left"));
  textAlignCenterButton?.addEventListener("click", () => setSelectedTextAlign("center"));
  textAlignRightButton?.addEventListener("click", () => setSelectedTextAlign("right"));
  textUppercaseButton?.addEventListener("click", applyUppercaseToText);
  fontFamilySelect?.addEventListener("change", () => {
    const selectedFont = fontFamilySelect.value || "Arial";
    defaultTextFontFamily = selectedFont;
    const textObjects = getActiveTextObjects();
    if (textObjects.length) {
      applyTextStyleToSelection({ fontFamily: selectedFont });
      updateEditorStatus(`Fonte aplicada: ${selectedFont}`, "success");
    } else {
      updateEditorStatus(`Fonte padrão definida: ${selectedFont}`, "info");
    }
  });
  fontSizeInput?.addEventListener("change", () => {
    const nextSize = clampFontSize(fontSizeInput.value);
    fontSizeInput.value = nextSize;
    const textObjects = getActiveTextObjects();
    if (textObjects.length) {
      applyTextStyleToSelection({ fontSize: nextSize });
      updateEditorStatus(`Tamanho aplicado: ${nextSize}px`, "success");
    }
  });
  duplicateButton?.addEventListener("click", duplicateSelectedObject);
  centerButton?.addEventListener("click", centerSelectedObject);
  bringForwardButton?.addEventListener("click", bringSelectedForward);
  sendBackwardButton?.addEventListener("click", sendSelectedBackward);
  removeSelectedButton?.addEventListener("click", removeSelectedObject);
  clearButton?.addEventListener("click", clearArtworkCanvas);
  applyButton?.addEventListener("click", applyArtworkToViewer);
  elementDecorativeStripeButton?.addEventListener("click", () => addCreativeElement("decorativeStripe"));
  elementSimpleFrameButton?.addEventListener("click", () => addCreativeElement("simpleFrame"));
  elementRoundedFrameButton?.addEventListener("click", () => addCreativeElement("roundedFrame"));
  elementCircleBadgeButton?.addEventListener("click", () => addCreativeElement("circleBadge"));
  elementPromoBadgeButton?.addEventListener("click", () => addCreativeElement("promoBadge"));
  elementHeartButton?.addEventListener("click", () => addCreativeElement("heart"));
  elementLightningButton?.addEventListener("click", () => addCreativeElement("lightning"));
  elementSpeechBubbleButton?.addEventListener("click", () => addCreativeElement("speechBubble"));
  elementDividerLineButton?.addEventListener("click", () => addCreativeElement("dividerLine"));
  elementTextBadgeButton?.addEventListener("click", () => addCreativeElement("textBadge"));
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
    undoEditorChange,
    redoEditorChange,
    copySelectedObject,
    pasteCopiedObject,
    alignSelectedLeft,
    alignSelectedCenter,
    alignSelectedRight,
    alignSelectedTop,
    alignSelectedMiddle,
    alignSelectedBottom,
    toggleGrid,
    toggleSnap,
    zoomInEditor,
    zoomOutEditor,
    resetEditorZoom,
    fitEditorZoomToScreen,
    populateTemplateSelect,
    applySelectedTemplate,
    addTextObject,
    duplicateSelectedObject,
    centerSelectedObject,
    bringSelectedForward,
    sendSelectedBackward,
    removeSelectedObject,
    addCreativeElement,
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

  updateGridButtonLabel();
  updateSnapButtonLabel();
  populateFontFamilySelect();
  setActiveEditorTool("select");
  setArtworkEditorProduct("mug");
  setGuideVisibility(true);
  updateObjectPropertiesPanel();
  updateTextControlsFromSelection();
  const restoredInitialProject = restoreInitialArtworkProject();
  requestAnimationFrame(fitEditorZoomToScreen);

  if (!restoredInitialProject) {
    resetHistoryWithCurrentState();
    updateEditorStatus("Editor 2D pronto", "idle");
  }

  autoSaveEnabled = true;
  renderColorPalette();
  updateColorStatusFromSelection();
})();
