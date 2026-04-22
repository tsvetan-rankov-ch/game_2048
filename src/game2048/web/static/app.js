"use strict";

const DIRECTIONS = ["up", "down", "left", "right"];
const ARROW_TO_DIR = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  w: "up",
  s: "down",
  a: "left",
  d: "right",
};
const DIR_ARROW = { up: "\u2191", down: "\u2193", left: "\u2190", right: "\u2192" };

const els = {
  board: document.getElementById("board"),
  score: document.getElementById("score"),
  newGame: document.getElementById("new-game"),
  overlay: document.getElementById("overlay"),
  overlayTitle: document.getElementById("overlay-title"),
  overlaySubtitle: document.getElementById("overlay-subtitle"),
  overlayNew: document.getElementById("overlay-new"),
  hintBtn: document.getElementById("hint-btn"),
  hintOut: document.getElementById("hint-out"),
  hintScores: document.getElementById("hint-scores"),
  provider: document.getElementById("provider"),
  solveBtn: document.getElementById("solve-btn"),
  solveStatus: document.getElementById("solve-status"),
  solveLog: document.getElementById("solve-log"),
  fourProb: document.getElementById("four-prob"),
  fourProbVal: document.getElementById("four-prob-val"),
  providerStatus: document.getElementById("provider-status"),
};

const state = {
  providers: [],
  solving: false,
  status: "playing",
};

function dirLabel(dir) {
  return `${DIR_ARROW[dir]} ${dir[0].toUpperCase()}${dir.slice(1)}`;
}

function renderBoard(board) {
  els.board.innerHTML = "";
  for (const row of board) {
    for (const v of row) {
      const cell = document.createElement("div");
      cell.className = "cell" + (v ? ` v${v}` : "");
      cell.textContent = v ? String(v) : "";
      els.board.appendChild(cell);
    }
  }
}

function renderOverlay(status) {
  if (status === "playing") {
    els.overlay.hidden = true;
    return;
  }
  els.overlay.hidden = false;
  if (status === "won") {
    els.overlayTitle.textContent = "You won!";
    els.overlaySubtitle.textContent = "Reached 2048. Start a new game?";
  } else {
    els.overlayTitle.textContent = "Game over";
    els.overlaySubtitle.textContent = "No moves left.";
  }
}

function renderProviders(providers) {
  const current = els.provider.value || "local";
  els.provider.innerHTML = "";
  for (const p of providers) {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.configured ? p.label : `${p.label} (not configured)`;
    opt.disabled = !p.configured;
    els.provider.appendChild(opt);
  }
  if ([...els.provider.options].some((o) => o.value === current && !o.disabled)) {
    els.provider.value = current;
  } else {
    els.provider.value = "local";
  }

  els.providerStatus.innerHTML = "";
  for (const p of providers) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = p.label;
    const status = document.createElement("span");
    status.textContent = p.configured ? "configured" : "not set";
    status.className = p.configured ? "configured" : "missing";
    li.appendChild(label);
    li.appendChild(status);
    els.providerStatus.appendChild(li);
  }
}

function applyState(s) {
  state.providers = s.providers;
  state.solving = s.solving;
  state.status = s.status;
  renderBoard(s.board);
  els.score.textContent = String(s.score);
  renderOverlay(s.status);
  renderProviders(s.providers);
  els.solveStatus.textContent = s.solving ? "solving..." : (s.status === "playing" ? "idle" : s.status);
  els.solveBtn.textContent = s.solving ? "Stop" : "Start Solve";
  const provider = els.provider.value || "local";
  els.solveBtn.disabled = provider !== "local" && !s.solving;

  if (typeof s.four_prob === "number") {
    const pct = Math.round(s.four_prob * 100);
    els.fourProb.value = String(pct);
    els.fourProbVal.textContent = `${pct}%`;
  }
}

async function api(path, method = "GET", body = undefined) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const resp = await fetch(path, opts);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(data.error || `HTTP ${resp.status}`);
    err.payload = data;
    err.status = resp.status;
    throw err;
  }
  return data;
}

async function refresh() {
  const s = await api("/api/state");
  applyState(s);
}

async function doMove(direction) {
  if (state.solving || state.status !== "playing") return;
  try {
    const s = await api("/api/move", "POST", { direction });
    applyState(s);
  } catch (err) {
    if (err.status !== 409) {
      console.warn("move failed:", err);
    }
  }
}

async function doNewGame() {
  const pct = Number(els.fourProb.value) / 100;
  const s = await api("/api/new-game", "POST", { four_prob: pct });
  clearHint();
  clearSolveLog();
  applyState(s);
}

function clearHint() {
  els.hintOut.textContent = "No hint yet.";
  els.hintScores.hidden = true;
  els.hintScores.querySelector("tbody").innerHTML = "";
}

function clearSolveLog() {
  els.solveLog.innerHTML = "";
}

async function doHint() {
  const provider = els.provider.value || "local";
  els.hintBtn.disabled = true;
  els.hintOut.textContent = `Thinking (${provider})...`;
  try {
    const data = await api("/api/hint", "POST", { provider });
    const dir = data.direction;
    els.hintOut.innerHTML =
      `Suggested: <strong>${dirLabel(dir)}</strong> ` +
      `<span class="small">via ${data.provider}, ${data.elapsed_ms} ms</span>`;

    const tbody = els.hintScores.querySelector("tbody");
    tbody.innerHTML = "";
    if (data.scores) {
      const entries = DIRECTIONS.map((d) => [d, data.scores[d]]);
      entries.sort((a, b) => (b[1] ?? -Infinity) - (a[1] ?? -Infinity));
      for (const [d, score] of entries) {
        const tr = document.createElement("tr");
        if (d === dir) tr.className = "best";
        const td1 = document.createElement("td");
        td1.textContent = dirLabel(d);
        const td2 = document.createElement("td");
        td2.textContent = score === null || score === -Infinity || score === undefined ? "–" : Number(score).toFixed(2);
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
      }
      els.hintScores.hidden = false;
    } else {
      els.hintScores.hidden = true;
    }
  } catch (err) {
    els.hintOut.textContent = `Error: ${err.payload?.error || err.message}`;
    els.hintScores.hidden = true;
  } finally {
    els.hintBtn.disabled = false;
  }
}

let solvePollTimer = null;

async function pollSolve() {
  try {
    const data = await api("/api/solve/status");
    applyState(data);
    renderSolveLog(data.log || []);
    if (!data.running) {
      clearInterval(solvePollTimer);
      solvePollTimer = null;
    }
  } catch (err) {
    console.warn("solve poll failed:", err);
  }
}

function renderSolveLog(entries) {
  els.solveLog.innerHTML = "";
  for (const e of entries.slice(-20)) {
    const li = document.createElement("li");
    li.textContent = `#${e.move_index} ${dirLabel(e.direction)}  score=${e.score}  (${e.status})`;
    els.solveLog.appendChild(li);
  }
}

async function doSolveToggle() {
  if (state.solving) {
    await api("/api/solve/stop", "POST");
    state.solving = false;
    if (solvePollTimer) {
      clearInterval(solvePollTimer);
      solvePollTimer = null;
    }
    await refresh();
    return;
  }
  try {
    await api("/api/solve/start", "POST", { provider: "local" });
    state.solving = true;
    await refresh();
    if (!solvePollTimer) {
      solvePollTimer = setInterval(pollSolve, 300);
    }
  } catch (err) {
    alert(`Could not start solve: ${err.payload?.error || err.message}`);
  }
}

function wireEvents() {
  window.addEventListener("keydown", (e) => {
    const dir = ARROW_TO_DIR[e.key];
    if (!dir) return;
    e.preventDefault();
    doMove(dir);
  });

  for (const btn of document.querySelectorAll(".dpad")) {
    btn.addEventListener("click", () => doMove(btn.dataset.dir));
  }

  els.newGame.addEventListener("click", doNewGame);
  els.overlayNew.addEventListener("click", doNewGame);
  els.hintBtn.addEventListener("click", doHint);
  els.solveBtn.addEventListener("click", doSolveToggle);

  els.provider.addEventListener("change", () => {
    const provider = els.provider.value || "local";
    els.solveBtn.disabled = provider !== "local" && !state.solving;
  });

  els.fourProb.addEventListener("input", () => {
    els.fourProbVal.textContent = `${els.fourProb.value}%`;
  });
}

wireEvents();
refresh();
