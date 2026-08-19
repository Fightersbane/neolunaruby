"use strict";

const $ = (id) => document.getElementById(id);
let speakingTimer = null;

// ---------- events pushed from Python ----------
window.onEvent = (evt) => {
  if (evt.type === "state") {
    setLed(evt.state);
    if (evt.error) toast(evt.error);
  } else if (evt.type === "speaking") {
    showLatency(evt.entry.latency_ms);
    pulseVoiceline();
  } else if (evt.type === "history") {
    renderHistory(evt.items);
  } else if (evt.type === "cable") {
    cableStatus(evt);
  } else if (evt.type === "discord") {
    $("discord-status").textContent = evt.status;
  } else if (evt.type === "update") {
    if (evt.status === "updating") toast("Updating — this can take a minute…");
    else if (evt.status === "restarting") toast("Updated. Restarting…");
    else if (evt.status === "failed") toast(`Update failed: ${evt.error || "unknown error"}`);
  }
};

function setModeUI(mode) {
  document.querySelectorAll(".seg button").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
}

async function copyText(label, text) {
  try {
    await navigator.clipboard.writeText(text);
    toast(`${label} copied.`);
  } catch {
    prompt(`Copy the ${label}:`, text);
  }
}

function renderDiscord(d) {
  $("discord-status").textContent = d.status;
  const links = $("discord-links");
  links.replaceChildren();
  if (d.install_link) {
    const a = document.createElement("button");
    a.textContent = "Copy DM install link";
    a.title = "She opens this to add /say to her own account — then /say works inside any DM";
    a.onclick = () => copyText("install link", d.install_link);
    const b = document.createElement("button");
    b.textContent = "Copy server invite";
    b.onclick = () => copyText("server invite", d.invite_link);
    links.append(a, " · ", b);
  }
}

function cableStatus(evt) {
  const hint = $("cable-hint");
  if (evt.status === "downloading") {
    hint.textContent = "Downloading VB-Cable…";
  } else if (evt.status === "rescanning") {
    hint.textContent = "Installing — accept the Windows admin prompt if it appears…";
  } else if (evt.status === "done") {
    toast("Virtual mic installed.");
    init();
  } else if (evt.status === "restart_needed") {
    hint.textContent = "Installed — restart the app (or PC) to see the virtual mic.";
  } else if (evt.status === "failed") {
    hint.replaceChildren("Install failed — ");
    const b = document.createElement("button");
    b.textContent = "open the download page";
    b.onclick = () => pywebview.api.open_cable_page();
    hint.append(b);
    toast(evt.error || "VB-Cable install failed.");
  }
}

function setLed(state) {
  $("led").className = "led" + (state === "ready" ? " ready" : state === "error" ? " error" : "");
  $("led").title = state;
}

function pulseVoiceline() {
  document.body.classList.add("speaking");
  clearTimeout(speakingTimer);
  speakingTimer = setTimeout(() => document.body.classList.remove("speaking"), 2500);
}

function showLatency(lat) {
  if (!lat || lat.total_ms == null) return;
  $("chip-latency").innerHTML = `<b>${(lat.total_ms / 1000).toFixed(1)}s</b>`;
  $("chip-latency").title = `TTS ${lat.tts_ms} ms + voice ${lat.rvc_ms} ms`;
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 4000);
}

// ---------- say ----------
async function say() {
  const input = $("say-input");
  const text = input.value.trim();
  if (!text) return;
  const res = await pywebview.api.say(text);
  if (res.ok) input.value = "";
  else toast(res.error);
}

// ---------- settings ----------
async function setSetting(key, value) {
  const res = await pywebview.api.set_setting(key, value);
  if (!res.ok) toast(res.error);
  return res.ok;
}

function renderHistory(items) {
  const list = $("history-list");
  list.replaceChildren();
  $("history-empty").style.display = items.length ? "none" : "block";
  for (const e of items) {
    const li = document.createElement("li");
    const text = document.createElement("div");
    text.className = "htext";
    text.textContent = e.text;
    text.title = e.text;
    const lat = document.createElement("div");
    lat.className = "hlat";
    lat.textContent = e.latency_ms.total_ms != null ? `${(e.latency_ms.total_ms / 1000).toFixed(1)}s` : "";
    const btn = document.createElement("button");
    btn.className = "quiet replay";
    btn.textContent = "▶";
    btn.title = "Replay";
    btn.onclick = async () => {
      const res = await pywebview.api.replay(e.id);
      if (res.ok) pulseVoiceline();
      else toast(res.error);
    };
    li.append(text, lat, btn);
    list.append(li);
  }
}

async function refreshTelemetry() {
  const res = await pywebview.api.get_telemetry();
  if (!res.ok) return;
  if (res.gpu) {
    const g = res.gpu;
    $("chip-gpu").innerHTML = `GPU <b>${g.util}%</b>`;
    $("chip-gpu").title = g.util_scope === "app" ? "this app's GPU use" : "whole-system GPU use (per-app not supported by driver)";
    if (g.app_vram_mb != null) {
      $("chip-vram").innerHTML = `VRAM <b>${(g.app_vram_mb / 1024).toFixed(1)}G</b>`;
      $("chip-vram").title = `this app: ${(g.app_vram_mb / 1024).toFixed(1)} GB · system: ${(g.vram_used_mb / 1024).toFixed(1)} / ${(g.vram_total_mb / 1024).toFixed(1)} GB`;
    } else {
      $("chip-vram").innerHTML = `VRAM <b>${(g.vram_used_mb / 1024).toFixed(1)}G</b>`;
      $("chip-vram").title = "whole-system VRAM use";
    }
  }
  showLatency(res.last_timing);
}

function renderCableHint(dev, currentDevice) {
  const hint = $("cable-hint");
  hint.replaceChildren();
  if (dev.cable === null) {
    hint.append("No virtual mic found — ");
    const btn = document.createElement("button");
    btn.textContent = "Install VB-Cable";
    btn.onclick = () => {
      hint.textContent = "Starting download…";
      pywebview.api.install_cable();
    };
    hint.append(btn, " (free driver, one Windows admin prompt)");
  } else if (currentDevice !== dev.cable) {
    const btn = document.createElement("button");
    btn.textContent = "🎤 Use virtual mic";
    btn.onclick = async () => {
      if (await setSetting("device", dev.cable)) {
        $("device").value = String(dev.cable);
        renderCableHint(dev, dev.cable);
      }
    };
    hint.append(btn, " — then pick “CABLE Output” as your mic in Discord.");
  } else {
    hint.append("Speaking into the virtual mic — set Discord's input to “CABLE Output”.");
  }
}

// ---------- init ----------
async function init() {
  const state = await pywebview.api.get_state();
  setLed(state.state);

  const s = state.settings;
  $("preset").replaceChildren(...state.presets.map((p) => new Option(p, p, false, p === s.preset)));
  $("speed").value = s.speed;
  $("speed-val").textContent = `${Number(s.speed).toFixed(2)}×`;
  $("pitch").value = s.n_semitones;
  $("pitch-val").textContent = (s.n_semitones >= 0 ? "+" : "") + s.n_semitones;
  $("hotkey").value = s.hotkey;
  setModeUI(s.mode);
  $("allowed-ids").value = (s.allowed_dm_users || []).join(", ");
  renderDiscord(state.discord || { status: "no token configured" });
  $("chip-version").textContent = `v${state.version || "dev"}`;

  const dev = await pywebview.api.list_devices();
  // settings persist device NAMES; resolve to the current index for the UI
  const devIdx = dev.devices.find((d) => d.name === s.device)?.index ?? null;
  const monIdx = dev.devices.find((d) => d.name === s.monitor_device)?.index ?? null;
  const options = [new Option("System default", "", false, devIdx === null)];
  const monOptions = [new Option("Off", "", false, monIdx === null)];
  for (const d of dev.devices) {
    const label = (d.index === dev.cable ? "🎤 " : "") + d.name + (d.is_default ? " (default)" : "");
    options.push(new Option(label, d.index, false, d.index === devIdx));
    monOptions.push(new Option(label, d.index, false, d.index === monIdx));
  }
  $("device").replaceChildren(...options);
  $("monitor").replaceChildren(...monOptions);
  renderCableHint(dev, devIdx);

  renderHistory((await pywebview.api.get_history()).items);
  refreshTelemetry();
  setInterval(refreshTelemetry, 2000);
}

window.addEventListener("pywebviewready", init);

// ---------- wiring ----------
$("chip-version").onclick = async () => {
  toast("Checking for updates…");
  const res = await pywebview.api.check_update();
  if (!res.ok) return toast(res.error);
  if (res.behind === 0) return toast(`Up to date (v${res.version}).`);
  if (confirm(`Update available (${res.behind} new change${res.behind > 1 ? "s" : ""}). Update and restart now?`)) {
    pywebview.api.apply_update();
  }
};

$("say-btn").onclick = say;
$("say-input").addEventListener("keydown", (e) => { if (e.key === "Enter") say(); });

$("preset").onchange = (e) => setSetting("preset", e.target.value).then((ok) => { if (ok) init(); });
$("speed").oninput = (e) => { $("speed-val").textContent = `${Number(e.target.value).toFixed(2)}×`; };
$("speed").onchange = (e) => setSetting("speed", Number(e.target.value));
$("pitch").oninput = (e) => { const v = Number(e.target.value); $("pitch-val").textContent = (v >= 0 ? "+" : "") + v; };
$("pitch").onchange = (e) => setSetting("n_semitones", Number(e.target.value));
$("device").onchange = (e) => setSetting("device", e.target.value === "" ? null : Number(e.target.value));
$("monitor").onchange = (e) => setSetting("monitor_device", e.target.value === "" ? null : Number(e.target.value));
$("test-tone").onclick = () => pywebview.api.test_tone();

document.querySelectorAll(".seg button").forEach((btn) => {
  btn.onclick = async () => {
    if (await setSetting("mode", btn.dataset.mode)) setModeUI(btn.dataset.mode);
  };
});

$("allowed-save").onclick = async () => {
  if (await setSetting("allowed_dm_users", $("allowed-ids").value)) {
    const state = await pywebview.api.get_state();
    $("allowed-ids").value = (state.settings.allowed_dm_users || []).join(", ");
    toast("Allowlist saved.");
  }
};

// ---------- hotkey recorder ----------
const KEYMAP = {
  " ": "space", "ArrowUp": "up", "ArrowDown": "down", "ArrowLeft": "left",
  "ArrowRight": "right", "Enter": "enter", "Tab": "tab", "Backspace": "backspace",
  "Delete": "delete", "Home": "home", "End": "end", "PageUp": "page up",
  "PageDown": "page down", "Insert": "insert",
};
let recordingHotkey = false;

$("hotkey-record").onclick = () => {
  recordingHotkey = true;
  $("hotkey").value = "press keys…";
  $("hotkey").classList.add("recording");
};

async function stopHotkeyRecording(combo) {
  recordingHotkey = false;
  $("hotkey").classList.remove("recording");
  if (combo && (await setSetting("hotkey", combo))) {
    $("hotkey").value = combo;
    toast(`Hotkey set to ${combo}.`);
  } else {
    const state = await pywebview.api.get_state();
    $("hotkey").value = state.settings.hotkey;
  }
}

window.addEventListener("keydown", (e) => {
  if (!recordingHotkey) return;
  e.preventDefault();
  e.stopPropagation();
  if (e.key === "Escape") {
    stopHotkeyRecording(null);
    return;
  }
  const mods = [];
  if (e.ctrlKey) mods.push("ctrl");
  if (e.altKey) mods.push("alt");
  if (e.shiftKey) mods.push("shift");
  if (e.metaKey) mods.push("windows");
  if (["Control", "Shift", "Alt", "Meta"].includes(e.key)) {
    $("hotkey").value = mods.join("+") + "+…";
    return;
  }
  const key = KEYMAP[e.key] || e.key.toLowerCase();
  stopHotkeyRecording([...mods, key].join("+"));
}, true);

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + btn.dataset.tab));
  };
});
