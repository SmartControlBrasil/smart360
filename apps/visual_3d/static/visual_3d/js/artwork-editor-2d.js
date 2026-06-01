(() => {
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

  const editorCanvasElement = document.getElementById("artwork-editor-canvas");
  const widthInput = document.getElementById("artwork-editor-width");
  const heightInput = document.getElementById("artwork-editor-height");
  const imageInput = document.getElementById("artwork-editor-image-input");
  const textInput = document.getElementById("artwork-editor-text-input");
  const fontSizeInput = document.getElementById("artwork-editor-font-size");
  const textColorInput = document.getElementById("artwork-editor-text-color");
  const currentProductLabel = document.getElementById("artwork-editor-current-product");
  const productSelector = document.getElementById("artwork-editor-product-selector");
  const toggleGuidesButton = document.getElementById("artwork-editor-toggle-guides");
  const addTextButton = document.getElementById("artwork-editor-add-text");
  const duplicateButton = document.getElementById("artwork-editor-duplicate");
  const centerButton = document.getElementById("artwork-editor-center");
  const bringForwardButton = document.getElementById("artwork-editor-bring-forward");
  const sendBackwardButton = document.getElementById("artwork-editor-send-backward");
  const removeSelectedButton = document.getElementById("artwork-editor-remove-selected");
  const clearButton = document.getElementById("artwork-editor-clear");
  const applyButton = document.getElementById("artwork-editor-apply");
  const statusElement = document.getElementById("artwork-editor-status");

  if (!editorCanvasElement) {
    return;
  }

  function updateEditorStatus(message, state = "idle") {
    if (!statusElement) {
      return;
    }

    statusElement.textContent = message;
    statusElement.dataset.state = state;
  }

  if (!window.fabric) {
    updateEditorStatus("Fabric.js não carregou", "error");
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

  function updateCanvasAndSelection(object) {
    if (object) {
      object.setCoords();
      artworkCanvas.setActiveObject(object);
    }

    artworkCanvas.requestRenderAll();
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
      toggleGuidesButton.textContent = guidesVisible ? "Ocultar guias" : "Mostrar guias";
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

    drawGuideObjects(config);
    setGuideVisibility(guidesVisible);
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
    updateEditorStatus("Objeto removido", "success");
  }

  function clearArtworkCanvas() {
    getUserObjects().forEach((object) => artworkCanvas.remove(object));
    artworkCanvas.discardActiveObject();
    artworkCanvas.setBackgroundColor(null, () => {
      drawGuideObjects(getGuideConfig());
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

  function exportArtworkProjectJson() {
    return JSON.stringify({
      productKey: currentProductGuideKey,
      width: artworkCanvas.getWidth(),
      height: artworkCanvas.getHeight(),
      canvas: artworkCanvas.toJSON(),
    });
  }

  function importArtworkProjectJson(json) {
    const project = typeof json === "string" ? JSON.parse(json) : json;

    clearGuideObjects();

    if (project.productKey) {
      currentProductGuideKey = ARTWORK_EDITOR_PRODUCT_GUIDES[project.productKey] ? project.productKey : "mug";
    }

    if (project.width) {
      artworkCanvas.setWidth(clampCanvasSize(project.width, artworkCanvas.getWidth()));
    }

    if (project.height) {
      artworkCanvas.setHeight(clampCanvasSize(project.height, artworkCanvas.getHeight()));
    }

    if (widthInput) {
      widthInput.value = artworkCanvas.getWidth();
    }

    if (heightInput) {
      heightInput.value = artworkCanvas.getHeight();
    }

    artworkCanvas.loadFromJSON(project.canvas || project, () => {
      drawGuideObjects(getGuideConfig());
      updateEditorStatus("Projeto carregado", "success");
    });
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

  widthInput?.addEventListener("change", () => resizeArtworkCanvas({ redrawGuides: true }));
  heightInput?.addEventListener("change", () => resizeArtworkCanvas({ redrawGuides: true }));
  imageInput?.addEventListener("change", (event) => addImageFromFile(event.target.files[0]));
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
  document.addEventListener("keydown", handleEditorShortcut);

  window.visual3dArtworkEditor2d = {
    setProduct: setArtworkEditorProduct,
    toggleGuides,
    addTextObject,
    duplicateSelectedObject,
    centerSelectedObject,
    bringSelectedForward,
    sendSelectedBackward,
    removeSelectedObject,
    clearArtworkCanvas,
    exportArtworkProjectJson,
    importArtworkProjectJson,
    exportArtworkPngDataUrl,
  };

  setArtworkEditorProduct("mug");
  setGuideVisibility(true);
  updateEditorStatus("Editor 2D pronto", "idle");
})();
