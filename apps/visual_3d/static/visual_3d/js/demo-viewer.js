// Importa o namespace principal do Three.js usado para cena, câmera, geometrias, materiais e texturas.
import * as THREE from "three";
// Importa os controles de órbita para permitir girar/inspecionar a caneca com mouse ou toque.
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
// Importa o loader responsável por carregar o arquivo GLB da caneca.
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

// Caminho público do modelo 3D principal da caneca servido pelos arquivos estáticos do Django.
const MODEL_URL = "/static/visual_3d/models/mug.glb";
// Tamanho visual alvo do GLB após o cálculo automático de escala.
const GLB_DISPLAY_SIZE = 3.2;
// Folga usada para posicionar a câmera sem cortar o modelo nas bordas do canvas.
const CAMERA_FIT_PADDING = 1.35;
// Corrige a orientação inicial do mug.glb para aproximar a alça do início da estampa.
const MUG_MODEL_BASE_ROTATION_DEGREES = 90;
// Valor padrão do controle manual "Girar caneca"; soma por cima da rotação base.
const USER_MODEL_ROTATION_DEFAULT_DEGREES = 0;
// Largura do canvas 2D interno onde a arte do usuário é composta antes de virar textura.
const ARTWORK_CANVAS_WIDTH = 2048;
// Altura do canvas 2D interno; proporção 2:1 ajuda a simular uma faixa ao redor da caneca.
const ARTWORK_CANVAS_HEIGHT = 1024;
// Cor de fundo aplicada no canvas da arte; vira área branca/respiro na textura.
const ARTWORK_CANVAS_BACKGROUND = "#ffffff";
// Fração horizontal útil do canvas usada como base para conter a arte sem ocupar tudo.
const ARTWORK_SAFE_WIDTH = 0.6;
// Margem superior da área útil da arte dentro do canvas intermediário.
const ARTWORK_SAFE_TOP = 0.03;
// Margem inferior da área útil da arte dentro do canvas intermediário.
const ARTWORK_SAFE_BOTTOM = 0.08;
// Deslocamento horizontal base aplicado antes do slider Posição X.
const ARTWORK_BASE_OFFSET_X = 0.20;
// Deslocamento extra de início lateral para aproximar a arte da região esperada da costura/alça.
const ARTWORK_START_SIDE_OFFSET = 0.55;
// Palavras usadas para tentar identificar meshes/materiais de alça quando o GLB vier separado.
const HANDLE_NAME_PARTS = ["handle", "alca", "alça", "grip", "asa", "pegador"];

// Elemento HTML que recebe o canvas WebGL criado pelo Three.js.
const container = document.getElementById("visual-3d-canvas");
// Botão que captura o frame atual do renderer como imagem PNG.
const captureButton = document.getElementById("capture-preview");
// Elemento img onde o preview capturado é exibido.
const previewImage = document.getElementById("captured-preview");
// Mensagem mostrada enquanto ainda não existe preview capturado.
const previewEmpty = document.getElementById("preview-empty");
// Input file usado para selecionar PNG/JPEG/WebP da arte.
const artworkInput = document.getElementById("artwork-input");
// Botão que remove a arte aplicada e restaura materiais originais.
const removeArtworkButton = document.getElementById("remove-artwork");
// Botão que pausa ou retoma a rotação automática do objeto.
const toggleRotationButton = document.getElementById("toggle-rotation");
// Botão que volta controles de arte e rotação visual para o padrão.
const resetArtworkAdjustmentsButton = document.getElementById("reset-artwork-adjustments");
// Slider do HTML que gira a caneca no eixo Y para visualização/alinhamento.
const mugRotationInput = document.getElementById("mug-rotation");
// Output textual que mostra em graus o valor do slider "Girar caneca".
const mugRotationOutput = document.getElementById("mug-rotation-value");
// Status textual sobre upload/aplicação/remocao da arte.
const artworkStatus = document.getElementById("artwork-status");
// Status textual sobre carregamento do GLB ou uso do fallback.
const modelStatus = document.getElementById("model-status");
// Texto resumo do diagnóstico de meshes do GLB.
const diagnosticsSummary = document.getElementById("model-diagnostics-summary");
// Corpo da tabela de diagnóstico onde cada mesh encontrado vira uma linha.
const diagnosticsBody = document.getElementById("model-diagnostics-body");
// Lista de sliders que alteram offset X/Y e escala X/Y da arte.
const artworkControls = Array.from(document.querySelectorAll("[data-artwork-control]"));
// Lista de checkboxes que invertem a arte horizontalmente ou verticalmente.
const artworkToggles = Array.from(document.querySelectorAll("[data-artwork-toggle]"));
// Mapa entre nomes internos dos controles e outputs visuais no HTML.
const artworkOutputs = {
  // Output numérico do slider Posição X.
  offsetX: document.getElementById("artwork-offset-x-value"),
  // Output numérico do slider Posição Y.
  offsetY: document.getElementById("artwork-offset-y-value"),
  // Output numérico do slider Escala X.
  scaleX: document.getElementById("artwork-scale-x-value"),
  // Output numérico do slider Escala Y.
  scaleY: document.getElementById("artwork-scale-y-value"),
};
// Tipos de imagem aceitos no upload para evitar arquivos incompatíveis.
const allowedArtworkTypes = new Set(["image/png", "image/jpeg", "image/webp"]);
// Estado inicial dos controles de arte usados para desenhar no canvas intermediário.
const defaultArtworkTransform = {
  // Deslocamento horizontal inicial da arte.
  offsetX: 0,
  // Deslocamento vertical inicial da arte; negativo posiciona mais para baixo/alto conforme o cálculo usado.
  offsetY: -1,
  // Escala horizontal inicial da arte.
  scaleX: 1,
  // Escala vertical inicial da arte.
  scaleY: 1,
  // Espelhamento horizontal inicial.
  flipX: false,
  // Espelhamento vertical inicial; corrige a orientação visual esperada no UV atual.
  flipY: true,
};

// Textura ativa criada a partir do canvas intermediário.
let artworkTexture = null;
// Imagem original carregada pelo usuário em um objeto Image().
let artworkImage = null;
// Canvas 2D interno onde a arte é redesenhada a cada ajuste.
let artworkCanvas = null;
// Contexto 2D usado para limpar fundo, posicionar, escalar e desenhar a imagem.
let artworkCanvasContext = null;
// URL temporária criada para ler o arquivo local selecionado pelo usuário.
let artworkObjectUrl = null;
// Referência ao GLB carregado; null enquanto o fallback estiver ativo ou antes do load.
let glbModel = null;
// Controla se o grupo externo gira automaticamente no loop de animação.
let autoRotateEnabled = true;
// Valor atual do slider "Girar caneca", em graus.
let userRotationDegrees = USER_MODEL_ROTATION_DEFAULT_DEGREES;
// Estado mutável dos controles de arte usado por redrawArtworkCanvas().
let artworkTransform = { ...defaultArtworkTransform };

// Cena principal do Three.js, onde câmera, luzes, chão e caneca são inseridos.
const scene = new THREE.Scene();
// Cor de fundo do viewport 3D.
scene.background = new THREE.Color(0x101722);

// Câmera perspectiva: FOV 45, aspect inicial 1, planos de corte perto/longe.
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
// Posição inicial antes do enquadramento automático do GLB.
camera.position.set(0, 2.2, 5.5);

// Renderer WebGL com suavização de bordas e buffer preservado para captura do preview.
const renderer = new THREE.WebGLRenderer({
  // Antialias melhora serrilhados no modelo.
  antialias: true,
  // preserveDrawingBuffer permite usar toDataURL no canvas para capturar preview.
  preserveDrawingBuffer: true,
});
// Limita pixel ratio para equilibrar nitidez e desempenho.
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
// Ativa sombras nos materiais/luzes que usam castShadow/receiveShadow.
renderer.shadowMap.enabled = true;
// Insere o canvas WebGL dentro do container da página.
container.appendChild(renderer.domElement);

// OrbitControls permite girar, aproximar e inspecionar a caneca manualmente.
const controls = new OrbitControls(camera, renderer.domElement);
// Damping deixa o movimento mais suave/inercial.
controls.enableDamping = true;
// Pan é desativado para manter o produto centralizado.
controls.enablePan = false;
// Distância mínima de zoom para não entrar dentro da caneca.
controls.minDistance = 3.2;
// Distância máxima de zoom para não afastar demais.
controls.maxDistance = 8;
// Ponto que a câmera orbita; ajustado depois pelo fitModelToViewer().
controls.target.set(0, 0.55, 0);

// Grupo externo que recebe a rotação automática; não altera a rotação base do modelo.
const objectRoot = new THREE.Group();
// Adiciona o grupo externo à cena.
scene.add(objectRoot);

// Grupo interno da caneca; recebe a rotação base e a rotação do slider "Girar caneca".
const modelRoot = new THREE.Group();
// modelRoot dentro de objectRoot permite somar rotação automática + rotação controlada.
objectRoot.add(modelRoot);

// Grupo do fallback geométrico usado caso mug.glb não carregue.
const fallbackMug = new THREE.Group();
// O fallback também fica em modelRoot para obedecer ao mesmo controle de rotação.
modelRoot.add(fallbackMug);

// Placeholder generico: corpo cilindrico, borda superior e alca simples.
// Corpo cilíndrico sem tampas, aproximando a superfície imprimível de uma caneca.
const bodyGeometry = new THREE.CylinderGeometry(1.05, 0.92, 2.15, 64, 1, true);
// Material branco do fallback; também recebe textura se o GLB falhar.
const bodyMaterial = new THREE.MeshStandardMaterial({
  // Cor base clara da caneca sem arte.
  color: 0xf7f8fb,
  // Rugosidade visual para brilho suave, não espelhado.
  roughness: 0.38,
  // Baixa metalicidade, pois cerâmica/plástico não deve parecer metal.
  metalness: 0.04,
  // DoubleSide permite ver a parede do cilindro por dentro/fora no fallback.
  side: THREE.DoubleSide,
});
// Mesh do corpo do fallback: geometria + material.
const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
// Permite que o corpo gere sombra.
body.castShadow = true;
// Permite que o corpo receba sombra.
body.receiveShadow = true;
// Adiciona o corpo ao grupo fallback.
fallbackMug.add(body);

// Geometria de torus para simular a borda superior da caneca fallback.
const rimGeometry = new THREE.TorusGeometry(1.05, 0.045, 16, 80);
// Borda usa o mesmo material branco do corpo.
const rim = new THREE.Mesh(rimGeometry, bodyMaterial);
// Coloca a borda no topo do cilindro.
rim.position.y = 1.075;
// Rotaciona o torus para ficar horizontal como boca da caneca.
rim.rotation.x = Math.PI / 2;
// Adiciona a borda ao fallback.
fallbackMug.add(rim);

// Disco/cilindro baixo para simular a base da caneca fallback.
const baseGeometry = new THREE.CylinderGeometry(0.92, 0.9, 0.08, 64);
// Mesh da base usando o material branco.
const base = new THREE.Mesh(baseGeometry, bodyMaterial);
// Move a base para a parte inferior da caneca.
base.position.y = -1.08;
// Permite que a base gere sombra.
base.castShadow = true;
// Adiciona a base ao fallback.
fallbackMug.add(base);

// Curva 3D que define o formato da alça do fallback.
const handleCurve = new THREE.CatmullRomCurve3([
  // Ponto superior onde a alça encosta no corpo.
  new THREE.Vector3(1.05, 0.62, 0),
  // Ponto externo superior da alça.
  new THREE.Vector3(1.72, 0.42, 0),
  // Ponto externo inferior da alça.
  new THREE.Vector3(1.76, -0.42, 0),
  // Ponto inferior onde a alça encosta no corpo.
  new THREE.Vector3(1.05, -0.62, 0),
]);
// TubeGeometry transforma a curva em um tubo, formando a alça visível.
const handleGeometry = new THREE.TubeGeometry(handleCurve, 42, 0.085, 18, false);
// Mesh da alça usando o mesmo material branco.
const handle = new THREE.Mesh(handleGeometry, bodyMaterial);
// Permite que a alça gere sombra.
handle.castShadow = true;
// Adiciona a alça ao fallback.
fallbackMug.add(handle);

// Pequeno retângulo azul decorativo do fallback, usado antes de qualquer arte.
const accentGeometry = new THREE.BoxGeometry(1.25, 0.62, 0.012);
// Material azul do retângulo decorativo.
const accentMaterial = new THREE.MeshStandardMaterial({
  // Azul visível na frente do fallback sem upload.
  color: 0x3267d6,
  // Rugosidade média para não refletir demais.
  roughness: 0.5,
});
// Mesh do detalhe decorativo.
const accent = new THREE.Mesh(accentGeometry, accentMaterial);
// Posiciona o detalhe na frente do cilindro fallback.
accent.position.set(0, 0.05, 1.01);
// Adiciona o detalhe ao fallback.
fallbackMug.add(accent);

// Luz direcional principal, parecida com uma fonte de luz de estúdio.
const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
// Posição da luz principal acima e à frente/lado do objeto.
keyLight.position.set(3, 5, 4);
// Ativa sombra gerada pela luz principal.
keyLight.castShadow = true;
// Insere a luz principal na cena.
scene.add(keyLight);

// Luz hemisférica preenche sombras com tons frios no céu e escuros no chão.
const fillLight = new THREE.HemisphereLight(0xbfd7ff, 0x202533, 1.2);
// Insere a luz de preenchimento na cena.
scene.add(fillLight);

// Geometria circular usada como piso/sombra abaixo da caneca.
const floorGeometry = new THREE.CircleGeometry(2.8, 80);
// Material fosco do piso.
const floorMaterial = new THREE.MeshStandardMaterial({ color: 0x253044, roughness: 0.75 });
// Mesh do piso circular.
const floor = new THREE.Mesh(floorGeometry, floorMaterial);
// Rotaciona o círculo para ficar horizontal no plano XZ.
floor.rotation.x = -Math.PI / 2;
// Posição inicial do piso; fitModelToViewer ajusta conforme o GLB.
floor.position.y = -1.14;
// Permite que o piso receba sombra da caneca.
floor.receiveShadow = true;
// Adiciona o piso à cena.
scene.add(floor);

// Atualiza o texto de status da arte e uma flag visual via data-state.
function updateArtworkStatus(message, state = "idle") {
  // Mostra a mensagem para o usuário.
  artworkStatus.textContent = message;
  // Permite estilizar estado: idle, loading, success, warning ou error.
  artworkStatus.dataset.state = state;
}

// Atualiza o texto de status do modelo 3D e seu estado visual.
function updateModelStatus(message, state = "idle") {
  // Mostra se o GLB carregou ou se fallback está sendo usado.
  modelStatus.textContent = message;
  // Armazena estado para CSS/semântica visual.
  modelStatus.dataset.state = state;
}

// Formata valores dos sliders removendo zeros finais para deixar a UI mais limpa.
function formatArtworkValue(name, value) {
  // Converte para número, fixa duas casas e remove zeros desnecessários.
  return Number(value).toFixed(2).replace(/\.?0+$/, "");
}

// Sincroniza o slider de rotação da caneca com o estado userRotationDegrees.
function syncMugRotationControl() {
  // Atualiza o valor do input range.
  mugRotationInput.value = userRotationDegrees;
  // Mostra o valor arredondado em graus no output.
  mugRotationOutput.textContent = `${Math.round(userRotationDegrees)}°`;
}

// Aplica a rotação visual do modelo, somando rotação base técnica e rotação do usuário.
function applyModelRotation() {
  // Converte a rotação base do modelo de graus para radianos, formato usado pelo Three.js.
  const baseRotationRadians = THREE.MathUtils.degToRad(MUG_MODEL_BASE_ROTATION_DEGREES);
  // Converte a rotação escolhida no slider de graus para radianos.
  const userRotationRadians = THREE.MathUtils.degToRad(userRotationDegrees);

  // Rotaciona o grupo inteiro da caneca/fallback no eixo Y.
  modelRoot.rotation.y = baseRotationRadians + userRotationRadians;
  // Atualiza o valor exibido no controle.
  syncMugRotationControl();
}

// Volta a rotação manual do usuário para zero, mantendo a rotação base do modelo.
function resetModelRotation() {
  // Restaura somente a parte controlada pelo usuário.
  userRotationDegrees = USER_MODEL_ROTATION_DEFAULT_DEGREES;
  // Reaplica base + usuário no modelRoot.
  applyModelRotation();
}

// Sincroniza sliders/checkboxes com o estado atual e habilita/desabilita conforme existe arte.
function syncArtworkControls() {
  // Só permite ajustes quando existe textura criada.
  const hasArtwork = Boolean(artworkTexture);

  // Percorre sliders de posição e escala.
  artworkControls.forEach((control) => {
    // Nome interno vem do data-artwork-control do HTML.
    const name = control.dataset.artworkControl;
    // Valor atual vem do objeto artworkTransform.
    const value = artworkTransform[name];

    // Desabilita o slider se ainda não há arte aplicada.
    control.disabled = !hasArtwork;
    // Mantém o input refletindo o estado interno.
    control.value = value;

    // Se existe output para esse controle, atualiza o texto exibido.
    if (artworkOutputs[name]) {
      // Exibe valor curto, por exemplo 1 em vez de 1.00.
      artworkOutputs[name].textContent = formatArtworkValue(name, value);
    }
  });

  // Percorre checkboxes de inversão horizontal/vertical.
  artworkToggles.forEach((control) => {
    // Desabilita o checkbox se ainda não há arte aplicada.
    control.disabled = !hasArtwork;
    // Marca/desmarca conforme o estado interno flipX/flipY.
    control.checked = Boolean(artworkTransform[control.dataset.artworkToggle]);
  });


  // O botão de reset só faz sentido quando existe arte ativa.
  resetArtworkAdjustmentsButton.disabled = !hasArtwork;
}

// Garante que o canvas intermediário e a CanvasTexture existam antes de aplicar arte.
function ensureArtworkCanvasTexture() {
  // Cria o canvas 2D uma única vez por arte carregada.
  if (!artworkCanvas) {
    // Canvas em memória, não aparece diretamente na página.
    artworkCanvas = document.createElement("canvas");
    // Define largura de alta resolução para a textura.
    artworkCanvas.width = ARTWORK_CANVAS_WIDTH;
    // Define altura de alta resolução para a textura.
    artworkCanvas.height = ARTWORK_CANVAS_HEIGHT;
    // Contexto usado para desenhar fundo, imagem, escala e flips.
    artworkCanvasContext = artworkCanvas.getContext("2d");
  }

  // Cria a textura Three.js apontando para o canvas se ainda não existir.
  if (!artworkTexture) {
    // CanvasTexture atualiza a textura a partir do conteúdo do canvas 2D.
    artworkTexture = new THREE.CanvasTexture(artworkCanvas);
    // Define espaço de cor correto para imagens comuns da web.
    artworkTexture.colorSpace = THREE.SRGBColorSpace;
    // flipY false evita inversão vertical automática na textura do Three.js.
    artworkTexture.flipY = false;
    // RepeatWrapping permite que o deslocamento horizontal atravesse a costura do UV.
    artworkTexture.wrapS = THREE.RepeatWrapping;
    // No eixo vertical, prende na borda para evitar mosaico de cima para baixo.
    artworkTexture.wrapT = THREE.ClampToEdgeWrapping;
    // Centro da textura usado se rotação fosse aplicada; mantido centralizado.
    artworkTexture.center.set(0.5, 0.5);
    // Offset inicial da textura no UV.
    artworkTexture.offset.set(0, 0);
    // Sem repetição visual adicional por padrão.
    artworkTexture.repeat.set(1, 1);
  }
}

// Redesenha a arte no canvas intermediário com posição, escala e flips atuais.
function redrawArtworkCanvas() {
  // Sem imagem ou contexto, não há o que desenhar.
  if (!artworkImage || !artworkCanvasContext) {
    return;
  }

  // Largura real do canvas de composição.
  const canvasWidth = artworkCanvas.width;
  // Altura real do canvas de composição.
  const canvasHeight = artworkCanvas.height;
  // Largura segura: fração do canvas onde a arte deve caber por padrão.
  const safeWidth = canvasWidth * ARTWORK_SAFE_WIDTH;
  // Altura segura: canvas menos margens superior e inferior.
  const safeHeight = canvasHeight * (1 - ARTWORK_SAFE_TOP - ARTWORK_SAFE_BOTTOM);
  // Posição Y inicial da área segura, calculada a partir da margem superior.
  const safeTop = canvasHeight * ARTWORK_SAFE_TOP;
  // Proporção original da imagem enviada pelo usuário.
  const imageAspect = artworkImage.naturalWidth / artworkImage.naturalHeight;
  // Proporção da área segura onde a imagem será encaixada.
  const safeAspect = safeWidth / safeHeight;
  // Largura base começa ocupando toda a largura segura.
  let baseWidth = safeWidth;
  // Altura base começa ocupando toda a altura segura.
  let baseHeight = safeHeight;

  // Se a imagem é mais larga que a área segura, limita pela largura.
  if (imageAspect > safeAspect) {
    // Calcula altura proporcional para não deformar a imagem.
    baseHeight = baseWidth / imageAspect;
  } else {
    // Se é mais alta/estreita, limita pela altura e calcula a largura proporcional.
    baseWidth = baseHeight * imageAspect;
  }

  // Largura final desenhada: base proporcional multiplicada pela Escala X.
  const drawWidth = baseWidth * Math.max(artworkTransform.scaleX, 0.01);
  // Altura final desenhada: base proporcional multiplicada pela Escala Y.
  const drawHeight = baseHeight * Math.max(artworkTransform.scaleY, 0.01);
  // Curso horizontal do slider; garante deslocamento útil mesmo quando a arte é larga.
  const horizontalTravel = Math.max((canvasWidth - Math.min(drawWidth, canvasWidth)) / 2, canvasWidth * 0.2);
  // Curso vertical do slider; evita deslocamento exagerado quando a arte é pequena.
  const verticalTravel = Math.max((canvasHeight - Math.min(drawHeight, canvasHeight)) / 2, safeHeight * 0.25);
  // Centro X final: centro do canvas + offsets base/início + slider Posição X.
  const centerX = canvasWidth / 2 +
  // Esta soma controla a aproximação horizontal da arte em relação à costura/alça no UV.
  (ARTWORK_BASE_OFFSET_X + ARTWORK_START_SIDE_OFFSET + artworkTransform.offsetX) * horizontalTravel;
  // Centro Y final: centro da área segura, invertendo o sentido visual do slider Y.
  const centerY = safeTop + safeHeight / 2 - artworkTransform.offsetY * verticalTravel;

  // Limpa tudo antes de redesenhar, evitando rastros de frames anteriores.
  artworkCanvasContext.clearRect(0, 0, canvasWidth, canvasHeight);
  // Define o fundo branco/transparente configurado para a textura.
  artworkCanvasContext.fillStyle = ARTWORK_CANVAS_BACKGROUND;
  // Preenche o canvas inteiro; áreas sem arte viram respiro branco na caneca.
  artworkCanvasContext.fillRect(0, 0, canvasWidth, canvasHeight);
  // Salva o estado do contexto antes de aplicar translate/scale.
  artworkCanvasContext.save();
  // Move a origem do desenho para o centro calculado da arte.
  artworkCanvasContext.translate(centerX, centerY);
  // Aplica espelhamento horizontal/vertical quando os checkboxes estão ativos.
  artworkCanvasContext.scale(artworkTransform.flipX ? -1 : 1, artworkTransform.flipY ? -1 : 1);
  // Desenha a imagem centralizada na origem transformada.
  artworkCanvasContext.drawImage(artworkImage, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
  // Restaura o contexto para remover transformações antes do próximo redraw.
  artworkCanvasContext.restore();

  // Informa ao Three.js que o conteúdo do canvas mudou e a textura precisa subir para a GPU.
  artworkTexture.needsUpdate = true;
}

// Aplica ajustes de textura e redesenha o canvas intermediário.
function applyArtworkTransform() {
  // Se ainda não existe textura, não há material para atualizar.
  if (!artworkTexture) {
    return;
  }

  // Offset UV da textura no material; mantido em zero para o canvas controlar a posição principal.
  artworkTexture.offset.set(0, 0);
  // Mantém uma única repetição lógica da textura no material.
  artworkTexture.repeat.set(1, 1);
  // Garante que não há rotação da textura no UV.
  artworkTexture.rotation = 0;
  // Redesenha a imagem no canvas com os valores atuais dos controles.
  redrawArtworkCanvas();
  // Marca a textura como atualizada após modificar offset/repeat/canvas.
  artworkTexture.needsUpdate = true;
}

// Reseta sliders, flips e rotação visual para os padrões atuais.
function resetArtworkSettings({ apply = true } = {}) {
  // Restaura posição, escala e flips da arte.
  artworkTransform = { ...defaultArtworkTransform };
  // Restaura o slider de rotação da caneca.
  resetModelRotation();
  // Atualiza inputs/outputs do HTML para refletir os padrões.
  syncArtworkControls();

  // Quando solicitado, redesenha a textura já com os padrões restaurados.
  if (apply) {
    applyArtworkTransform();
  }
}

// Libera textura, canvas e URL temporária da arte atual.
function disposeArtworkTexture() {
  // Se existe textura na GPU, libera seus recursos.
  if (artworkTexture) {
    artworkTexture.dispose();
    artworkTexture = null;
  }

  // Limpa o canvas em memória antes de descartar as referências.
  if (artworkCanvasContext && artworkCanvas) {
    artworkCanvasContext.clearRect(0, 0, artworkCanvas.width, artworkCanvas.height);
  }

  // Remove a referência para a imagem carregada.
  artworkImage = null;
  // Remove a referência para o canvas de composição.
  artworkCanvas = null;
  // Remove a referência para o contexto 2D.
  artworkCanvasContext = null;

  // Revoga a URL temporária criada com URL.createObjectURL.
  if (artworkObjectUrl) {
    URL.revokeObjectURL(artworkObjectUrl);
    artworkObjectUrl = null;
  }
}

// Remove textura aplicada no fallback geométrico e volta o material ao branco.
function resetFallbackMaterial() {
  // Remove o mapa de textura do material do corpo fallback.
  bodyMaterial.map = null;
  // Restaura a cor clara original do fallback.
  bodyMaterial.color.set(0xf7f8fb);
  // Pede ao Three.js para recompilar/atualizar o material.
  bodyMaterial.needsUpdate = true;
}

// Normaliza nomes para comparação sem diferenciar maiúsculas/minúsculas ou acentos.
function normalizeName(value = "") {
  // Converte para string, baixa caixa e remove diacríticos como ç/ã quando possível.
  return value.toString().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// Garante que material único e array de materiais sejam tratados da mesma forma.
function materialList(material) {
  // Se já é array, retorna como está; senão embrulha em array.
  return Array.isArray(material) ? material : [material];
}

// Tenta descobrir se um mesh do GLB representa a alça para não aplicar arte nele.
function meshLooksLikeHandle(mesh) {
  // Junta nome do mesh, nome do pai e nomes dos materiais como texto pesquisável.
  const names = [mesh.name, mesh.parent?.name, ...materialList(mesh.material).map((material) => material?.name)];
  // Normaliza tudo em uma única string para busca por palavras-chave.
  const searchableName = names.map(normalizeName).join(" ");

  // Retorna true se algum termo conhecido de alça aparece no nome/material.
  return HANDLE_NAME_PARTS.some((part) => searchableName.includes(normalizeName(part)));
}

// Conta vértices aproximados de um mesh para exibir no diagnóstico.
function getMeshVertexCount(mesh) {
  // Atributo position possui a contagem de vértices quando a geometria está disponível.
  return mesh.geometry?.attributes?.position?.count ?? 0;
}

// Converte material único ou lista de materiais em texto amigável para diagnóstico.
function getMaterialNames(material) {
  // Usa "sem nome" quando o material não veio nomeado no GLB.
  return materialList(material).map((item) => item?.name || "sem nome").join(", ");
}

// Mostra diagnóstico específico quando o GLB falha e o fallback geométrico é usado.
function setDiagnosticsFallback() {
  // Mensagem na página explicando que não há GLB para inspecionar.
  diagnosticsSummary.textContent = "Usando fallback geométrico, sem diagnóstico de GLB.";
  // Remove linhas antigas da tabela.
  diagnosticsBody.innerHTML = "";
  // Também registra no console para depuração técnica.
  console.log("Diagnóstico do modelo 3D: usando fallback geométrico, sem diagnóstico de GLB.");
}

// Percorre o GLB carregado e preenche tabela/console com meshes e materiais encontrados.
function renderModelDiagnostics(model) {
  // Lista local com dados de cada mesh.
  const diagnostics = [];

  // traverse visita todos os filhos do scene graph do GLB.
  model.traverse((child) => {
    // Ignora objetos que não são meshes renderizáveis.
    if (!child.isMesh) {
      return;
    }

    // Guarda dados úteis para entender estrutura do modelo.
    diagnostics.push({
      // Nome do mesh no GLB.
      mesh: child.name || "sem nome",
      // Nome(s) do(s) material(is) do mesh.
      material: getMaterialNames(child.material),
      // Contagem aproximada de vértices.
      vertices: getMeshVertexCount(child),
      // Indica se o filtro atual trataria esse mesh como alça.
      treatedAsHandle: meshLooksLikeHandle(child) ? "sim" : "não",
    });
  });

  // Atualiza resumo da página com quantidade de meshes encontrados.
  diagnosticsSummary.textContent = diagnostics.length
    ? `${diagnostics.length} mesh(es) encontrados no GLB.`
    : "Nenhum mesh encontrado no GLB.";
  // Limpa tabela antes de preencher com os dados atuais.
  diagnosticsBody.innerHTML = "";

  // Cria uma linha de tabela para cada mesh diagnosticado.
  diagnostics.forEach((item) => {
    // Linha HTML da tabela.
    const row = document.createElement("tr");
    // Valores que serão distribuídos nas colunas.
    const values = [item.mesh, item.material, item.vertices.toLocaleString("pt-BR"), item.treatedAsHandle];

    // Cria uma célula para cada valor.
    values.forEach((value) => {
      // Célula HTML da tabela.
      const cell = document.createElement("td");
      // Texto visível da célula.
      cell.textContent = value;
      // Adiciona a célula à linha.
      row.appendChild(cell);
    });

    // Adiciona a linha preenchida ao corpo da tabela.
    diagnosticsBody.appendChild(row);
  });

  // Exibe a mesma informação no console em formato de tabela.
  console.table(diagnostics);
}

// Clona um material do GLB/fallback e troca seu map pela textura da arte.
function cloneMaterialWithTexture(material, texture) {
  // Clonar evita modificar diretamente o material original armazenado.
  const nextMaterial = material.clone();

  // Só define map em materiais que possuem essa propriedade.
  if ("map" in nextMaterial) {
    nextMaterial.map = texture;
  }

  // Se o material tem cor base, força branco para a arte não ser tingida.
  if (nextMaterial.color) {
    nextMaterial.color.set(0xffffff);
  }

  // Informa ao Three.js que o material clonado mudou.
  nextMaterial.needsUpdate = true;
  // Retorna o material pronto para ser atribuído ao mesh.
  return nextMaterial;
}

// Clona material original armazenado para restaurar o GLB sem compartilhar instância mutável.
function cloneStoredMaterial(material) {
  // Cria nova instância do material original.
  const clonedMaterial = material.clone();
  // Garante atualização do material restaurado no renderer.
  clonedMaterial.needsUpdate = true;
  // Retorna o clone restaurável.
  return clonedMaterial;
}

// Restaura todos os materiais originais do GLB depois de remover ou trocar a arte.
function restoreGlbMaterials() {
  // Se o GLB ainda não carregou, não há materiais para restaurar.
  if (!glbModel) {
    return;
  }

  // Percorre cada objeto do GLB.
  glbModel.traverse((child) => {
    // Só processa meshes que receberam backup de material original.
    if (!child.isMesh || !child.userData.originalMaterial) {
      return;
    }

    // Se o mesh usa múltiplos materiais, restaura cada um individualmente.
    if (Array.isArray(child.userData.originalMaterial)) {
      child.material = child.userData.originalMaterial.map(cloneStoredMaterial);
      return;
    }

    // Restaura material único.
    child.material = cloneStoredMaterial(child.userData.originalMaterial);
  });
}

// Aplica a CanvasTexture nos meshes imprimíveis do GLB.
function applyTextureToGlb(texture) {
  // Lista de meshes que receberão a textura.
  const printableMeshes = [];

  // Percorre todos os filhos do GLB procurando meshes com material.
  glbModel.traverse((child) => {
    // Ignora objetos não renderizáveis ou sem material.
    if (!child.isMesh || !child.material) {
      return;
    }

    // Quando possível, não aplica arte em meshes identificados como alça.
    if (meshLooksLikeHandle(child)) {
      return;
    }

    // Guarda mesh como candidato a receber textura.
    printableMeshes.push(child);
  });

  // Sem mesh compatível, sinaliza erro para o fluxo de aplicação.
  if (!printableMeshes.length) {
    throw new Error("No compatible GLB material found.");
  }

  // Aplica a arte no material/UV do GLB. Se o modelo for monolitico, a alca
  // so consegue ser preservada quando vier separada por nome/material.
  printableMeshes.forEach((child) => {
    // Alguns GLBs usam array de materiais por mesh.
    if (Array.isArray(child.material)) {
      // Clona e troca textura em cada material do array.
      child.material = child.material.map((material) => cloneMaterialWithTexture(material, texture));
    } else {
      // Clona e troca textura em material único.
      child.material = cloneMaterialWithTexture(child.material, texture);
    }
  });
}

// Aplica textura ao GLB quando existe, ou ao fallback geométrico quando o GLB falhou.
function applyTextureToActiveObject(texture) {
  // try/catch evita quebrar a página se o material do modelo for incompatível.
  try {
    // Prioriza o GLB real quando carregado.
    if (glbModel) {
      // Remove textura anterior antes de aplicar uma nova.
      restoreGlbMaterials();
      // Aplica a textura aos meshes imprimíveis do GLB.
      applyTextureToGlb(texture);
      return;
    }

    // Fallback: aplica textura diretamente no corpo cilíndrico simples.
    bodyMaterial.map = texture;
    // Deixa o material branco para não alterar as cores da arte.
    bodyMaterial.color.set(0xffffff);
    // Solicita atualização do material fallback.
    bodyMaterial.needsUpdate = true;
  } catch (error) {
    // Mostra erro discreto na interface se a textura não puder ser aplicada.
    updateArtworkStatus("Erro ao aplicar textura", "error");
  }
}

// Remove a arte ativa e volta GLB/fallback ao estado sem textura.
function resetArtwork() {
  // Libera textura, canvas e imagem carregada.
  disposeArtworkTexture();
  // Remove map do fallback, se ele estiver em uso.
  resetFallbackMaterial();
  // Restaura materiais originais do GLB.
  restoreGlbMaterials();

  // Limpa o input file para permitir reenviar o mesmo arquivo depois.
  if (artworkInput) {
    artworkInput.value = "";
  }

  // Reseta controles sem tentar reaplicar textura já removida.
  resetArtworkSettings({ apply: false });
  // Atualiza status da arte na UI.
  updateArtworkStatus("Nenhuma arte aplicada");
}

// Enquadra, centraliza e escala automaticamente o GLB dentro do viewer.
function fitModelToViewer(model) {
  // Bounding box inicial mede tamanho e centro do modelo como ele veio do GLB.
  const box = new THREE.Box3().setFromObject(model);
  // Vetor com largura, altura e profundidade do modelo.
  const size = box.getSize(new THREE.Vector3());
  // Centro geométrico do modelo antes de reposicionar.
  const center = box.getCenter(new THREE.Vector3());
  // Maior eixo evita divisão por zero e define a escala proporcional.
  const largestSide = Math.max(size.x, size.y, size.z, 0.001);
  // Fator que faz o maior eixo chegar no tamanho visual alvo.
  const scale = GLB_DISPLAY_SIZE / largestSide;

  // Centraliza o GLB na origem já considerando a escala aplicada ao grupo.
  model.scale.setScalar(scale);
  // Move o modelo para que seu centro fique perto da origem após escala.
  model.position.copy(center).multiplyScalar(-scale);
  // Atualiza matrizes para a próxima bounding box refletir escala/posição finais.
  model.updateMatrixWorld(true);

  // Bounding box já com modelo centralizado e escalado.
  const fittedBox = new THREE.Box3().setFromObject(model);
  // Tamanho final do modelo na cena.
  const fittedSize = fittedBox.getSize(new THREE.Vector3());
  // Centro final usado como target dos controles.
  const fittedCenter = fittedBox.getCenter(new THREE.Vector3());
  // Maior eixo final ajuda a calcular distância segura da câmera.
  const fittedLargestSide = Math.max(fittedSize.x, fittedSize.y, fittedSize.z, GLB_DISPLAY_SIZE);
  // FOV vertical da câmera convertido para radianos.
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  // FOV horizontal derivado do FOV vertical e aspect ratio atual.
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
  // Distância necessária para caber no eixo vertical.
  const verticalDistance = fittedSize.y / (2 * Math.tan(verticalFov / 2));
  // Distância necessária para caber no eixo horizontal.
  const horizontalDistance = fittedSize.x / (2 * Math.tan(horizontalFov / 2));
  // Distância final da câmera com padding para respiro visual.
  const cameraDistance = Math.max(verticalDistance, horizontalDistance, fittedLargestSide) * CAMERA_FIT_PADDING;

  // Posiciona o piso logo abaixo da base real do modelo.
  floor.position.y = fittedBox.min.y - 0.04;
  // Faz OrbitControls orbitar o centro real do modelo.
  controls.target.copy(fittedCenter);
  // Ajusta zoom mínimo proporcional ao tamanho enquadrado.
  controls.minDistance = Math.max(cameraDistance * 0.45, 1.2);
  // Ajusta zoom máximo proporcional ao tamanho enquadrado.
  controls.maxDistance = Math.max(cameraDistance * 2.4, controls.minDistance + 1);
  // Posiciona a câmera à frente e levemente acima do centro do modelo.
  camera.position.set(fittedCenter.x, fittedCenter.y + fittedLargestSide * 0.18, fittedCenter.z + cameraDistance);
  // Plano próximo proporcional evita clipping perto demais.
  camera.near = Math.max(cameraDistance / 100, 0.01);
  // Plano distante grande o bastante para manter objeto e piso visíveis.
  camera.far = Math.max(cameraDistance * 100, 100);
  // Aplica alterações de near/far/aspect/FOV na câmera.
  camera.updateProjectionMatrix();
  // Atualiza controles após trocar target e câmera.
  controls.update();
}

// Armazena cópias dos materiais originais do GLB para restaurar ao remover arte.
function storeOriginalGlbMaterials(model) {
  // Percorre todos os objetos do GLB.
  model.traverse((child) => {
    // Só meshes com material precisam de backup.
    if (!child.isMesh || !child.material) {
      return;
    }

    // Ativa geração de sombras para meshes do GLB.
    child.castShadow = true;
    // Ativa recebimento de sombras para meshes do GLB.
    child.receiveShadow = true;

    // Se o mesh tem vários materiais, clona todos.
    if (Array.isArray(child.material)) {
      child.userData.originalMaterial = child.material.map((material) => material.clone());
      return;
    }

    // Se o mesh tem material único, clona esse material.
    child.userData.originalMaterial = child.material.clone();
  });
}

// Exibe o modelo fallback quando o GLB não carrega.
function showFallbackModel() {
  // O fallback já está no modelRoot; aqui apenas torna visível.
  fallbackMug.visible = true;
}

// Carrega o GLB da caneca e prepara diagnóstico, materiais e enquadramento.
function loadGlbModel() {
  // Mostra estado de carregamento na UI.
  updateModelStatus("Carregando modelo 3D...", "loading");

  // Loader específico para arquivos GLTF/GLB.
  const loader = new GLTFLoader();
  // Inicia carregamento assíncrono do modelo.
  loader.load(
    // URL do arquivo GLB.
    MODEL_URL,
    // Callback de sucesso.
    (gltf) => {
      // Guarda a cena raiz do GLB para aplicar textura/restaurar depois.
      glbModel = gltf.scene;
      // Salva materiais originais antes de qualquer modificação.
      storeOriginalGlbMaterials(glbModel);
      // Preenche painel e console com informações dos meshes.
      renderModelDiagnostics(glbModel);
      // Garante renderer com dimensões atuais antes do enquadramento.
      resizeRenderer();
      // Centraliza, escala e reposiciona câmera para o GLB.
      fitModelToViewer(glbModel);

      // Esconde fallback porque o GLB real carregou.
      fallbackMug.visible = false;
      // Adiciona GLB ao grupo rotacionado da caneca.
      modelRoot.add(glbModel);
      // Atualiza status de sucesso.
      updateModelStatus("Modelo carregado", "success");

      // Se uma arte foi enviada antes do GLB terminar, aplica agora.
      if (artworkTexture) {
        applyTextureToActiveObject(artworkTexture);
      }
    },
    // Callback de progresso não usado no momento.
    undefined,
    // Callback de erro: mantém fallback geométrico.
    () => {
      // Torna fallback visível.
      showFallbackModel();
      // Informa que não há diagnóstico de GLB.
      setDiagnosticsFallback();
      // Atualiza status de fallback.
      updateModelStatus("Modelo não encontrado, usando fallback", "warning");
    },
  );
}

// Ajusta renderer e câmera ao tamanho real do container HTML.
function resizeRenderer() {
  // Mede o container onde o canvas está inserido.
  const { width, height } = container.getBoundingClientRect();
  // Evita largura zero, que quebraria o renderer/aspect.
  const safeWidth = Math.max(width, 1);
  // Evita altura zero, que quebraria o renderer/aspect.
  const safeHeight = Math.max(height, 1);

  // Redimensiona o canvas WebGL sem alterar CSS externo.
  renderer.setSize(safeWidth, safeHeight, false);
  // Atualiza proporção da câmera.
  camera.aspect = safeWidth / safeHeight;
  // Recalcula matriz de projeção da câmera.
  camera.updateProjectionMatrix();
}

// Loop de renderização: roda a cada frame via requestAnimationFrame.
function animate() {
  // Se rotação automática estiver ativa, gira o grupo externo lentamente.
  if (autoRotateEnabled) {
    objectRoot.rotation.y += 0.006;
  }

  // Atualiza damping e estado dos OrbitControls.
  controls.update();
  // Desenha a cena do ponto de vista da câmera.
  renderer.render(scene, camera);
  // Agenda o próximo frame.
  requestAnimationFrame(animate);
}

// Captura a imagem atual do canvas WebGL como preview PNG.
captureButton.addEventListener("click", () => {
  // Força render antes da captura para pegar o estado mais recente.
  renderer.render(scene, camera);
  // Converte o canvas WebGL em data URL PNG.
  previewImage.src = renderer.domElement.toDataURL("image/png");
  // Torna a imagem de preview visível via classe CSS.
  previewImage.classList.add("has-preview");
  // Oculta mensagem de preview vazio.
  previewEmpty.hidden = true;
});

// Reage quando o usuário seleciona um arquivo de arte.
artworkInput.addEventListener("change", (event) => {
  // Primeiro arquivo selecionado no input.
  const file = event.target.files[0];

  // Sem arquivo, remove arte atual e encerra.
  if (!file) {
    resetArtwork();
    return;
  }

  // Bloqueia formatos fora da lista permitida.
  if (!allowedArtworkTypes.has(file.type)) {
    resetArtwork();
    updateArtworkStatus("Formato inválido", "error");
    return;
  }

  // Informa ao usuário que a imagem será processada.
  updateArtworkStatus("Carregando imagem...", "loading");
  // Libera textura/canvas/URL anteriores antes de carregar nova arte.
  disposeArtworkTexture();
  // Cria URL temporária para o navegador carregar o arquivo local.
  artworkObjectUrl = URL.createObjectURL(file);

  // Image() permite saber dimensões naturais antes de desenhar no canvas.
  const nextImage = new Image();

  // Executa quando o navegador termina de carregar a imagem do upload.
  nextImage.onload = () => {
    // Guarda a imagem carregada como arte ativa.
    artworkImage = nextImage;
    // Garante canvas e CanvasTexture disponíveis.
    ensureArtworkCanvasTexture();
    // Reseta controles sem aplicar ainda, para começar de estado conhecido.
    resetArtworkSettings({ apply: false });
    // Desenha canvas e prepara parâmetros da textura.
    applyArtworkTransform();
    // Atualiza estado visual dos controles.
    syncArtworkControls();
    // Aplica a CanvasTexture ao GLB ou fallback.
    applyTextureToActiveObject(artworkTexture);

    // Se não houve erro durante aplicação, mostra sucesso.
    if (artworkStatus.dataset.state !== "error") {
      updateArtworkStatus("Arte aplicada com sucesso", "success");
    }
  };

  // Erro ao carregar imagem também limpa estado e avisa usuário.
  nextImage.onerror = () => {
    resetArtwork();
    updateArtworkStatus("Formato inválido", "error");
  };

  // Dispara o carregamento da imagem a partir da URL temporária.
  nextImage.src = artworkObjectUrl;
});

// Botão "Remover arte" volta tudo para estado sem textura.
removeArtworkButton.addEventListener("click", resetArtwork);

// Botão pausa/retoma apenas a rotação automática do objectRoot.
toggleRotationButton.addEventListener("click", () => {
  // Alterna o booleano que o loop animate() consulta.
  autoRotateEnabled = !autoRotateEnabled;
  // Atualiza texto do botão conforme estado atual.
  toggleRotationButton.textContent = autoRotateEnabled ? "Pausar rotação" : "Retomar rotação";
});

// Botão "Resetar ajustes" volta controles de arte/rotação para padrões.
resetArtworkAdjustmentsButton.addEventListener("click", () => {
  // Reseta e reaplica caso exista textura ativa.
  resetArtworkSettings();
});

// Slider "Girar caneca" muda somente a rotação do modelRoot.
mugRotationInput.addEventListener("input", () => {
  // Lê o valor em graus direto do input.
  userRotationDegrees = Number(mugRotationInput.value);
  // Reaplica rotação base + rotação do usuário.
  applyModelRotation();
});

// Sliders de posição/escala da arte redesenham o canvas intermediário.
artworkControls.forEach((control) => {
  // Cada input dispara em tempo real enquanto o slider se move.
  control.addEventListener("input", () => {
    // Atualiza propriedade correspondente no estado artworkTransform.
    artworkTransform[control.dataset.artworkControl] = Number(control.value);
    // Sincroniza outputs e valores visuais dos controles.
    syncArtworkControls();
    // Redesenha a textura com o novo valor.
    applyArtworkTransform();
  });
});

// Checkboxes de flip redesenham a arte com escala 2D negativa quando ativados.
artworkToggles.forEach((control) => {
  // Evento change dispara quando checkbox é marcado/desmarcado.
  control.addEventListener("change", () => {
    // Atualiza flipX ou flipY no estado interno.
    artworkTransform[control.dataset.artworkToggle] = control.checked;
    // Redesenha a textura com a inversão aplicada.
    applyArtworkTransform();
  });
});


// Estado inicial: controles desabilitados até existir arte.
syncArtworkControls();
// Aplica rotação base inicial do modelo/fallback.
applyModelRotation();

// ResizeObserver reage a mudanças no tamanho do container do canvas.
if ("ResizeObserver" in window) {
  // Observador chama resizeRenderer quando o container muda de tamanho.
  const resizeObserver = new ResizeObserver(resizeRenderer);
  // Começa a observar o container do viewer.
  resizeObserver.observe(container);
}

// Inicia carregamento do modelo GLB.
loadGlbModel();
// Também ajusta renderer em resize da janela.
window.addEventListener("resize", resizeRenderer);
// Faz um resize inicial para configurar canvas/câmera.
resizeRenderer();
// Inicia o loop de renderização contínua.
animate();
