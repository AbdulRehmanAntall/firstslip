---
title: FirstSlip
emoji: ✏️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Step-by-step algebra checker with verified feedback
---

# FirstSlip

Write the solution to a linear equation one step per line. A SymPy checker marks every step and finds the first
step that changes the answer; Qwen3.5-27B (via Hugging Face Inference Providers) suggests what went wrong. The
app labels the checker's findings as **verified** and the model's sentence as **not verified**.

- `/` the checker, `/results` the research findings (experiments E1–E3).
- Nothing typed is stored or logged. Requests are capped per session and per day.
- Secret `HF_TOKEN`: a token allowed to call Inference Providers. Without it the checker still works and the
  model's explanation is shown as unavailable.

Source: the FirstSlip research repository (`app/`, `core/checker.py`, `core/prompts.py`).
