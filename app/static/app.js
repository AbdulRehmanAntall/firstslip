"use strict";

const PROBLEMS = [
  "4\\left(x+3\\right)=20", "5x-7=2x+8", "\\frac{x}{3}+2=5", "-3x=2\\left(x-6\\right)",
  "7-2x=3x+12", "3\\left(2x-1\\right)=4x+5", "\\frac{2x+1}{3}=x-1", "6x+4=2\\left(x-6\\right)",
  "9-\\left(x+4\\right)=2x", "\\frac{x}{2}-\\frac{x}{5}=3", "2\\left(x-4\\right)-3=x+1", "8x=3\\left(x+10\\right)",
];
const EXAMPLES = [
  { problem: "4\\left(x+3\\right)=20", steps: ["4x+3=20", "4x=17", "x=\\frac{17}{4}"] },
  { problem: "5x-7=2x+8", steps: ["3x-7=8", "3x=1", "x=\\frac{1}{3}"] },
  { problem: "-3x=2\\left(x-6\\right)", steps: ["-3x=2x-12", "-3x=-10", "x=\\frac{10}{3}"] },
  { problem: "\\frac{x}{3}+2=5", steps: ["\\frac{x}{3}=3", "x=1"] },
];
const ICON = {
  check: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1.2 14.2-4-4 1.4-1.4 2.6 2.6 5.6-5.6 1.4 1.4-7 7z"/></svg>',
  cross: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm3.5 12.1-1.4 1.4L12 13.4l-2.1 2.1-1.4-1.4 2.1-2.1-2.1-2.1 1.4-1.4 2.1 2.1 2.1-2.1 1.4 1.4-2.1 2.1 2.1 2.1z"/></svg>',
  question: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 16h-2v-2h2v2zm1.6-6.3-.9.9c-.6.6-.7 1-.7 1.9h-2v-.5c0-1 .4-1.8 1.1-2.5l1.2-1.2a1.7 1.7 0 0 0-1.2-2.9 1.8 1.8 0 0 0-1.8 1.8H8.4a3.6 3.6 0 0 1 7.2 0c0 .9-.4 1.8-1 2.5z"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3zm-1.2 14.2-3.5-3.5 1.4-1.4 2.1 2.1 4.9-4.9 1.4 1.4-6.3 6.3z"/></svg>',
  bubble: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3C6.5 3 2 6.8 2 11.5c0 2.4 1.2 4.6 3.1 6.1L4.5 21l3.9-1.9c1.1.3 2.3.4 3.6.4 5.5 0 10-3.8 10-8.5S17.5 3 12 3zm1 12h-2v-2h2v2zm0-4h-2V7h2v4z"/></svg>',
  remove: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};
const MARK = { same: ICON.check, changed: ICON.cross, unreadable: ICON.question, incomparable: ICON.question, empty: "" };

const $ = (s) => document.querySelector(s);
const stepsEl = $("#steps");
const fb = $("#feedback");
let exampleIdx = 0;
let problemIdx = Math.floor(Math.random() * PROBLEMS.length);

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renumber() {
  [...stepsEl.children].forEach((row, i) => {
    row.querySelector(".num").textContent = i + 1;
    row.querySelector("math-field").setAttribute("aria-label", `Step ${i + 1}`);
  });
}

function clearMarks() {
  for (const row of stepsEl.children) {
    row.className = "step";
    row.querySelector(".mark").innerHTML = "";
    const n = row.querySelector(".note");
    if (n) n.remove();
  }
}

function addStep(value = "", focus = true, after = null) {
  const row = document.createElement("div");
  row.className = "step";
  row.innerHTML = `<span class="num"></span><math-field></math-field>
    <span class="mark" aria-hidden="true"></span>
    <button class="remove" type="button" title="Remove step" aria-label="Remove step">${ICON.remove}</button>`;
  const mf = row.querySelector("math-field");
  mf.value = value;
  mf.addEventListener("keydown", (e) => {
    if (e.key === "Backspace" && !mf.value && stepsEl.children.length > 1) {
      e.preventDefault();
      const prev = row.previousElementSibling || row.nextElementSibling;
      row.remove(); renumber(); clearMarks();
      prev?.querySelector("math-field").focus();
    }
  });
  // MathLive handles Enter itself (physical and on-screen keyboard) and reports it as an
  // input event with inputType "insertLineBreak", not as a keydown the page can see.
  mf.addEventListener("input", (e) => {
    if (e.inputType === "insertLineBreak") addStep("", true, row);
    else clearMarks();
  });
  row.querySelector("button").addEventListener("click", () => {
    if (stepsEl.children.length > 1) { row.remove(); renumber(); clearMarks(); }
    else mf.value = "";
  });
  if (after) after.after(row); else stepsEl.appendChild(row);
  renumber();
  if (focus) setTimeout(() => mf.focus(), 0);
  return row;
}

function setSolution(problem, steps) {
  $("#problem").value = problem;
  stepsEl.innerHTML = "";
  (steps.length ? steps : [""]).forEach((s) => addStep(s, false));
  fb.innerHTML = "";
}

function stepValues() {
  return [...stepsEl.querySelectorAll("math-field")].map((m) => m.getValue("latex-unstyled") || m.value);
}

function render(data) {
  const rows = [...stepsEl.children];
  for (const s of data.steps) {
    const row = rows[s.index - 1];
    if (!row) continue;
    row.className = `step ${s.status}`;
    row.querySelector(".mark").innerHTML = MARK[s.status] || "";
    row.querySelector(".mark").setAttribute("aria-label", s.message);
    row.querySelector(".note")?.remove(); // render runs again once the model's guess arrives
    if (s.status !== "same" && s.status !== "empty") {
      const note = document.createElement("div");
      note.className = "note";
      note.textContent = s.message;
      row.appendChild(note);
    }
  }
  const err = data.verified.some((v) => v.kind === "error");
  let html = `<div class="panel verified${err ? " has-error" : ""}">
    <h2>${ICON.shield} What the checker found <span class="tag ok">Verified</span></h2>`;
  for (const v of data.verified) {
    html += `<p>${esc(v.text)}</p>`;
    if (v.before && v.after) {
      html += `<p class="small">Before: <math-field read-only class="ro">${esc(v.before.latex)}</math-field> &nbsp;→&nbsp;
        after step ${v.step}: <math-field read-only class="ro">${esc(v.after.latex)}</math-field></p>`;
    }
  }
  if (!data.verified.length) html += `<p>Add some steps, then check again.</p>`;
  html += `</div>`;

  if (data.guess) {
    const g = data.guess;
    html += `<div class="panel guess">
      <h2>${ICON.bubble} The model's guess <span class="tag maybe">Not verified</span></h2>
      <p>${esc(g.feedback)}</p>`;
    if (!g.agrees) {
      html += `<p class="warn">Careful: this sentence is about step ${esc(g.step ?? "?")}, but the checker found the
        first wrong step is step ${data.first_error}. Trust the checker for <i>where</i>; the model may be wrong about <i>what</i>.</p>`;
    }
    html += `<p class="small">Written by ${esc(g.model)} (prompt ${esc(g.prompt)}). In our tests this model named the real
      mistake about half the time, so check it against your own working.</p></div>`;
  } else if (data.guess_note) {
    html += `<div class="panel guess"><h2>${ICON.bubble} The model's guess <span class="tag maybe">Not verified</span></h2>
      <p class="small">${esc(data.guess_note)}</p></div>`;
  }
  fb.innerHTML = html;
  fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// --- the checker, in the browser ------------------------------------------------
// Pyodide runs the project's own Python (core/checker.py, app/checking.py) unchanged,
// with the same SymPy version as the study.
const PY_FILES = ["core/__init__.py", "core/checker.py", "app/__init__.py", "app/checking.py", "app/mathnorm.py"];
const PY_PACKAGES = ["sympy==1.14.0", "mpmath==1.3.0", "lark==1.3.1"];
let checkSolution = null;

async function loadChecker() {
  const py = await loadPyodide();
  await py.loadPackage("micropip");
  await py.pyimport("micropip").install(PY_PACKAGES);
  for (const f of PY_FILES) {
    const r = await fetch(`py/${f}`);
    if (!r.ok) throw new Error(`missing ${f}`);
    py.FS.mkdirTree(`/home/pyodide/${f.split("/")[0]}`);
    py.FS.writeFile(`/home/pyodide/${f}`, await r.text());
  }
  await py.runPythonAsync(`
import json, sys
sys.path.insert(0, "/home/pyodide")
from app.checking import check_solution, report_dict
def run(problem, steps_json):
    return json.dumps(report_dict(check_solution(problem, json.loads(steps_json))))
`);
  const run = py.globals.get("run");
  checkSolution = (problem, steps) => JSON.parse(run(problem, JSON.stringify(steps)));
  checkSolution("x=1", ["x=1"]); // warm up SymPy so the first real check is quick
}

// --- the model's guess, only where a server provides one ------------------------
async function explain(problem, steps) {
  try {
    const r = await fetch("api/explain", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ problem, steps }),
    });
    if (!r.ok && r.status < 500 && r.status !== 429) { // no server here (static hosting)
      return { guess: null, guess_note: "This version of the app has no model attached, so there is no explanation. Everything above is verified by the checker." };
    }
    if (!r.ok) return { guess: null, guess_note: "The model is unavailable right now. The checker's result above still stands." };
    return await r.json();
  } catch (e) {
    return { guess: null, guess_note: "Could not reach the model. The checker's result above still stands." };
  }
}

async function check() {
  const btn = $("#check");
  clearMarks();
  btn.disabled = true; btn.textContent = "Checking…";
  await new Promise((r) => setTimeout(r, 0)); // let the button repaint before SymPy runs
  const problem = $("#problem").value, steps = stepValues();
  try {
    const data = checkSolution(problem, steps);
    data.guess = null; data.guess_note = null;
    render(data);
    if (data.first_error) {
      Object.assign(data, await explain(problem, steps));
      render(data);
    }
  } catch (e) {
    fb.innerHTML = `<div class="panel verified has-error"><p class="err">The checker hit an error on this input. Try rewriting the line.</p></div>`;
  } finally {
    btn.disabled = false; btn.textContent = "Check Steps";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  setSolution(PROBLEMS[problemIdx], []);
  $("#add").addEventListener("click", () => addStep());
  $("#check").addEventListener("click", check);
  $("#clear").addEventListener("click", () => setSolution($("#problem").value, []));
  $("#new-problem").addEventListener("click", () => {
    problemIdx = (problemIdx + 1) % PROBLEMS.length;
    setSolution(PROBLEMS[problemIdx], []);
    stepsEl.querySelector("math-field").focus();
  });
  $("#example").addEventListener("click", () => {
    const ex = EXAMPLES[exampleIdx++ % EXAMPLES.length];
    setSolution(ex.problem, ex.steps);
  });
  $("#problem").addEventListener("input", (e) => {
    if (e.inputType === "insertLineBreak") stepsEl.querySelector("math-field").focus();
    else clearMarks();
  });
  loadChecker().then(() => {
    $("#check").disabled = false; $("#check").textContent = "Check Steps";
    $("#status").remove();
  }).catch(() => {
    $("#check").textContent = "Checker Unavailable";
    $("#status").textContent = "The checker could not load. Check your connection and reload the page.";
    $("#status").classList.add("err");
  });
});
