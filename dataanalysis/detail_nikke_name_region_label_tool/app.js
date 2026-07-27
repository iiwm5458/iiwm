const GROUPS = [
  { id: "block", label: "对局 block", color: "#ff4646", kinds: ["matchBlock"] },
  { id: "panel", label: "阵容 / 赛果面板", color: "#00d8ff", kinds: ["rosterPanel", "detailPanel"] },
  { id: "player", label: "玩家昵称 / ID", color: "#ff50dc", kinds: ["playerNickname", "playerId", "playerIdFallback"] },
  { id: "team", label: "阵容整行 OCR", color: "#2896ff", kinds: ["teamRow"] },
  { id: "name", label: "妮姬名字", color: "#b969ff", kinds: ["nikkeNameSlot", "nikkeNameLabel"] },
  { id: "power", label: "妮姬战力", color: "#32eb73", kinds: ["powerSlot"] },
  { id: "collection", label: "藏品图标", color: "#ffdc28", kinds: ["collectionSlot"] },
  { id: "stat", label: "循环等级", color: "#f5f5f5", kinds: ["statRow", "statSlot"] },
  { id: "detail", label: "赛果页名字", color: "#ffaa2d", kinds: ["detailRound", "detailNameLeft", "detailNameRight"] },
  { id: "defeat", label: "战败贴图", color: "#ff2d2d", kinds: ["defeatStickerLeft", "defeatStickerRight"] },
];

const RESOLUTION_PRESETS = [
  {
    key: "1920x1080",
    label: "1920*1080",
    width: 15016,
    height: 9344,
    baseImage: "../../screenshots/1920x1080测试/64进32全部战斗数据（详）2026年7月2日.png",
  },
  { key: "1920x1200", label: "1920*1200", width: 15024, height: 9364, baseImage: "" },
  { key: "1920x1440", label: "1920*1440", width: 15024, height: 9364, baseImage: "" },
  { key: "2560x1080", label: "2560*1080", width: 15024, height: 9364, baseImage: "" },
  { key: "2560x1440", label: "2560*1440", width: 15024, height: 9364, baseImage: "" },
  {
    key: "3440x1440",
    label: "3440*1440",
    width: 15024,
    height: 9364,
    baseImage: "../../screenshots/2026年7月1日2/64进32全部战斗数据（详）2026年7月1日.png",
  },
  { key: "3840x2160", label: "3840*2160", width: 15024, height: 9364, baseImage: "" },
  {
    key: "overseas-1920x1080",
    label: "国际服 / 港澳台 1920*1080",
    width: 15304,
    height: 9276,
    clientProfile: "overseas",
    baseImage: "",
  },
  {
    key: "overseas-3440x1440",
    label: "国际服 / 港澳台 3440*1440",
    width: 15336,
    height: 9364,
    clientProfile: "overseas",
    baseImage: "",
  },
];

const DEFAULT_LAYOUT = {
  outerGroupGap: 56,
  matchColumnGap: 42,
  matchRowGap: 18,
};
// This specialized copy deliberately exposes only the first block column.
// Coordinates remain in the full 64->32 image coordinate system on export.
const SAMPLE_BLOCK_IDS = new Set(["g01m1", "g01m3", "g05m1", "g05m3"]);
const SAMPLE_SCOPE_LABEL = "左侧四个样本 block（G1M1、G1M3、G5M1、G5M3）";
const TEMPLATE_CONFIG = structuredClone(window.REGION_LABEL_CONFIG || {});
const TEMPLATE_WIDTH = Number(TEMPLATE_CONFIG.image_width || 1836);
const TEMPLATE_HEIGHT = Number(TEMPLATE_CONFIG.image_height || 2318);
const TEMPLATE_BOXES = (TEMPLATE_CONFIG.boxes || []).filter((box) => box.kind !== "matchBlock");
const MAX_UNDO_STEPS = 80;
const DETAIL_SYNC_KINDS = new Set(["detailRound", "detailNameLeft", "detailNameRight", "defeatStickerLeft", "defeatStickerRight"]);
const ROSTER_SYNC_KINDS = new Set(["teamRow", "nikkeNameSlot", "nikkeNameLabel", "powerSlot", "collectionSlot"]);
const CN_DETAIL_PANEL_X = [0.4019, 0.5992];
const OVERSEAS_DETAIL_PANEL_X = [0.3950, 0.6050];
const OVERSEAS_DEFEAT_X = {
  L: [0.031, 0.213],
  R: [0.795, 1.0],
};
const OVERSEAS_DEFEAT_Y = [
  [[0.0148, 0.0466], [0.0505, 0.0823], [0.0869, 0.1187], [0.1236, 0.1554], [0.1597, 0.1915]],
  [[0.2135, 0.2453], [0.2496, 0.2814], [0.2860, 0.3178], [0.3227, 0.3545], [0.3584, 0.3902]],
  [[0.4131, 0.4449], [0.4487, 0.4805], [0.4847, 0.5165], [0.5218, 0.5536], [0.5579, 0.5897]],
  [[0.6122, 0.6440], [0.6479, 0.6797], [0.6843, 0.7161], [0.7210, 0.7528], [0.7566, 0.7884]],
  [[0.8109, 0.8427], [0.8470, 0.8788], [0.8834, 0.9152], [0.9197, 0.9515], [0.9557, 0.9875]],
];
const OVERSEAS_COLLECTION_GRIDS = {
  "overseas-1920x1080": {
    blockWidth: 1871,
    blockHeight: 2296,
    x0: { L: [10, 152, 294, 436, 578], R: [1161, 1303, 1445, 1587, 1729] },
    y0: [720, 1018, 1316, 1614, 1912],
    width: 27,
    height: 29,
    bottomMatchDy: 11,
  },
  "overseas-3440x1440": {
    blockWidth: 1875,
    blockHeight: 2318,
    x0: { L: [11, 153, 295, 437, 579], R: [1166, 1308, 1450, 1592, 1734] },
    y0: [718, 1017, 1316, 1615, 1914],
    width: 26,
    height: 29,
    bottomMatchDy: 12,
  },
};

const KIND_TO_GROUP = new Map();
for (const group of GROUPS) {
  for (const kind of group.kinds) KIND_TO_GROUP.set(kind, group.id);
}
const GROUP_BY_ID = new Map(GROUPS.map((group) => [group.id, group]));
const DEFAULT_KIND_BY_GROUP = new Map(GROUPS.map((group) => [group.id, group.kinds[0]]));

const state = {
  profiles: new Map(),
  defaultProfiles: new Map(),
  currentResolution: "3440x1440",
  config: null,
  boxes: [],
  undoStack: [],
  activeGroup: "block",
  selectedId: "",
  zoom: 1,
  onlyActive: true,
  showLabels: false,
  showLocked: true,
  syncDetailRows: true,
  syncRosterRows: true,
  syncCollectionRows: true,
  syncCollectionRowSlots: false,
  syncSameAcrossBlocks: false,
  syncBlockScope: "all",
  syncBlockTransforms: true,
  drag: null,
  inspectorSnapshotArmed: true,
  inspectorSync: null,
  objectUrl: "",
};

const els = {
  resolutionSelect: document.getElementById("resolutionSelect"),
  backgroundFile: document.getElementById("backgroundFile"),
  backgroundHint: document.getElementById("backgroundHint"),
  groupButtons: document.getElementById("groupButtons"),
  onlyActive: document.getElementById("onlyActive"),
  showLabels: document.getElementById("showLabels"),
  showLocked: document.getElementById("showLocked"),
  syncDetailRows: document.getElementById("syncDetailRows"),
  syncRosterRows: document.getElementById("syncRosterRows"),
  syncCollectionRows: document.getElementById("syncCollectionRows"),
  syncCollectionRowSlots: document.getElementById("syncCollectionRowSlots"),
  syncSameAcrossBlocks: document.getElementById("syncSameAcrossBlocks"),
  syncBlockScope: document.getElementById("syncBlockScope"),
  syncBlockTransforms: document.getElementById("syncBlockTransforms"),
  outerGapInput: document.getElementById("outerGapInput"),
  matchColumnGapInput: document.getElementById("matchColumnGapInput"),
  matchRowGapInput: document.getElementById("matchRowGapInput"),
  gapStepInput: document.getElementById("gapStepInput"),
  applyGaps: document.getElementById("applyGaps"),
  rebuildBlocks: document.getElementById("rebuildBlocks"),
  outerGapMinus: document.getElementById("outerGapMinus"),
  outerGapPlus: document.getElementById("outerGapPlus"),
  columnGapMinus: document.getElementById("columnGapMinus"),
  columnGapPlus: document.getElementById("columnGapPlus"),
  rowGapMinusBlock: document.getElementById("rowGapMinusBlock"),
  rowGapPlusBlock: document.getElementById("rowGapPlusBlock"),
  rowGapStep: document.getElementById("rowGapStep"),
  rowGapMinus: document.getElementById("rowGapMinus"),
  rowGapPlus: document.getElementById("rowGapPlus"),
  undoStep: document.getElementById("undoStep"),
  resetDefault: document.getElementById("resetDefault"),
  resetActiveGroup: document.getElementById("resetActiveGroup"),
  addBox: document.getElementById("addBox"),
  duplicateBox: document.getElementById("duplicateBox"),
  deleteBox: document.getElementById("deleteBox"),
  lockBox: document.getElementById("lockBox"),
  collectionMode: document.getElementById("collectionMode"),
  previousBox: document.getElementById("previousBox"),
  nextBox: document.getElementById("nextBox"),
  annotationProgress: document.getElementById("annotationProgress"),
  saveJson: document.getElementById("saveJson"),
  savePng: document.getElementById("savePng"),
  importJson: document.getElementById("importJson"),
  selectedHint: document.getElementById("selectedHint"),
  labelInput: document.getElementById("labelInput"),
  xInput: document.getElementById("xInput"),
  yInput: document.getElementById("yInput"),
  wInput: document.getElementById("wInput"),
  hInput: document.getElementById("hInput"),
  noteInput: document.getElementById("noteInput"),
  viewport: document.getElementById("viewport"),
  stage: document.getElementById("stage"),
  baseImage: document.getElementById("baseImage"),
  emptyCanvas: document.getElementById("emptyCanvas"),
  overlay: document.getElementById("overlay"),
  zoomLabel: document.getElementById("zoomLabel"),
  metaLine: document.getElementById("metaLine"),
};

function init() {
  if (!TEMPLATE_CONFIG || !Array.isArray(TEMPLATE_CONFIG.boxes)) {
    alert("初始标注数据没有加载成功。");
    return;
  }
  els.baseImage.addEventListener("error", () => {
    if (!state.config?.base_image) return;
    els.emptyCanvas.classList.remove("hidden");
    els.backgroundHint.textContent = "默认底图路径不可用。请点击“更替当前分辨率底图”选择对应的大图；标注坐标不会被重置。";
  });
  for (const preset of RESOLUTION_PRESETS) {
    const profile = buildFullProfile(preset);
    state.profiles.set(preset.key, profile);
    state.defaultProfiles.set(preset.key, cloneProfile(profile));
  }
  renderResolutionOptions();
  switchResolution(state.currentResolution, false);
  bindEvents();
  renderAll();
}

function renderResolutionOptions() {
  els.resolutionSelect.innerHTML = "";
  for (const preset of RESOLUTION_PRESETS) {
    const option = document.createElement("option");
    option.value = preset.key;
    option.textContent = preset.label;
    els.resolutionSelect.appendChild(option);
  }
  els.resolutionSelect.value = state.currentResolution;
}

function buildFullProfile(preset) {
  const config = {
    version: 2,
    tool: "nikke_ocr_full_region_label_tool",
    mode: "full-image",
    resolution_key: preset.key,
    resolution_label: preset.label,
    stage_code: "group64",
    client_profile: preset.clientProfile || "cn",
    image_width: preset.width,
    image_height: preset.height,
    coordinate_unit: "px",
    base_image: preset.baseImage || "",
    background_name: preset.baseImage ? preset.baseImage.split("/").pop() : "",
    layout: structuredClone(DEFAULT_LAYOUT),
    boxes: [],
  };
  rebuildProfileBoxesFromTemplate(config);
  if (config.client_profile === "overseas") applyOverseasProfileGeometry(config);
  return config;
}

function rebuildProfileBoxesFromTemplate(config) {
  const blocks = buildGroup64Blocks(config.image_width, config.image_height, config.layout);
  const boxes = [];
  for (const block of blocks) {
    boxes.push({
      id: block.id,
      kind: "matchBlock",
      group: "block",
      label: `G${pad2(block.group_index)} M${block.match_index} block`,
      x: block.x,
      y: block.y,
      w: block.w,
      h: block.h,
      block_id: block.id,
      group_index: block.group_index,
      match_index: block.match_index,
      template_id: "matchBlock",
      locked: false,
      note: "",
    });
    for (const templateBox of TEMPLATE_BOXES) {
      const local = {
        x: Number(templateBox.x || 0) / TEMPLATE_WIDTH,
        y: Number(templateBox.y || 0) / TEMPLATE_HEIGHT,
        w: Number(templateBox.w || 0) / TEMPLATE_WIDTH,
        h: Number(templateBox.h || 0) / TEMPLATE_HEIGHT,
      };
      const id = `${block.id}__${templateBox.id || templateBox.kind}`;
      boxes.push(normalizeBox({
        ...templateBox,
        id,
        x: block.x + local.x * block.w,
        y: block.y + local.y * block.h,
        w: local.w * block.w,
        h: local.h * block.h,
        block_id: block.id,
        group_index: block.group_index,
        match_index: block.match_index,
        template_id: templateBox.id || `${templateBox.kind}:${templateBox.label || ""}`,
        local,
      }, boxes.length));
    }
  }
  config.boxes = boxes;
  config.blocks = blockBoxesFromConfig(config);
}

function setConfigBoxLocal(config, box, local) {
  const block = config.boxes.find((candidate) => candidate.kind === "matchBlock" && candidate.block_id === box.block_id);
  if (!block) return;
  box.local = { ...local };
  box.x = block.x + local.x * block.w;
  box.y = block.y + local.y * block.h;
  box.w = local.w * block.w;
  box.h = local.h * block.h;
}

function applyOverseasProfileGeometry(config) {
  const cnPanelWidth = CN_DETAIL_PANEL_X[1] - CN_DETAIL_PANEL_X[0];
  const overseasPanelWidth = OVERSEAS_DETAIL_PANEL_X[1] - OVERSEAS_DETAIL_PANEL_X[0];
  const collectionGrid = OVERSEAS_COLLECTION_GRIDS[config.resolution_key];
  for (const box of config.boxes) {
    if (!box.local || box.kind === "matchBlock") continue;
    const collectionMatch = String(box.label || "").match(/^([LR])R([1-5])P([1-5]) collection$/);
    if (collectionGrid && collectionMatch) {
      const side = collectionMatch[1];
      const row = Number(collectionMatch[2]) - 1;
      const slot = Number(collectionMatch[3]) - 1;
      const matchDy = box.match_index === 3 || box.match_index === 4 ? collectionGrid.bottomMatchDy : 0;
      setConfigBoxLocal(config, box, {
        x: collectionGrid.x0[side][slot] / collectionGrid.blockWidth,
        y: (collectionGrid.y0[row] + matchDy) / collectionGrid.blockHeight,
        w: collectionGrid.width / collectionGrid.blockWidth,
        h: collectionGrid.height / collectionGrid.blockHeight,
      });
      continue;
    }
    if (box.kind === "detailPanel") {
      setConfigBoxLocal(config, box, { x: OVERSEAS_DETAIL_PANEL_X[0], y: 0, w: overseasPanelWidth, h: 1 });
      continue;
    }
    const roundMatch = String(box.label || "").match(/^Detail round ([1-5])$/);
    if (roundMatch) {
      const round = Number(roundMatch[1]) - 1;
      setConfigBoxLocal(config, box, { x: OVERSEAS_DETAIL_PANEL_X[0], y: round / 5, w: overseasPanelWidth, h: 1 / 5 });
      continue;
    }
    const defeatMatch = String(box.label || "").match(/^Detail R([1-5]) ([LR]) defeat ([1-5])$/);
    if (defeatMatch) {
      const round = Number(defeatMatch[1]) - 1;
      const slot = Number(defeatMatch[3]) - 1;
      const [x0, x1] = OVERSEAS_DEFEAT_X[defeatMatch[2]];
      const [y0, y1] = OVERSEAS_DEFEAT_Y[round][slot];
      setConfigBoxLocal(config, box, { x: OVERSEAS_DETAIL_PANEL_X[0] + x0 * overseasPanelWidth, y: y0, w: (x1 - x0) * overseasPanelWidth, h: y1 - y0 });
      continue;
    }
    if (box.kind === "detailNameLeft" || box.kind === "detailNameRight") {
      const old = { ...box.local };
      const relativeX = (old.x - CN_DETAIL_PANEL_X[0]) / cnPanelWidth;
      setConfigBoxLocal(config, box, {
        x: OVERSEAS_DETAIL_PANEL_X[0] + relativeX * overseasPanelWidth,
        y: old.y,
        w: old.w / cnPanelWidth * overseasPanelWidth,
        h: old.h,
      });
    }
  }
  config.region_profile_note = "国际服 / 港澳台服当前运行基线：详细赛果中栏与 DISCONNECTED 贴图已采用海外专用坐标；其余区域沿用当前通用运行坐标，供后续精调。";
}

function buildGroup64Blocks(width, height, layout) {
  const outer = Math.max(0, Number(layout.outerGroupGap || 0));
  const colGap = Math.max(0, Number(layout.matchColumnGap || 0));
  const rowGap = Math.max(0, Number(layout.matchRowGap || 0));
  const groupW = Math.max(1, Math.floor((width - outer * 3) / 4));
  const groupH = Math.max(1, Math.floor((height - outer) / 2));
  const blocks = [];
  for (let groupRow = 0; groupRow < 2; groupRow += 1) {
    for (let groupCol = 0; groupCol < 4; groupCol += 1) {
      const groupIndex = groupRow * 4 + groupCol + 1;
      const gx0 = groupCol * (groupW + outer);
      const gy0 = groupRow * (groupH + outer);
      const gx1 = groupCol === 3 ? width : gx0 + groupW;
      const gy1 = groupRow === 1 ? height : gy0 + groupH;
      const gw = gx1 - gx0;
      const gh = gy1 - gy0;
      const cellW = Math.max(1, Math.floor((gw - colGap) / 2));
      const cellH = Math.max(1, Math.floor((gh - rowGap) / 2));
      for (let row = 0; row < 2; row += 1) {
        for (let col = 0; col < 2; col += 1) {
          const matchIndex = row * 2 + col + 1;
          const x0 = gx0 + col * (cellW + colGap);
          const y0 = gy0 + row * (cellH + rowGap);
          const x1 = gx0 + (col === 1 ? gw : col * (cellW + colGap) + cellW);
          const y1 = gy0 + (row === 1 ? gh : row * (cellH + rowGap) + cellH);
          blocks.push({
            id: `g${pad2(groupIndex)}m${matchIndex}`,
            group_index: groupIndex,
            match_index: matchIndex,
            x: x0,
            y: y0,
            w: x1 - x0,
            h: y1 - y0,
          });
        }
      }
    }
  }
  return blocks;
}

function isSampleBox(box) {
  return Boolean(box && SAMPLE_BLOCK_IDS.has(box.block_id || box.id));
}

function sampleBoxes() {
  return state.boxes.filter(isSampleBox);
}

function sampleStageBounds() {
  const fullWidth = Number(state.config?.image_width || 1);
  const fullHeight = Number(state.config?.image_height || 1);
  const blocks = state.boxes.filter((box) => box.kind === "matchBlock" && isSampleBox(box));
  const right = blocks.length ? Math.max(...blocks.map((box) => box.x + box.w)) : fullWidth;
  return {
    x: 0,
    y: 0,
    w: Math.max(1, Math.min(fullWidth, right + 6)),
    h: fullHeight,
  };
}

function sampleStageX(globalX) {
  return globalX - sampleStageBounds().x;
}

function switchResolution(key, saveCurrent = true) {
  if (saveCurrent && state.config) {
    state.config.boxes = state.boxes.map(cloneBox);
    state.profiles.set(state.currentResolution, cloneProfile(state.config));
  }
  state.currentResolution = key;
  state.config = cloneProfile(state.profiles.get(key));
  state.boxes = state.config.boxes.map((box, index) => normalizeBox(box, index));
  state.selectedId = "";
  els.resolutionSelect.value = key;
  updateGapInputs();
  loadProfileBaseImage();
  setZoom("fit");
  updateMeta();
  renderAll();
}

function normalizeBox(box, index) {
  const group = groupForKind(box.kind);
  const normalized = {
    id: box.id || `${box.kind || group}-${String(index + 1).padStart(4, "0")}`,
    kind: box.kind || DEFAULT_KIND_BY_GROUP.get(group) || group,
    group,
    label: box.label || "",
    x: Number(box.x) || 0,
    y: Number(box.y) || 0,
    w: Math.max(4, Number(box.w) || 40),
    h: Math.max(4, Number(box.h) || 40),
    block_id: box.block_id || "",
    group_index: Number(box.group_index || 0),
    match_index: Number(box.match_index || 0),
    template_id: box.template_id || box.id || `${box.kind || group}:${box.label || ""}`,
    local: box.local ? { ...box.local } : null,
    locked: Boolean(box.locked),
    note: box.note || "",
  };
  if (!normalized.local && normalized.kind !== "matchBlock") updateLocalFromGlobal(normalized);
  return normalized;
}

function cloneBox(box) {
  return {
    id: box.id,
    kind: box.kind,
    group: box.group,
    label: box.label,
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    block_id: box.block_id || "",
    group_index: box.group_index || 0,
    match_index: box.match_index || 0,
    template_id: box.template_id || "",
    local: box.local ? { ...box.local } : null,
    locked: Boolean(box.locked),
    note: box.note || "",
  };
}

function cloneProfile(profile) {
  return structuredClone(profile);
}

function snapshotState() {
  return {
    config: cloneProfile(state.config),
    boxes: state.boxes.map(cloneBox),
    selectedId: state.selectedId,
    activeGroup: state.activeGroup,
    currentResolution: state.currentResolution,
  };
}

function pushUndo() {
  state.undoStack.push(snapshotState());
  if (state.undoStack.length > MAX_UNDO_STEPS) state.undoStack.shift();
  updateUndoButton();
}

function restoreSnapshot(snapshot) {
  state.config = cloneProfile(snapshot.config);
  state.boxes = snapshot.boxes.map(cloneBox);
  state.selectedId = snapshot.selectedId || "";
  state.activeGroup = snapshot.activeGroup || state.activeGroup;
  state.currentResolution = snapshot.currentResolution || state.currentResolution;
  state.profiles.set(state.currentResolution, cloneProfile(state.config));
  updateGapInputs();
  updateMeta();
  renderAll();
}

function undoStep() {
  const snapshot = state.undoStack.pop();
  if (!snapshot) return;
  restoreSnapshot(snapshot);
  updateUndoButton();
}

function updateUndoButton() {
  els.undoStep.disabled = state.undoStack.length === 0;
  els.undoStep.textContent = state.undoStack.length ? `撤销上一步(${state.undoStack.length})` : "撤销上一步";
}

function groupForKind(kind) {
  return KIND_TO_GROUP.get(kind) || (GROUP_BY_ID.has(kind) ? kind : "name");
}

function bindEvents() {
  els.resolutionSelect.addEventListener("change", () => switchResolution(els.resolutionSelect.value));
  els.backgroundFile.addEventListener("change", loadBackgroundFile);
  for (const [element, key] of [
    [els.onlyActive, "onlyActive"],
    [els.showLabels, "showLabels"],
    [els.showLocked, "showLocked"],
    [els.syncDetailRows, "syncDetailRows"],
    [els.syncRosterRows, "syncRosterRows"],
    [els.syncCollectionRows, "syncCollectionRows"],
    [els.syncCollectionRowSlots, "syncCollectionRowSlots"],
    [els.syncSameAcrossBlocks, "syncSameAcrossBlocks"],
    [els.syncBlockTransforms, "syncBlockTransforms"],
  ]) {
    element.addEventListener("change", () => {
      state[key] = element.checked;
      renderBoxes();
    });
  }
  els.syncBlockScope.addEventListener("change", () => {
    state.syncBlockScope = els.syncBlockScope.value === "row8" ? "row8" : "all";
  });
  els.undoStep.addEventListener("click", undoStep);
  els.resetDefault.addEventListener("click", resetDefault);
  els.resetActiveGroup.addEventListener("click", resetActiveGroup);
  els.addBox.addEventListener("click", addBox);
  els.duplicateBox.addEventListener("click", duplicateSelected);
  els.deleteBox.addEventListener("click", deleteSelected);
  els.lockBox.addEventListener("click", toggleLockSelected);
  els.collectionMode.addEventListener("click", activateCollectionMode);
  els.previousBox.addEventListener("click", () => selectRelativeBox(-1));
  els.nextBox.addEventListener("click", () => selectRelativeBox(1));
  els.saveJson.addEventListener("click", saveJson);
  els.savePng.addEventListener("click", savePng);
  els.importJson.addEventListener("change", importJson);
  els.applyGaps.addEventListener("click", applyGapInputs);
  els.rebuildBlocks.addEventListener("click", () => {
    pushUndo();
    rebuildBlocksFromLayout();
    renderAll();
  });
  els.outerGapMinus.addEventListener("click", () => adjustLayoutGap("outerGroupGap", -1));
  els.outerGapPlus.addEventListener("click", () => adjustLayoutGap("outerGroupGap", 1));
  els.columnGapMinus.addEventListener("click", () => adjustLayoutGap("matchColumnGap", -1));
  els.columnGapPlus.addEventListener("click", () => adjustLayoutGap("matchColumnGap", 1));
  els.rowGapMinusBlock.addEventListener("click", () => adjustLayoutGap("matchRowGap", -1));
  els.rowGapPlusBlock.addEventListener("click", () => adjustLayoutGap("matchRowGap", 1));
  els.rowGapMinus.addEventListener("click", () => adjustRowGap(-1));
  els.rowGapPlus.addEventListener("click", () => adjustRowGap(1));

  for (const input of [els.labelInput, els.noteInput]) {
    input.addEventListener("focus", armInspectorSnapshot);
    input.addEventListener("input", applyInspector);
  }
  for (const input of [els.xInput, els.yInput, els.wInput, els.hInput]) {
    input.addEventListener("focus", armInspectorSnapshot);
    input.addEventListener("change", applyInspector);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") input.blur();
    });
  }
  document.querySelectorAll("[data-zoom]").forEach((button) => {
    button.addEventListener("click", () => setZoom(button.dataset.zoom));
  });
  window.addEventListener("resize", () => {
    if (els.zoomLabel.dataset.mode === "fit") setZoom("fit");
  });
  document.addEventListener("keydown", handleKeyDown);
  document.addEventListener("pointermove", handlePointerMove);
  document.addEventListener("pointerup", endDrag);
}

function renderAll() {
  applyZoom();
  if (els.syncBlockScope) els.syncBlockScope.value = state.syncBlockScope;
  renderGroupButtons();
  renderBoxes();
  updateInspector();
  updateUndoButton();
  updateAnnotationProgress();
}

function renderGroupButtons() {
  els.groupButtons.innerHTML = "";
  for (const group of GROUPS) {
    const count = sampleBoxes().filter((box) => box.group === group.id).length;
    const button = document.createElement("button");
    button.className = `group-button${state.activeGroup === group.id ? " active" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <span class="swatch" style="background:${group.color}"></span>
      <span>${group.label}</span>
      <span class="count">${count}</span>
    `;
    button.addEventListener("click", () => {
      state.activeGroup = group.id;
      renderGroupButtons();
      renderBoxes();
    });
    els.groupButtons.appendChild(button);
  }
}

function renderBoxes() {
  els.overlay.innerHTML = "";
  const fragment = document.createDocumentFragment();
  const bounds = sampleStageBounds();
  for (const box of sampleBoxes()) {
    const hidden = shouldHide(box);
    const div = document.createElement("div");
    div.className = [
      "box",
      box.kind === "matchBlock" ? "block-box" : "",
      box.kind === "collectionSlot" ? "collection-box" : "",
      hidden ? "hidden" : "",
      box.locked ? "locked" : "",
      box.id === state.selectedId ? "selected" : "",
    ].filter(Boolean).join(" ");
    div.dataset.id = box.id;
    div.style.setProperty("--box-color", colorForBox(box));
    div.style.left = `${(box.x - bounds.x) * state.zoom}px`;
    div.style.top = `${(box.y - bounds.y) * state.zoom}px`;
    div.style.width = `${box.w * state.zoom}px`;
    div.style.height = `${box.h * state.zoom}px`;
    const label = document.createElement("div");
    label.className = `box-label${state.showLabels ? "" : " off"}`;
    label.textContent = box.label || box.kind;
    div.appendChild(label);
    for (const handle of ["nw", "n", "ne", "e", "se", "s", "sw", "w"]) {
      const h = document.createElement("div");
      h.className = `handle ${handle}`;
      h.dataset.handle = handle;
      div.appendChild(h);
    }
    div.addEventListener("pointerdown", (event) => beginDrag(event, box.id));
    fragment.appendChild(div);
  }
  els.overlay.appendChild(fragment);
  updateAnnotationProgress();
}

function shouldHide(box) {
  if (box.locked && !state.showLocked) return true;
  if (state.onlyActive && box.group !== state.activeGroup) return true;
  return false;
}

function colorForBox(box) {
  return GROUP_BY_ID.get(box.group)?.color || "#ffffff";
}

function beginDrag(event, id) {
  const box = findBox(id);
  if (!box) return;
  selectBox(id);
  if (box.locked) return;
  event.preventDefault();
  pushUndo();
  state.drag = {
    id,
    handle: event.target?.dataset?.handle || "move",
    startX: event.clientX,
    startY: event.clientY,
    original: cloneBox(box),
    syncPeers: syncPeersForBox(box),
  };
}

function handlePointerMove(event) {
  if (!state.drag) return;
  const box = findBox(state.drag.id);
  if (!box || box.locked) return;
  const dx = (event.clientX - state.drag.startX) / state.zoom;
  const dy = (event.clientY - state.drag.startY) / state.zoom;
  const next = clampBox(resizeBox(state.drag.original, state.drag.handle, dx, dy));
  if (box.kind === "matchBlock") {
    moveBlockWithChildren(box, state.drag.original, next);
    if (state.syncBlockTransforms) syncOtherBlocks(state.drag.original, next, box.id);
  } else {
    Object.assign(box, next);
    updateLocalFromGlobal(box);
    applySyncedDelta(state.drag.original, box, state.drag.syncPeers);
    syncTemplateAcrossBlocks(box);
  }
  updateProfileAfterEdit();
  renderBoxes();
  updateInspector();
}

function endDrag() {
  state.drag = null;
}

function resizeBox(original, handle, dx, dy) {
  let { x, y, w, h } = original;
  if (handle === "move") return { x: x + dx, y: y + dy, w, h };
  if (handle.includes("w")) { x += dx; w -= dx; }
  if (handle.includes("e")) { w += dx; }
  if (handle.includes("n")) { y += dy; h -= dy; }
  if (handle.includes("s")) { h += dy; }
  if (w < 4) { x += w - 4; w = 4; }
  if (h < 4) { y += h - 4; h = 4; }
  return { x, y, w, h };
}

function clampBox(box) {
  const maxW = Number(state.config.image_width || 1);
  const maxH = Number(state.config.image_height || 1);
  let x = Math.max(0, Math.min(maxW - 4, Number(box.x) || 0));
  let y = Math.max(0, Math.min(maxH - 4, Number(box.y) || 0));
  let w = Math.max(4, Number(box.w) || 4);
  let h = Math.max(4, Number(box.h) || 4);
  if (x + w > maxW) w = maxW - x;
  if (y + h > maxH) h = maxH - y;
  return { x, y, w, h };
}

function moveBlockWithChildren(blockBox, originalBlock, nextBlock) {
  const sx = nextBlock.w / Math.max(1, originalBlock.w);
  const sy = nextBlock.h / Math.max(1, originalBlock.h);
  Object.assign(blockBox, nextBlock);
  for (const child of state.boxes) {
    if (child.id === blockBox.id || child.block_id !== blockBox.block_id) continue;
    child.x = nextBlock.x + (child.x - originalBlock.x) * sx;
    child.y = nextBlock.y + (child.y - originalBlock.y) * sy;
    child.w *= sx;
    child.h *= sy;
    updateLocalFromGlobal(child);
  }
}

function syncOtherBlocks(originalBlock, nextBlock, activeId) {
  const dx = nextBlock.x - originalBlock.x;
  const dy = nextBlock.y - originalBlock.y;
  const dw = nextBlock.w - originalBlock.w;
  const dh = nextBlock.h - originalBlock.h;
  for (const blockBox of state.boxes.filter((box) => box.kind === "matchBlock" && isSampleBox(box) && box.id !== activeId && !box.locked)) {
    const old = cloneBox(blockBox);
    const next = clampBox({ ...blockBox, x: blockBox.x + dx, y: blockBox.y + dy, w: blockBox.w + dw, h: blockBox.h + dh });
    moveBlockWithChildren(blockBox, old, next);
  }
}

function updateBoxElement(box) {
  const div = els.overlay.querySelector(`[data-id="${CSS.escape(box.id)}"]`);
  if (!div) return;
  const bounds = sampleStageBounds();
  div.style.left = `${(box.x - bounds.x) * state.zoom}px`;
  div.style.top = `${(box.y - bounds.y) * state.zoom}px`;
  div.style.width = `${box.w * state.zoom}px`;
  div.style.height = `${box.h * state.zoom}px`;
}

function selectBox(id) {
  state.selectedId = id;
  state.inspectorSnapshotArmed = true;
  state.inspectorSync = null;
  renderBoxes();
  updateInspector();
}

function orderedGroupBoxes(groupId = state.activeGroup, unlockedOnly = true) {
  return sampleBoxes()
    .filter((box) => box.group === groupId && (!unlockedOnly || !box.locked))
    .sort((left, right) => left.y - right.y || left.x - right.x || left.id.localeCompare(right.id));
}

function selectRelativeBox(direction) {
  const candidates = orderedGroupBoxes();
  if (!candidates.length) return;
  const index = candidates.findIndex((box) => box.id === state.selectedId);
  const nextIndex = index < 0 ? (direction > 0 ? 0 : candidates.length - 1) : (index + direction + candidates.length) % candidates.length;
  const next = candidates[nextIndex];
  selectBox(next.id);
  focusBoxInViewport(next);
}

function focusBoxInViewport(box) {
  if (!box) return;
  const bounds = sampleStageBounds();
  const targetLeft = Math.max(0, (box.x - bounds.x) * state.zoom - els.viewport.clientWidth / 2 + box.w * state.zoom / 2);
  const targetTop = Math.max(0, (box.y - bounds.y) * state.zoom - els.viewport.clientHeight / 2 + box.h * state.zoom / 2);
  els.viewport.scrollTo({ left: targetLeft, top: targetTop, behavior: "smooth" });
}

function activateCollectionMode() {
  state.activeGroup = "collection";
  state.onlyActive = true;
  state.showLabels = false;
  els.onlyActive.checked = true;
  els.showLabels.checked = false;
  renderGroupButtons();
  const selected = findBox(state.selectedId);
  if (!selected || selected.group !== "collection" || selected.locked) selectRelativeBox(1);
  else renderBoxes();
}

function updateAnnotationProgress() {
  if (!els.annotationProgress) return;
  const group = GROUP_BY_ID.get(state.activeGroup);
  const boxes = sampleBoxes().filter((box) => box.group === state.activeGroup);
  const locked = boxes.filter((box) => box.locked).length;
  const open = boxes.length - locked;
  els.annotationProgress.textContent = group ? `${group.label}：已确认 ${locked} / ${boxes.length}，待标注 ${open}` : "";
  if (els.collectionMode) els.collectionMode.classList.toggle("active", state.activeGroup === "collection");
}

function findBox(id) {
  return state.boxes.find((box) => box.id === id);
}

function blockForId(blockId) {
  return state.boxes.find((box) => box.kind === "matchBlock" && box.block_id === blockId);
}

function updateLocalFromGlobal(box) {
  if (!box || box.kind === "matchBlock" || !box.block_id) return;
  const block = blockForId(box.block_id);
  if (!block) return;
  box.local = {
    x: (box.x - block.x) / Math.max(1, block.w),
    y: (box.y - block.y) / Math.max(1, block.h),
    w: box.w / Math.max(1, block.w),
    h: box.h / Math.max(1, block.h),
  };
}

function setGlobalFromLocal(box, local = box.local) {
  if (!box || box.kind === "matchBlock" || !box.block_id || !local) return;
  const block = blockForId(box.block_id);
  if (!block) return;
  box.local = { ...local };
  box.x = block.x + local.x * block.w;
  box.y = block.y + local.y * block.h;
  box.w = local.w * block.w;
  box.h = local.h * block.h;
}

function detailSyncInfo(box) {
  if (!box || !DETAIL_SYNC_KINDS.has(box.kind)) return null;
  let match = String(box.label || "").match(/^Detail round ([1-5])$/);
  if (match) return { row: Number(match[1]), suffix: "round" };
  match = String(box.label || "").match(/^Detail R([1-5]) (.+)$/);
  if (match) return { row: Number(match[1]), suffix: match[2] };
  return null;
}

function detailSyncPeers(box) {
  if (!state.syncDetailRows) return [];
  const info = detailSyncInfo(box);
  if (!info || info.row !== 1) return [];
  return state.boxes
    .filter((candidate) => {
      if (candidate.id === box.id || candidate.locked || candidate.kind !== box.kind || candidate.block_id !== box.block_id) return false;
      const candidateInfo = detailSyncInfo(candidate);
      return candidateInfo && candidateInfo.row >= 2 && candidateInfo.suffix === info.suffix;
    })
    .map((candidate) => ({ id: candidate.id, original: cloneBox(candidate) }));
}

function rosterSyncInfo(box) {
  if (!box || !ROSTER_SYNC_KINDS.has(box.kind)) return null;
  let match = String(box.label || "").match(/^([LR]) team row ([1-5])$/);
  if (match) return { side: match[1], row: Number(match[2]), slot: 0, suffix: "teamRow", spacingGroup: "teamRow" };
  match = String(box.label || "").match(/^([LR])R([1-5])P([1-5]) (name slot|name label|power|collection)$/);
  if (match) {
    return {
      side: match[1],
      row: Number(match[2]),
      slot: Number(match[3]),
      suffix: `P${match[3]} ${match[4]}`,
      spacingGroup: match[4],
    };
  }
  return null;
}

function rosterSyncPeers(box) {
  const info = rosterSyncInfo(box);
  if (!info) return [];
  if (box.kind === "collectionSlot" ? !state.syncCollectionRows : !state.syncRosterRows) return [];
  return state.boxes
    .filter((candidate) => {
      if (candidate.id === box.id || candidate.locked || candidate.kind !== box.kind || candidate.block_id !== box.block_id) return false;
      const candidateInfo = rosterSyncInfo(candidate);
      return candidateInfo && candidateInfo.side === info.side && candidateInfo.suffix === info.suffix;
    })
    .map((candidate) => ({ id: candidate.id, original: cloneBox(candidate) }));
}

function collectionRowPeers(box) {
  if (box?.kind !== "collectionSlot" || !state.syncCollectionRowSlots) return [];
  const info = rosterSyncInfo(box);
  if (!info) return [];
  return state.boxes
    .filter((candidate) => {
      if (candidate.id === box.id || candidate.locked || candidate.kind !== "collectionSlot" || candidate.block_id !== box.block_id) return false;
      const candidateInfo = rosterSyncInfo(candidate);
      return candidateInfo && candidateInfo.side === info.side && candidateInfo.row === info.row;
    })
    .map((candidate) => ({ id: candidate.id, original: cloneBox(candidate) }));
}

function syncPeersForBox(box) {
  const peers = [...detailSyncPeers(box), ...rosterSyncPeers(box), ...collectionRowPeers(box)];
  return [...new Map(peers.map((peer) => [peer.id, peer])).values()];
}

function applySyncedDelta(original, current, peers) {
  if (!peers || !peers.length) return;
  const dx = current.x - original.x;
  const dy = current.y - original.y;
  const dw = current.w - original.w;
  const dh = current.h - original.h;
  const changed = [];
  for (const peer of peers) {
    const box = findBox(peer.id);
    if (!box || box.locked) continue;
    Object.assign(box, clampBox({ ...box, x: peer.original.x + dx, y: peer.original.y + dy, w: peer.original.w + dw, h: peer.original.h + dh }));
    updateLocalFromGlobal(box);
    changed.push(box);
  }
  for (const box of changed) syncTemplateAcrossBlocks(box);
}

function syncTemplateAcrossBlocks(box) {
  if (!state.syncSameAcrossBlocks || !box.template_id || box.kind === "matchBlock" || !box.local) return;
  for (const peer of state.boxes) {
    if (peer.id === box.id || peer.kind === "matchBlock" || peer.template_id !== box.template_id || peer.locked) continue;
    if (!isSampleBox(peer)) continue;
    if (!sameCrossBlockScope(box, peer)) continue;
    setGlobalFromLocal(peer, box.local);
  }
}

function sameCrossBlockScope(source, target) {
  if (state.syncBlockScope !== "row8") return true;
  return eightBlockRowKey(source) === eightBlockRowKey(target);
}

function eightBlockRowKey(box) {
  const groupIndex = Number(box.group_index || 0);
  const matchIndex = Number(box.match_index || 0);
  if (groupIndex <= 0 || matchIndex <= 0) return "";
  const groupRow = Math.floor((groupIndex - 1) / 4);
  const matchRow = Math.floor((matchIndex - 1) / 2);
  return `${groupRow}:${matchRow}`;
}

function syncLockAcrossBlocks(box) {
  if (!state.syncSameAcrossBlocks || !box.template_id) return;
  for (const peer of state.boxes) {
    if (peer.id === box.id || peer.kind !== box.kind || peer.template_id !== box.template_id) continue;
    if (!isSampleBox(peer)) continue;
    if (!sameCrossBlockScope(box, peer)) continue;
    peer.locked = box.locked;
  }
}

function rosterRowSpacingTargets(box) {
  const info = rosterSyncInfo(box);
  if (!info) return [];
  if (box.kind === "collectionSlot" ? !state.syncCollectionRows : !state.syncRosterRows) return [];
  return state.boxes
    .map((candidate) => ({ box: candidate, info: rosterSyncInfo(candidate) }))
    .filter((item) => item.info && !item.box.locked && item.box.block_id === box.block_id && item.info.side === info.side && item.info.spacingGroup === info.spacingGroup && item.box.kind === box.kind);
}

function detailRowSpacingTargets(box) {
  if (!state.syncDetailRows) return [];
  const selectedInfo = detailSyncInfo(box);
  if (!selectedInfo) return [];
  return state.boxes
    .map((candidate) => ({ box: candidate, info: detailSyncInfo(candidate) }))
    .filter((item) => item.info && !item.box.locked && item.box.block_id === box.block_id && DETAIL_SYNC_KINDS.has(item.box.kind));
}

function applyRowGap(targets, direction) {
  const step = Math.max(1, Number(els.rowGapStep?.value || 1)) * direction;
  pushUndo();
  for (const item of targets) {
    if (item.info.row <= 1) continue;
    Object.assign(item.box, clampBox({ ...item.box, y: item.box.y + (item.info.row - 1) * step }));
    updateLocalFromGlobal(item.box);
    if (state.syncSameAcrossBlocks) syncTemplateAcrossBlocks(item.box);
  }
  updateProfileAfterEdit();
  renderBoxes();
  updateInspector();
}

function adjustRowGap(direction) {
  const selected = findBox(state.selectedId);
  const detailTargets = detailRowSpacingTargets(selected);
  if (detailTargets.length) return applyRowGap(detailTargets, direction);
  const rosterTargets = rosterRowSpacingTargets(selected);
  if (rosterTargets.length) return applyRowGap(rosterTargets, direction);
  alert("请先选择阵容页的整行/名字/战力/藏品框，或赛果页的块/名字/战败贴图框。");
}

function updateInspector() {
  const box = findBox(state.selectedId);
  const disabled = !box;
  els.selectedHint.textContent = box ? `${box.label || box.kind} · ${box.kind}${box.block_id ? ` · ${box.block_id}` : ""}${box.locked ? " · locked" : ""}` : "未选择框";
  for (const input of [els.labelInput, els.xInput, els.yInput, els.wInput, els.hInput, els.noteInput]) {
    input.disabled = disabled || (box?.locked && input !== els.noteInput);
  }
  if (!box) {
    els.labelInput.value = "";
    els.xInput.value = "";
    els.yInput.value = "";
    els.wInput.value = "";
    els.hInput.value = "";
    els.noteInput.value = "";
    return;
  }
  els.labelInput.value = box.label;
  els.xInput.value = Math.round(box.x);
  els.yInput.value = Math.round(box.y);
  els.wInput.value = Math.round(box.w);
  els.hInput.value = Math.round(box.h);
  els.noteInput.value = box.note || "";
}

function armInspectorSnapshot() {
  state.inspectorSnapshotArmed = true;
  state.inspectorSync = null;
}

function applyInspector() {
  const box = findBox(state.selectedId);
  if (!box) return;
  if (state.inspectorSnapshotArmed) {
    pushUndo();
    state.inspectorSync = { original: cloneBox(box), peers: syncPeersForBox(box) };
    state.inspectorSnapshotArmed = false;
  }
  box.note = els.noteInput.value;
  if (!box.locked) {
    box.label = els.labelInput.value;
    const next = clampBox({ x: Number(els.xInput.value), y: Number(els.yInput.value), w: Number(els.wInput.value), h: Number(els.hInput.value) });
    if (box.kind === "matchBlock") {
      moveBlockWithChildren(box, state.inspectorSync?.original || cloneBox(box), next);
    } else {
      Object.assign(box, next);
      updateLocalFromGlobal(box);
      if (state.inspectorSync) applySyncedDelta(state.inspectorSync.original, box, state.inspectorSync.peers);
      syncTemplateAcrossBlocks(box);
    }
  }
  updateProfileAfterEdit();
  renderBoxes();
  updateInspector();
}

function resetDefault() {
  if (!confirm("确定要把当前分辨率恢复为内置默认标注区域吗？当前未保存的调整可以先保存 JSON 备份。")) return;
  pushUndo();
  const profile = cloneProfile(state.defaultProfiles.get(state.currentResolution));
  state.profiles.set(state.currentResolution, cloneProfile(profile));
  state.config = profile;
  state.boxes = state.config.boxes.map((box, index) => normalizeBox(box, index));
  state.selectedId = "";
  updateGapInputs();
  loadProfileBaseImage();
  renderAll();
}

function resetActiveGroup() {
  const group = GROUP_BY_ID.get(state.activeGroup);
  if (!group) return;
  if (!confirm(`确定要把“${group.label}”恢复为当前分辨率的内置默认值吗？其他类别不会变更。`)) return;
  const defaults = state.defaultProfiles.get(state.currentResolution)?.boxes || [];
  const defaultById = new Map(defaults.filter((box) => box.group === state.activeGroup).map((box) => [box.id, cloneBox(box)]));
  const currentIds = new Set(state.boxes.filter((box) => box.group === state.activeGroup).map((box) => box.id));
  if (![...currentIds].every((id) => defaultById.has(id)) || defaultById.size !== currentIds.size) {
    alert("当前类别含有自定义框，无法安全局部重置。请改用“重置当前分辨率默认值”。");
    return;
  }
  pushUndo();
  state.boxes = state.boxes.map((box) => defaultById.get(box.id) || box).map((box, index) => normalizeBox(box, index));
  state.selectedId = "";
  updateProfileAfterEdit();
  renderAll();
}

function addBox() {
  const group = GROUP_BY_ID.get(state.activeGroup);
  const kind = DEFAULT_KIND_BY_GROUP.get(state.activeGroup) || state.activeGroup;
  const rect = els.viewport.getBoundingClientRect();
  const bounds = sampleStageBounds();
  const centerX = bounds.x + (els.viewport.scrollLeft + rect.width / 2 - 24) / state.zoom;
  const centerY = bounds.y + (els.viewport.scrollTop + rect.height / 2 - 24) / state.zoom;
  const block = nearestBlock(centerX, centerY);
  const box = normalizeBox({
    id: `${kind}-${Date.now()}`,
    kind,
    label: `${group?.label || kind} new`,
    x: Math.max(0, centerX - 80),
    y: Math.max(0, centerY - 40),
    w: 160,
    h: 80,
    locked: false,
    block_id: block?.block_id || "",
    group_index: block?.group_index || 0,
    match_index: block?.match_index || 0,
    template_id: `${kind}-custom-${Date.now()}`,
  }, state.boxes.length);
  updateLocalFromGlobal(box);
  pushUndo();
  state.boxes.push(box);
  updateProfileAfterEdit();
  selectBox(box.id);
  renderGroupButtons();
}

function duplicateSelected() {
  const box = findBox(state.selectedId);
  if (!box) return;
  const copy = normalizeBox({ ...box, id: `${box.kind}-${Date.now()}`, label: `${box.label} copy`, x: box.x + 12, y: box.y + 12, locked: false, template_id: `${box.template_id || box.kind}-copy-${Date.now()}` }, state.boxes.length);
  updateLocalFromGlobal(copy);
  pushUndo();
  state.boxes.push(copy);
  updateProfileAfterEdit();
  selectBox(copy.id);
  renderGroupButtons();
}

function deleteSelected() {
  const box = findBox(state.selectedId);
  if (!box || box.locked) return;
  pushUndo();
  if (box.kind === "matchBlock") {
    state.boxes = state.boxes.filter((item) => item.id !== box.id && item.block_id !== box.block_id);
  } else {
    state.boxes = state.boxes.filter((item) => item.id !== box.id);
  }
  state.selectedId = "";
  updateProfileAfterEdit();
  renderAll();
}

function toggleLockSelected(autoAdvance = false) {
  const box = findBox(state.selectedId);
  if (!box) return;
  pushUndo();
  box.locked = !box.locked;
  syncLockAcrossBlocks(box);
  updateProfileAfterEdit();
  renderBoxes();
  updateInspector();
  if (autoAdvance && box.locked) selectRelativeBox(1);
}

function handleKeyDown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
    event.preventDefault();
    undoStep();
    return;
  }
  const activeTag = document.activeElement?.tagName?.toLowerCase();
  if (["input", "textarea", "select"].includes(activeTag)) return;
  if (event.key === "[") {
    event.preventDefault();
    selectRelativeBox(-1);
    return;
  }
  if (event.key === "]") {
    event.preventDefault();
    selectRelativeBox(1);
    return;
  }
  if (event.key.toLowerCase() === "c") {
    event.preventDefault();
    activateCollectionMode();
    return;
  }
  const box = findBox(state.selectedId);
  if (!box) return;
  if (event.key.toLowerCase() === "s") {
    event.preventDefault();
    toggleLockSelected(true);
    return;
  }
  if (box.locked) return;
  if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    deleteSelected();
    return;
  }
  const amount = event.shiftKey ? 10 : 1;
  const move = { ArrowLeft: [-amount, 0], ArrowRight: [amount, 0], ArrowUp: [0, -amount], ArrowDown: [0, amount] }[event.key];
  if (!move) return;
  event.preventDefault();
  pushUndo();
  const original = cloneBox(box);
  const peers = syncPeersForBox(box);
  if (box.kind === "matchBlock") {
    moveBlockWithChildren(box, original, clampBox({ ...box, x: box.x + move[0], y: box.y + move[1] }));
    if (state.syncBlockTransforms) syncOtherBlocks(original, box, box.id);
  } else {
    Object.assign(box, clampBox({ ...box, x: box.x + move[0], y: box.y + move[1] }));
    updateLocalFromGlobal(box);
    applySyncedDelta(original, box, peers);
    syncTemplateAcrossBlocks(box);
  }
  updateProfileAfterEdit();
  renderBoxes();
  updateInspector();
}

function setZoom(value) {
  if (value === "fit") {
    const bounds = sampleStageBounds();
    const w = bounds.w;
    const h = bounds.h;
    const availableW = Math.max(1, els.viewport.clientWidth - 64);
    const availableH = Math.max(1, els.viewport.clientHeight - 64);
    state.zoom = Math.max(0.03, Math.min(1.0, Math.min(availableW / w, availableH / h)));
    els.zoomLabel.dataset.mode = "fit";
  } else {
    state.zoom = Number(value) || 1;
    els.zoomLabel.dataset.mode = "manual";
  }
  applyZoom();
  renderBoxes();
}

function applyZoom() {
  const bounds = sampleStageBounds();
  const fullWidth = Number(state.config.image_width || 1);
  const fullHeight = Number(state.config.image_height || 1);
  els.stage.style.width = `${bounds.w * state.zoom}px`;
  els.stage.style.height = `${bounds.h * state.zoom}px`;
  els.baseImage.style.width = `${fullWidth * state.zoom}px`;
  els.baseImage.style.height = `${fullHeight * state.zoom}px`;
  els.zoomLabel.textContent = `${Math.round(state.zoom * 100)}%`;
}

function updateMeta() {
  const config = state.config || {};
  const blockCount = sampleBoxes().filter((box) => box.kind === "matchBlock").length;
  const profile = config.client_profile === "overseas" ? "海外服基线" : "国服基线";
  els.metaLine.textContent = `${profile} · ${config.resolution_label || state.currentResolution} · 原图 ${config.image_width}x${config.image_height} · ${blockCount} 个样本 block · ${sampleBoxes().length} 个可标注框`;
}

function updateGapInputs() {
  const layout = state.config?.layout || DEFAULT_LAYOUT;
  els.outerGapInput.value = Math.round(Number(layout.outerGroupGap || 0));
  els.matchColumnGapInput.value = Math.round(Number(layout.matchColumnGap || 0));
  els.matchRowGapInput.value = Math.round(Number(layout.matchRowGap || 0));
}

function applyGapInputs() {
  pushUndo();
  state.config.layout = {
    outerGroupGap: Math.max(0, Number(els.outerGapInput.value || 0)),
    matchColumnGap: Math.max(0, Number(els.matchColumnGapInput.value || 0)),
    matchRowGap: Math.max(0, Number(els.matchRowGapInput.value || 0)),
  };
  rebuildBlocksFromLayout();
  renderAll();
}

function adjustLayoutGap(key, direction) {
  const step = Math.max(1, Number(els.gapStepInput.value || 1)) * direction;
  pushUndo();
  state.config.layout[key] = Math.max(0, Number(state.config.layout[key] || 0) + step);
  updateGapInputs();
  rebuildBlocksFromLayout();
  renderAll();
}

function rebuildBlocksFromLayout() {
  for (const box of state.boxes) updateLocalFromGlobal(box);
  const newBlocks = buildGroup64Blocks(state.config.image_width, state.config.image_height, state.config.layout);
  for (const newBlock of newBlocks) {
    const blockBox = blockForId(newBlock.id);
    if (!blockBox) continue;
    Object.assign(blockBox, { x: newBlock.x, y: newBlock.y, w: newBlock.w, h: newBlock.h });
  }
  for (const box of state.boxes) {
    if (box.kind !== "matchBlock") setGlobalFromLocal(box);
  }
  updateProfileAfterEdit();
}

function blockBoxesFromConfig(config) {
  return (config.boxes || [])
    .filter((box) => box.kind === "matchBlock")
    .map((box) => ({
      id: box.block_id || box.id,
      group_index: Number(box.group_index || 0),
      match_index: Number(box.match_index || 0),
      x: round2(box.x),
      y: round2(box.y),
      w: round2(box.w),
      h: round2(box.h),
      bbox: [round2(box.x), round2(box.y), round2(box.x + box.w), round2(box.y + box.h)],
    }));
}

function updateProfileAfterEdit() {
  state.config.boxes = state.boxes.map(cloneBox);
  state.config.blocks = blockBoxesFromConfig(state.config);
  state.profiles.set(state.currentResolution, cloneProfile(state.config));
  updateMeta();
}

function exportConfig() {
  updateProfileAfterEdit();
  const bounds = sampleStageBounds();
  return {
    ...state.config,
    tool: "nikke_ocr_left_column_region_label_tool",
    mode: "left-column-four-blocks",
    sample_scope: {
      label: SAMPLE_SCOPE_LABEL,
      block_ids: [...SAMPLE_BLOCK_IDS],
      crop_in_source: {
        x: round2(bounds.x),
        y: round2(bounds.y),
        w: round2(bounds.w),
        h: round2(bounds.h),
      },
    },
    saved_at: new Date().toISOString(),
    coordinate_unit: "px",
    blocks: state.boxes
      .filter((box) => box.kind === "matchBlock" && isSampleBox(box))
      .map((box) => ({
        id: box.block_id || box.id,
        group_index: box.group_index,
        match_index: box.match_index,
        x: round2(box.x),
        y: round2(box.y),
        w: round2(box.w),
        h: round2(box.h),
        bbox: [round2(box.x), round2(box.y), round2(box.x + box.w), round2(box.y + box.h)],
      })),
    boxes: sampleBoxes().map((box) => ({
      id: box.id,
      kind: box.kind,
      group: box.group,
      label: box.label,
      x: round2(box.x),
      y: round2(box.y),
      w: round2(box.w),
      h: round2(box.h),
      normalized: {
        x: round6(box.x / state.config.image_width),
        y: round6(box.y / state.config.image_height),
        w: round6(box.w / state.config.image_width),
        h: round6(box.h / state.config.image_height),
      },
      block_id: box.block_id || "",
      group_index: box.group_index || 0,
      match_index: box.match_index || 0,
      template_id: box.template_id || "",
      local: box.local ? {
        x: round6(box.local.x),
        y: round6(box.local.y),
        w: round6(box.local.w),
        h: round6(box.local.h),
      } : null,
      locked: Boolean(box.locked),
      note: box.note || "",
    })),
  };
}

function saveJson() {
  const data = JSON.stringify(exportConfig(), null, 2);
  downloadBlob(data, `nikke_ocr_left_column_regions_${state.currentResolution}_${stamp()}.json`, "application/json");
}

function savePng() {
  const bounds = sampleStageBounds();
  const width = Math.max(1, Math.round(bounds.w));
  const height = Math.max(1, Math.round(bounds.h));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (els.baseImage.complete && els.baseImage.naturalWidth > 0) {
    ctx.drawImage(els.baseImage, bounds.x, bounds.y, width, height, 0, 0, width, height);
  } else {
    ctx.fillStyle = "#050b13";
    ctx.fillRect(0, 0, width, height);
  }
  ctx.lineWidth = 3;
  ctx.font = "22px Segoe UI, Arial";
  for (const box of sampleBoxes()) {
    if (shouldHide(box)) continue;
    const x = box.x - bounds.x;
    const y = box.y - bounds.y;
    ctx.strokeStyle = colorForBox(box);
    if (box.kind === "collectionSlot") {
      const points = [
        [x + box.w * 0.5, y],
        [x + box.w, y + box.h * 0.25],
        [x + box.w, y + box.h * 0.75],
        [x + box.w * 0.5, y + box.h],
        [x, y + box.h * 0.75],
        [x, y + box.h * 0.25],
      ];
      ctx.beginPath();
      points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
      ctx.closePath();
      ctx.stroke();
    } else {
      ctx.strokeRect(x, y, box.w, box.h);
    }
    if (state.showLabels && box.label) {
      ctx.fillStyle = "rgba(0,0,0,0.72)";
      const textWidth = ctx.measureText(box.label).width;
      ctx.fillRect(x, Math.max(0, y - 26), textWidth + 10, 26);
      ctx.fillStyle = colorForBox(box);
      ctx.fillText(box.label, x + 5, Math.max(20, y - 7));
    }
  }
  canvas.toBlob((blob) => {
    if (blob) downloadBlob(blob, `nikke_ocr_left_column_preview_${stamp()}.png`, "image/png");
  });
}

function importJson(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const imported = JSON.parse(String(reader.result || "{}"));
      if (!Array.isArray(imported.boxes)) throw new Error("missing boxes");
      pushUndo();
      if (imported.mode === "left-column-four-blocks") {
        const key = imported.resolution_key || state.currentResolution;
        const config = normalizeImportedSampleConfig(imported, key);
        state.profiles.set(key, cloneProfile(config));
        if (!RESOLUTION_PRESETS.some((preset) => preset.key === key)) {
          RESOLUTION_PRESETS.push({
            key,
            label: imported.resolution_label || key,
            width: config.image_width,
            height: config.image_height,
            clientProfile: config.client_profile || "cn",
            baseImage: "",
          });
          renderResolutionOptions();
        }
        switchResolution(key, false);
      } else if (imported.mode === "full-image") {
        const key = imported.resolution_key || state.currentResolution;
        const config = normalizeImportedFullConfig(imported, key);
        state.profiles.set(key, cloneProfile(config));
        if (!RESOLUTION_PRESETS.some((preset) => preset.key === key)) {
          RESOLUTION_PRESETS.push({ key, label: key, width: config.image_width, height: config.image_height, baseImage: config.base_image || "" });
          renderResolutionOptions();
        }
        switchResolution(key, false);
      } else {
        alert("未识别的 JSON 格式。请选择本工具导出的“四 Block JSON”。");
      }
    } catch (error) {
      alert(`导入失败：${error.message || error}`);
    }
  };
  reader.readAsText(file, "utf-8");
  event.target.value = "";
}

function normalizeImportedSampleConfig(imported, key) {
  const preset = RESOLUTION_PRESETS.find((candidate) => candidate.key === key) || {
    key,
    label: imported.resolution_label || key,
    width: Number(imported.image_width || 1),
    height: Number(imported.image_height || 1),
    clientProfile: imported.client_profile || "cn",
    baseImage: "",
  };
  const config = buildFullProfile({
    ...preset,
    width: Number(imported.image_width || preset.width || 1),
    height: Number(imported.image_height || preset.height || 1),
  });
  config.layout = { ...DEFAULT_LAYOUT, ...(imported.layout || {}) };
  rebuildProfileBoxesFromTemplate(config);
  if (config.client_profile === "overseas") applyOverseasProfileGeometry(config);
  const importedById = new Map((imported.boxes || []).map((box) => [box.id, normalizeBox(box, 0)]));
  config.boxes = config.boxes.map((box, index) => {
    const replacement = importedById.get(box.id);
    return normalizeBox(replacement || box, index);
  });
  config.blocks = blockBoxesFromConfig(config);
  config.base_image = "";
  config.background_name = imported.background_name || "";
  config.mode = "left-column-four-blocks";
  return config;
}

function normalizeImportedFullConfig(imported, key) {
  const config = {
    ...imported,
    version: 2,
    mode: "full-image",
    resolution_key: key,
    resolution_label: imported.resolution_label || key,
    stage_code: imported.stage_code || "group64",
    image_width: Number(imported.image_width || 1),
    image_height: Number(imported.image_height || 1),
    layout: { ...DEFAULT_LAYOUT, ...(imported.layout || {}) },
    boxes: (imported.boxes || []).map((box, index) => normalizeBox(box, index)),
  };
  config.blocks = blockBoxesFromConfig(config);
  return config;
}

function loadProfileBaseImage() {
  const src = state.config.base_image || "";
  if (state.objectUrl) {
    URL.revokeObjectURL(state.objectUrl);
    state.objectUrl = "";
  }
  if (!src) {
    els.baseImage.removeAttribute("src");
    els.emptyCanvas.classList.remove("hidden");
    els.backgroundHint.textContent = "当前分辨率未绑定默认底图。请点击“更替当前分辨率底图”选择图片。";
    return;
  }
  els.baseImage.src = src;
  els.emptyCanvas.classList.add("hidden");
  els.backgroundHint.textContent = `当前底图：${state.config.background_name || src}`;
}

function loadBackgroundFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.onload = () => {
    pushUndo();
    scaleProfileToImage(img.naturalWidth || img.width, img.naturalHeight || img.height);
    if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
    state.objectUrl = url;
    state.config.base_image = url;
    state.config.background_name = file.name;
    state.profiles.set(state.currentResolution, cloneProfile(state.config));
    els.baseImage.src = url;
    els.emptyCanvas.classList.add("hidden");
    els.backgroundHint.textContent = `当前底图：${file.name}`;
    setZoom("fit");
    renderAll();
  };
  img.onerror = () => {
    URL.revokeObjectURL(url);
    alert("底图读取失败，请换一张 PNG/JPG。");
  };
  img.src = url;
  event.target.value = "";
}

function scaleProfileToImage(newWidth, newHeight) {
  const oldWidth = Math.max(1, Number(state.config.image_width || 1));
  const oldHeight = Math.max(1, Number(state.config.image_height || 1));
  const sx = newWidth / oldWidth;
  const sy = newHeight / oldHeight;
  state.config.image_width = newWidth;
  state.config.image_height = newHeight;
  state.config.layout.outerGroupGap = round2(Number(state.config.layout.outerGroupGap || 0) * ((sx + sy) / 2));
  state.config.layout.matchColumnGap = round2(Number(state.config.layout.matchColumnGap || 0) * sx);
  state.config.layout.matchRowGap = round2(Number(state.config.layout.matchRowGap || 0) * sy);
  for (const box of state.boxes) {
    box.x *= sx;
    box.y *= sy;
    box.w *= sx;
    box.h *= sy;
  }
  updateGapInputs();
  for (const box of state.boxes) updateLocalFromGlobal(box);
  updateProfileAfterEdit();
}

function nearestBlock(x, y) {
  let best = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const block of state.boxes.filter((box) => box.kind === "matchBlock")) {
    const inside = x >= block.x && x <= block.x + block.w && y >= block.y && y <= block.y + block.h;
    if (inside) return block;
    const cx = block.x + block.w / 2;
    const cy = block.y + block.h / 2;
    const distance = Math.hypot(cx - x, cy - y);
    if (distance < bestDistance) {
      best = block;
      bestDistance = distance;
    }
  }
  return best;
}

function downloadBlob(content, filename, type) {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function round2(value) {
  return Math.round(Number(value) * 100) / 100;
}

function round6(value) {
  return Math.round(Number(value) * 1_000_000) / 1_000_000;
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function stamp() {
  const date = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

init();
