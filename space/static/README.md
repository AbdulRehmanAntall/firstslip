---
title: FirstSlip
emoji: ✏️
colorFrom: blue
colorTo: green
sdk: static
app_file: index.html
pinned: false
short_description: Step-by-step algebra checker with verified feedback
---

# FirstSlip

Write the solution to a linear equation one step per line. A SymPy checker marks every step and finds the first
step that changes the answer, and says so as a **verified** claim.

- The checker runs in your browser (Pyodide, SymPy 1.14.0): the page loads `py/core/checker.py` and
  `py/app/checking.py`, the same files the research used. Nothing you type leaves your device or is stored.
- This static version has no model attached, so it gives no model explanation; the server version
  (`app/main.py` in the source repository) adds one from Qwen3.5-27B, labelled *not verified*.
- `results.html`: the research findings (experiments E1–E3).
