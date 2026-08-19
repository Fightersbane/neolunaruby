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
  }
};

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
    $("chip-gpu").innerHTML = `GPU <b>${res.gpu.util}%</b>`;
    $("chip-vram").innerHTML = `VRAM <b>${(res.gpu.vram_used_mb / 1024).toFixed(1)}G</b>`;
  }
  showLatency(res.last_timing);
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

  const dev = await pywebview.api.list_devices();
  const options = [new Option("System default", "", false, s.device === null)];
  for (const d of dev.devices) {
    const label = (d.index === dev.cable ? "🎤 " : "") + d.name + (d.is_default ? " (default)" : "");
    options.push(new Option(label, d.index, false, d.index === s.device));
  }
  $("device").replaceChildren(...options);

  renderHistory((await pywebview.api.get_history()).items);
  refreshTelemetry();
  setInterval(refreshTelemetry, 2000);
}

window.addEventListener("pywebviewready", init);

// ---------- wiring ----------
$("say-btn").onclick = say;
$("say-input").addEventListener("keydown", (e) => { if (e.key === "Enter") say(); });

$("preset").onchange = (e) => setSetting("preset", e.target.value).then((ok) => { if (ok) init(); });
$("speed").oninput = (e) => { $("speed-val").textContent = `${Number(e.target.value).toFixed(2)}×`; };
$("speed").onchange = (e) => setSetting("speed", Number(e.target.value));
$("pitch").oninput = (e) => { const v = Number(e.target.value); $("pitch-val").textContent = (v >= 0 ? "+" : "") + v; };
$("pitch").onchange = (e) => setSetting("n_semitones", Number(e.target.value));
$("device").onchange = (e) => setSetting("device", e.target.value === "" ? null : Number(e.target.value));
$("test-tone").onclick = () => pywebview.api.test_tone();
$("hotkey-apply").onclick = async () => {
  if (await setSetting("hotkey", $("hotkey").value.trim())) toast("Hotkey updated.");
};

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + btn.dataset.tab));
  };
});
