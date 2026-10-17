# FirstSlip — Phased Plan

Complete, step-by-step plan derived from the project proposal. Every phase lists **what to do**, **the specs that phase depends on**, **what to read**, and **the gate that must pass before the next phase starts**.

- **Timeline:** 16 Oct – 24 Nov 2026, ~80 hours total (~15 h/week)
- **Cut line:** 9 Nov 2026. Phases 0–3 produce a complete, usable project on their own (benchmark + prompted results + live app). Phases 4–6 add training and transfer. If the application deadline falls earlier, stop at the cut line and list the project as ongoing.
- **Rule:** do not start a phase until the previous gate is passed. At the end of every phase, fill in its section of [PROGRESS.md](PROGRESS.md).

| Phase | Name | Dates (2026) | Est. hours |
|---|---|---|---|
| 0 | Setup and core reading | 16 – 18 Oct | ~6 (+ ~8 reading) |
| 1 | Generator and checker | 19 – 27 Oct | ~16 |
| 2 | Prompted experiments E1–E3 | 28 Oct – 3 Nov | ~15 |
| 3 | Student app | 4 – 9 Nov | ~12 |
| ✂ | **Cut line: resume-ready** | **9 Nov** | |
| 4 | Training E4 (GRPO go/no-go on 12 Nov) | 10 – 17 Nov | ~16 |
| 5 | Transfer and faithfulness E5, E6 | 18 – 21 Nov | ~8 |
| 6 | Release and write-up | 22 – 24 Nov | ~9 |

---

## Global specifications (apply to all phases)

### Logging discipline
- [ ] Every run writes **one JSONL file per run** containing: git commit hash, random seed, config hash, model name + pinned version, and every prompt/response.
- [ ] Every API response is **cached** (never pay twice for the same call).
- [ ] An API **spending cap** is set before any paid call.

### Fixed model output format
- [ ] Every model answers in one fixed format: **the first wrong step number (or `0` for no error), then one sentence of feedback.**
- [ ] The same format is used for prompted models (E1–E3), training (E4) and evaluation (E5–E6). It keeps parsing exact and GRPO completions short.

### Metrics
- [ ] **First-error accuracy:** exact match with the true first wrong step, on incorrect solutions.
- [ ] **Clean accuracy:** saying "no error" (0) on correct solutions.
- [ ] **Error F1:** harmonic mean of first-error accuracy and clean accuracy (following ProcessBench), so a model cannot score well by always flagging an error.
- [ ] **Within-one accuracy:** prediction within ±1 step of the truth (for comparison with Srivatsa et al., 2025).
- [ ] **Misconception accuracy** (synthetic data only): naming the injected misconception, scored by a fixed mapping from free text to labels; mapping audited by hand on 100 items.
- [ ] **Faithfulness:** share of responses whose feedback sentence refers to the step they flagged. A rule-based extractor finds the step mentioned; 100 items checked by hand and the extractor's agreement with the hand labels reported.
- [ ] **Deference rate (E3):** share of responses that adopt the supplied wrong location.

### Statistics
- [ ] Model comparisons on the same items: **paired bootstrap with 10,000 resamples** and **McNemar's test**, with **Holm correction** within each experiment.
- [ ] Trained models: report **mean and standard deviation over three seeds**; a difference counts as stable only when it exceeds the between-seed standard deviation.
- [ ] Hypotheses are fixed in `PREREGISTRATION.md` before any run; a null result is reported as a null result.

### Ethics / scope
- [ ] No learner data is collected. The app keeps **no logs by default**, so no ethics review is needed.
- [ ] Always state plainly that no learner study was run and that VtG solutions are simulated (LLM-written, MathDial). A learner study is future work for the MSc.

---

## Phase 0 — Setup and core reading (16 – 18 Oct, ~6 h + reading)

### Tasks
- [x] Create the GitHub repository.
- [x] Create a Python environment with **pinned versions** (e.g. `requirements.txt` / lock file).
- [x] ~~Create a Kaggle notebook with GPU enabled (2 × T4)~~. *Dropped: all GPU work runs on Colab Pro (A100), which Phase 2 already used. `notebooks/phase0_kaggle_env_check.ipynb` is kept but not run.*
- [x] Load **VtG** from Hugging Face ([`eth-nlped/stepverify`](https://huggingface.co/datasets/eth-nlped/stepverify), 1,002 rows, CC BY 4.0: first error index, error category, teacher description).
- [x] Inspect **30 VtG rows by hand** and note observations.
- [x] Split VtG: **VtG dev = random 200 rows** (prompt format only, never used for training), **VtG test = remaining 802 rows**. Fix and record the seed.
- [x] Compute the **random baseline** on VtG.
- [x] Compute the **position-only baseline** on VtG (guess the most common error step for a given solution length).
- [x] Read items **A1–A5** of the reading list (~8 h).
- [x] Write `PREREGISTRATION.md` containing:
  - [x] RQ1–RQ4 and all hypotheses (H1, H1b, H2, H2b, H3 + anti-hypothesis, H4, H4b — see below)
  - [x] The **held-out misconception choice**: one misconception from each family —
    - one **distribution** error (e.g. distributing to the first term only)
    - one **sign** error
    - one **division** error (e.g. dividing one side only)
    - one **term-combining** error
  - [x] The planned splits, metrics, statistics and output format
- [x] Commit `PREREGISTRATION.md`.
- [x] Note to resolve while writing the pre-registration: the proposal lists 15 "seen" misconceptions and 4 held-out (one per family) — confirm the exact total from Sonkar et al. (2024) Table 1 and record the final list.

### Hypotheses to pre-register
- **RQ1 – Measurement.** How often do current LLMs locate the first wrong step, name the misconception, and write feedback about the same step they flagged?
  - **H1:** Localization accuracy on synthetic algebra will be well below the models' accuracy at solving the same equations, as reported for word problems.
  - **H1b:** In a measurable share of responses, the written feedback discusses a step other than the one the model flagged.
- **RQ2 – Grounding and trust.** Does giving the model the checker's error location improve its feedback, and when that location is deliberately wrong, how often does the model repeat it?
  - **H2:** Correct locations raise feedback accuracy, consistent with Daheim et al. (2024).
  - **H2b:** Models will adopt a wrong location in most cases rather than contradict it.
- **RQ3 – Training from the checker.** Does RL with the checker as reward improve error localization in a small open model, compared with SFT on the same labels?
  - **H3:** Both improve over the base model on misconception types seen in training. Only a model that learned to check steps, rather than recognise error patterns, will hold its gain on held-out misconception types.
  - **Anti-hypothesis:** the gain reduces to a position prior (guessing the most common error step for a given solution length). The position-only baseline tests this directly.
- **RQ4 – Transfer and side effects.** Does the gain carry over to VtG, where no checker applies? Does rewarding only the step number change how faithful the explanations are?
  - **H4:** Transfer to VtG will be positive but much smaller than the in-domain gain, because VtG errors are mostly misreadings of word problems rather than algebraic slips.
  - **H4b:** No prediction about faithfulness; the direction of the change is the finding.

### Reading (Phase 0)
- [x] **A1** — *Stepwise Verification and Remediation of Student Reasoning Errors with LLM Tutors* (Daheim et al., EMNLP 2024) — [link](https://aclanthology.org/2024.emnlp-main.478). Read all of it. Closest prior work and the source of VtG; the project must say clearly what it adds.
- [x] **A2** — *LLMs cannot spot math errors, even when allowed to peek into the solution* (Srivatsa, Maurya & Kochmar, 2025) — [link](https://arxiv.org/abs/2509.01395). Sections 1–4 and the prompt appendix. VtG baselines to compare against; reusable prompt templates.
- [x] **A3** — *LLMs cannot find reasoning errors, but can correct them given the error location* (Tyen et al., Findings of ACL 2024). Abstract, Sections 1 and 4. The finding the tool-augmented condition builds on.
- [x] **A4** — *LLM-based Cognitive Models of Students with Misconceptions* (Sonkar et al., 2024, MalAlgoPy) — [link](https://arxiv.org/abs/2410.12294). Section 3 and Table 1 closely — the blueprint for the generator.
- [x] **A5** — *Misconception Acquisition Dynamics in Large Language Models* (Liu et al., 2026, MalAlgoLib) — [link](https://arxiv.org/abs/2604.00818). Abstract and results: intermediate steps are what let a model learn where an error enters.
- [x] **B1** — *The Unreliability of Explanations in Few-shot Prompting for Textual Reasoning* (Ye & Durrett, NeurIPS 2022). Origin of the faithfulness measure.
- [x] **B2** — *SatLM: Satisfiability-Aided Language Models Using Declarative Prompting* (Ye, Chen, Dillig & Durrett, NeurIPS 2023). The LLM-plus-solver pattern the grounded condition follows.
- [x] **B3** — *To CoT or not to CoT?* (Sprague et al., ICLR 2025). Reread the section comparing CoT with symbolic solvers.

### Gate 0
- [x] **Both VtG baselines (random and position-only) computed** and
- [x] **`PREREGISTRATION.md` committed.**
- [x] Fill in Phase 0 in [PROGRESS.md](PROGRESS.md).

---

## Phase 1 — Generator and checker (19 – 27 Oct, ~16 h)

MalAlgoPy's code is not public (every candidate GitHub repo returns 404), so the generator is written **from scratch** from the misconception table in Sonkar et al. (2024). Expect ~2 days for this.

### Tasks — generator
- [x] Implement the **16 equation types** (from MalAlgoPy) as **reduction rules**, each producing one step. *(15 forms — T13 is absent from Sonkar et al. — plus intermediate states T12d and T12m; see PREREGISTRATION.md Amendment 1.)*
- [x] Implement the **misconceptions from Sonkar et al. (2024), Table 1** as **alternative (wrong) steps**.
- [x] Add the generator rules:
  - [x] **One error per item:** each incorrect solution contains exactly one injected misconception, and the checker must confirm the solution set changes at that step.
  - [x] **No accidental recovery:** no later step may return to the correct answer by chance; such items are **dropped and counted**.
  - [x] **Balanced positions:** the first-error position is balanced across step indices so a position-only guess cannot score well.
  - [x] **Deduplication:** equations are deduplicated by their **canonical SymPy form across all splits**.
  - [x] **Ranges:** coefficients are integers in **[-12, 12]**; answers are integers or simple fractions; solutions run **3 to 6 steps**.
- [x] Respect the held-out choice from `PREREGISTRATION.md` — held-out misconceptions must never appear in train/dev/test-seen.

### Tasks — checker
- [x] Parse each line of a solution:
  - plain text → `sympy.parsing.sympy_parser.parse_expr`
  - LaTeX (app input) → `parse_latex(..., backend="lark")` (lark avoids the ANTLR version pin)
- [x] Compare **solution sets between consecutive steps** using `solveset` for equations; for expressions use `simplify(a - b) == 0` **plus random numeric spot checks**.
- [x] Return the **first step where the solution set differs** (or 0 if none).

### Tasks — data
- [x] Generate all synthetic splits:

| Split | Source | Planned size | Use |
|---|---|---|---|
| Train | Generator, the 15 seen misconceptions | 6,000 incorrect + 2,000 clean | SFT and GRPO |
| Dev | Generator, same 15 misconceptions | 500 | Prompt tuning, early stopping, GRPO go/no-go |
| Test, seen types | Generator, same 15, new equations | 1,000 (25% clean) | In-domain results |
| Test, held-out types | Generator, the held-out misconceptions only | 1,000 (25% clean) | Did the model learn to check, or recognise patterns? |
| VtG dev | VtG, random 200 rows | 200 | Prompt format only; never for training |
| VtG test | VtG, remaining rows | 802 | Transfer test |

  (Sizes are targets, not measurements.)
- [x] Write a **dataset card** (sources, rules, splits, held-out choice, counts of dropped items, licence).

### Fallback
- If rebuilding the rules is too fiddly: start with the **8 most common misconceptions** and add the rest later; the held-out design still works.

### Gate 1
- [x] On **2,000 generated items**, the checker finds the injected step in **100% of incorrect items** and reports **no error on 100% of clean items**.
- [x] **50 items checked by hand.**
- [x] Fill in Phase 1 in [PROGRESS.md](PROGRESS.md).

---

## Phase 2 — Prompted experiments E1–E3 (28 Oct – 3 Nov, ~15 h)

### Models (three)
- **Qwen3.5-2B**, **Qwen3.5-4B** and **Qwen3.5-27B (FP8)**, served with **vLLM** (Apache 2.0) on a Colab Pro A100. Fallbacks: Qwen3-1.7B / Qwen3-4B / Qwen3.5-27B-GPTQ-Int4.
- *Both API models were dropped. The frontier model was replaced by Qwen3.5-27B for cost reasons (Amendment 3), and `gpt-6-luna` was removed (Amendment 4 in `PREREGISTRATION.md`).*

### Experiments

| Exp. | RQ | Conditions | Data |
|---|---|---|---|
| E1 Prompted localization | RQ1 | Random; position-only; 3 open models | Test seen, test held-out, VtG test |
| E2 Grounded feedback | RQ2 | No location given vs. checker location given; LLM writes the feedback | Synthetic tests |
| E3 Corrupted tool | RQ2 | Location given is the true step, one step off, or a random wrong step | Synthetic tests |

### Tasks
- [x] Write **one prompt template** and the **output parser** (fixed format: step number or 0, then one sentence). *(`core/prompts.py`; API runner `scripts/phase2_run.py`, Colab vLLM notebook `notebooks/phase2_colab_vllm.ipynb`.)*
- [x] **Freeze both** using the dev splits only (synthetic dev + VtG dev). *(Prompt p2-v1; judge j-v1, Amendment 5.)*
- [x] Run **E1** on all three models across **both synthetic tests and VtG test**, caching every response. Report VtG results on all 802 rows **and separately without the "None of the above" category** (8.7% of VtG, least consistent labels).
- [x] Run **E2** on the synthetic tests.
- [x] Run **E3** on the synthetic tests (true / one-off / random-wrong location); compute deference rate.
- [x] Build the **faithfulness extractor** (rule-based: finds the step the feedback sentence mentions). *(`core/faithfulness.py`; misconception mapping in `core/misconceptions.py`.)*
- [x] **Audit 100 items by hand** for faithfulness; report extractor–hand agreement. *(`results/phase2/audit.json`.)*
- [x] Audit misconception-name mapping on **100 items by hand**.
- [x] Produce **result tables with bootstrap intervals** (paired bootstrap, McNemar, Holm). *(`results/phase2/tables.md`.)*
- [x] Run the full grid **only on the final frozen prompt** (API cost control).

### Reading (Phases 2 and 4)
- [ ] **C1** — *ProcessBench: Identifying Process Errors in Mathematical Reasoning* (Zheng et al., 2024) — [link](https://arxiv.org/abs/2412.06559). Sections 1–3. Source of the error F1 metric.
- [ ] **C2** — *Let's Verify Step by Step* (Lightman et al., 2023). Sections 1–3. Process supervision and PRM800K.

### Gate 2
- [x] **All E1–E3 tables filled**, and
- [x] the faithfulness extractor **agrees with hand labels on ≥ 90%** of audited items. *(Passed by the LLM judge, which replaced the extractor under Amendment 5: 97% (93–100%) agreement. The rule-based extractor reached 21%.)*
- [x] Fill in Phase 2 in [PROGRESS.md](PROGRESS.md).

---

## Phase 3 — Student app (4 – 9 Nov, ~12 h)

### Tasks
- [x] **FastAPI endpoint:** problem + steps in → per-step check and feedback out. *(`app/main.py`, `POST /api/check`.)*
- [x] **Single page** with **MathLive** input (outputs LaTeX), **one line per step**, **green or red mark per step**.
- [x] **Feedback panel** that labels **checker-verified claims separately from the model's guesses**.
- [x] Unparseable input: show a clear **"could not read this line"** message rather than a guess.
- [x] **Deploy to Hugging Face Spaces** (free CPU) with a **per-session request cap**. *(Static Space, checker in the browser; see PROGRESS.md deviations. The caps apply to the server version.)*
- [x] App keeps **no logs by default**.
- [x] Add a **results page** with the E1–E3 findings.

### Reading (Phases 3 and 6)
- [ ] **D1** — *Generative AI without guardrails can harm learning* (Bastani et al., PNAS 2025). Evidence behind the corrupted-tool control.
- [ ] **D2** — *On Assessing the Faithfulness of LLM-generated Feedback on Student Assignments* (Jia et al., EDM 2024).
- [ ] **D3** — *Uncertainty Representation in Visualizations of Learning Analytics for Learners* (Demmans Epp & Bull, IEEE TLT 2015). Why the app labels verified vs. guessed claims.
- [ ] **D4** — *Representing Uncertainty in Open Learner Models: How Well Do People Interpret It?* (Demmans Epp et al., AIED 2026). The study a future learner experiment would extend.
- [ ] **D5** — *Algebra Mal-rules and Cognitive Accounts of Error* (Payne & Squibb, Cognitive Science 1990). Original source of the misconception taxonomy.
- [ ] **D6** — *MathDial* (Macina et al., Findings of EMNLP 2023). Section 3: how VtG student solutions were produced.

### Gate 3 — CUT LINE (9 Nov)
- [ ] **A friend can solve a problem, make a mistake and get feedback on a phone.**
- [ ] Deliverables 1–4 exist (generator + checker, synthetic benchmark + dataset card, prompted results, live app).
- [ ] Write the **short resume entry** (see Phase 6) — the project is presentable from here.
- [ ] Fill in Phase 3 in [PROGRESS.md](PROGRESS.md).

---

## Phase 4 — Training E4 (10 – 17 Nov, ~16 h)

### Setup
- Base model: **Qwen3.5-2B** (fallback Qwen3-1.7B).
- **TRL `GRPOTrainer`** with a custom reward function; **TRL `SFTTrainer`** for the baseline.
- **Unsloth + LoRA** to fit a 2B model and GRPO sampling in 16 GB.
- Compute: **Colab Pro** GPU (A100, as in Phase 2). Keep **each GRPO run under 3 hours**.

### GRPO reward (checker-scored)
| Completion | Reward |
|---|---|
| Correct step number | 1.0 |
| Correct "no error" (0) on a clean solution | 1.0 |
| Step number off by one | 0.2 |
| Anything else | 0 |
| **Format reward** (answer parses) | +0.1 |

Nothing in the reward looks at the feedback sentence — this is what makes E6 a clean test.

### Tasks
- [ ] Read **C3** — *DeepSeekMath* (Shao et al., 2024), GRPO section only.
- [ ] Read **C4** — [TRL GRPOTrainer docs](https://huggingface.co/docs/trl/main/grpo_trainer), custom reward function section, **before writing any training code**.
- [ ] **SFT baseline** on the train split (one run per seed).
- [ ] **GRPO** with the checker reward, starting from the **base model**.
- [ ] **Go/no-go on 12 Nov:** if mean reward has not risen **and** dev accuracy is not above the base model → switch to **rejection-sampling fine-tuning** (sample several answers, keep those the checker confirms, fine-tune on them).
- [ ] **Three seeds** for each trained condition (Base vs. SFT vs. GRPO/RFT).
- [ ] Evaluate on **both synthetic tests** (seen + held-out).
- [ ] **Plot the distribution of predicted steps** to check for position bias; compare against the position-only baseline (anti-hypothesis).

### Fallbacks
- GRPO has no signal (every sample in a group gets the same reward → zero update): start with easier items (two-step equations), raise samples per prompt, or switch to rejection-sampling fine-tuning.
- Qwen3.5-2B doesn't train well with Unsloth/TRL: use Qwen3-1.7B.
- Colab compute units run low: keep runs < 3 h.

### Gate 4
- [ ] **Three seeds per condition evaluated**, with **held-out results** and the **position check** reported.
- [ ] Fill in Phase 4 in [PROGRESS.md](PROGRESS.md).

---

## Phase 5 — Transfer and faithfulness E5, E6 (18 – 21 Nov, ~8 h)

| Exp. | RQ | Conditions | Data |
|---|---|---|---|
| E5 Transfer | RQ4 | Same checkpoints as E4 | VtG test |
| E6 Faithfulness after training | RQ4 | Same checkpoints, asked to explain the flagged step | Synthetic tests and VtG test |

### Tasks
- [ ] Evaluate **all checkpoints on VtG test**, **overall and by error category** (and with/without "None of the above").
- [ ] Run the **faithfulness measure on trained models** (E6).
- [ ] Write a **one-paragraph answer to each research question**, including the nulls.
- [ ] Mark **every hypothesis** as **supported / not supported / inconclusive**, with its evidence.
- [ ] Optional, only if time remains: evaluate on the **PRM800K test split** (MIT) as a harder test.

### Gate 5
- [ ] **Every hypothesis marked supported, not supported or inconclusive, with its evidence.**
- [ ] Fill in the resume-entry numbers (N, K, X, Y, A, B, C, D).
- [ ] Fill in Phase 5 in [PROGRESS.md](PROGRESS.md).

---

## Phase 6 — Release and write-up (22 – 24 Nov, ~9 h)

### Tasks
- [ ] Release **code, generator and synthetic data** on GitHub and as a **Hugging Face dataset** with a dataset card.
- [ ] Write a **short technical report (4–6 pages)** in the humanizer-academic style.
- [ ] Record a **60-second screen recording** of the app.
- [ ] Update the **README** with reproduction instructions.
- [ ] Update the **resume entry** and the **statement-of-purpose paragraph**.
- [ ] State limitations plainly: no learner study; VtG solutions are simulated; VtG problems come from GSM8K and may be in pre-training data.

### Resume entry template
> **FirstSlip: verifiable error localization for LLM tutors** (live app, GitHub). Built a SymPy step checker and a controlled benchmark of N algebra solutions with known first errors across K misconception types. Showed that prompted LLMs locate the first error in X% of cases and adopt a deliberately wrong verifier location in Y% of cases. Trained a 2B model with GRPO using the checker as reward: A% to B% on held-out misconception types and C% on 802 teacher-annotated solutions (SFT: D%).

Short version (stopped at cut line): replace the last sentence with *"Deployed a tutor that marks which feedback the checker has verified."*

### Statement-of-purpose sentences
- **Dr. Xi Ye:** I built a benchmark in which the location of every reasoning error is known by construction, and used it to test whether a verifiable step-level reward trains a small model to find errors that transfer to human-annotated data.
- **Dr. Carrie Demmans Epp:** I built a tutor that tells learners which parts of its feedback a symbolic checker has confirmed, and found that LLM tutors repeat a wrong verifier's diagnosis in Y% of cases; a learner study of how students interpret this distinction is what I would like to run in EdTeKLA.

### Gate 6
- [ ] **A stranger can reproduce the E1 table from the repository README.**
- [ ] Fill in Phase 6 in [PROGRESS.md](PROGRESS.md).

---

## Deliverables checklist

| # | Deliverable | Phase | Done |
|---|---|---|---|
| 1 | Open-source generator and SymPy checker | 1 | [x] |
| 2 | Synthetic benchmark (seen + held-out) with dataset card | 1 | [x] |
| 3 | Prompted results for three models (localization, faithfulness, deference) | 2 | [x] |
| 4 | Live student app separating verified feedback from guesses | 3 | [ ] |
| 5 | Trained checkpoints (SFT, GRPO; 3 seeds) with held-out and VtG results | 4–5 | [ ] |
| 6 | 4–6 page technical report | 6 | [ ] |
| 7 | 60-second screen recording | 6 | [ ] |

## Risk register

| Risk | What could happen | Fallback |
|---|---|---|
| GRPO has no signal | All samples in a group get the same reward; update is zero | Easier items (two-step), more samples per prompt, or rejection-sampling FT (go/no-go 12 Nov caps cost at 2 days) |
| Model doesn't train well | Qwen3.5's newer layers slow/unsupported in Unsloth/TRL | Qwen3-1.7B |
| Generator takes longer | Misconception rules are fiddly | Start with 8 most common misconceptions |
| Position shortcut | Trained model guesses a common step number | Balanced positions, position-only baseline, predicted-position plot |
| Noisy VtG labels | Inconsistent teacher annotations | Report with and without "None of the above" |
| Parsing failures in app | Students type unparseable steps | MathLive, one equation per line, "could not read this line" |
| API cost | Many models × thousands of items | Cache, spending cap, full grid only on final prompt |
| Colab compute | Compute units run low in Phase 4 | GRPO runs < 3 h |
| Overclaiming | Synthetic result presented as learning outcome | State no learner study; VtG is simulated |

## Sources
- [VtG dataset card](https://huggingface.co/datasets/eth-nlped/stepverify)
- [Daheim et al., EMNLP 2024](https://aclanthology.org/2024.emnlp-main.478)
- [Srivatsa et al., 2025](https://arxiv.org/abs/2509.01395)
- [Sonkar et al., 2024 (MalAlgoPy)](https://arxiv.org/abs/2410.12294)
- [Liu et al., 2026 (MalAlgoLib)](https://arxiv.org/abs/2604.00818)
- [Note that MalAlgoPy has no public repository](https://github.com/viktor1223/ed/blob/main/SIMULATED_STUDENT_RESEARCH.md)
- [ProcessBench](https://arxiv.org/abs/2412.06559)
- [TRL GRPOTrainer documentation](https://huggingface.co/docs/trl/main/grpo_trainer)
- [Qwen3.5 small models](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- [Qwen3.5 small models, licence](https://eu.36kr.com/en/p/3706848726643078)
- [Unsloth notebooks](https://unsloth.ai/docs/get-started/unsloth-notebooks)
- [Kaggle GPU quota](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- [SymPy LaTeX parser](https://github.com/sympy/sympy/blob/95085aaa2de28fb98a3f4a07d4ca305b741e8a9a/sympy/parsing/latex/__init__.py)
- [SymPy](https://www.sympy.org/) · [MathLive](https://cortexjs.io/mathlive/) · [Xi Ye homepage](https://xiye17.github.io/)
