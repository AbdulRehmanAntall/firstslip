# FirstSlip — Progress Log

Filled in at the **end of each phase**, once its gate is checked. See [PHASES.md](PHASES.md) for the full task list of each phase.

**Template for each phase:**
- **Dates / hours:** planned vs. actual
- **Gate:** passed / not passed (with evidence)
- **What was done:** bullet list of completed tasks
- **Key results / numbers:**
- **Artifacts:** files, commits, runs (git hash, JSONL log paths), links
- **Deviations from plan:** what changed and why
- **Issues / open questions:**
- **Carry-over to next phase:**

---

## Phase 0 — Setup and core reading
_Planned: 16 – 18 Oct 2026, ~6 h · Gate: both VtG baselines computed and `PREREGISTRATION.md` committed_

- **Status:** ✅ complete
- **Dates / hours:** 15 Oct 2026, one day ahead of plan. Reading A1–A5 and B1–B3 done beforehand.
- **Gate:** **passed.** Both VtG baselines are computed (`results/phase0/vtg_baselines.json`), and `PREREGISTRATION.md` is committed.

**What was done**
- Repo set up with `.venv`, pinned `requirements.txt` (Python 3.12.4; `datasets` 5.1.0, `sympy` 1.14.0, `numpy` 2.5.4, `pandas` 3.0.6, `scipy` 1.18.1) and `.gitignore`.
- `core/` package (shared code; renamed from `firstslip/`):
  - `runlog.py`: one JSONL per run, headed by git commit, seed and config hash.
  - `vtg.py`: loading, 1-based step convention, grouped split.
  - `stats.py`: bootstrap CI.
- Loaded VtG (`eth-nlped/stepverify`, 1,002 rows) and checked it against the proposal: "None of the above" is 87 rows (8.7%), and random expected accuracy is 18.2% (paper: 18.3%).
- Fixed the VtG split (`scripts/split_vtg.py`, seed `20261016`): **dev 200 / test 802**, grouped by problem, with 0 problems shared. Ids are in `data/vtg/split_ids.json`.
- Computed the random and position-only baselines (`scripts/vtg_baselines.py`). The position-only rule is fitted on VtG dev and scored on VtG test.
- Hand-inspected 30 VtG dev rows; notes are in `notes/vtg_inspection.md`.
- Pulled Sonkar et al. (2024) Table 1 and fixed the held-out misconceptions: **M2_S3 (distribution), M6 (sign), M20_S20 (division), M11 (term-combining)**.
- Wrote `PREREGISTRATION.md`, with testable criteria for every hypothesis.
- Wrote `notebooks/phase0_kaggle_env_check.ipynb`, which checks the GPUs, installs pinned packages and loads VtG plus the split.

**Key results / numbers.** VtG test, n = 802; 95% bootstrap CI with 10,000 resamples.

| Baseline | First-error acc. | 95% CI | Within-one |
|---|---|---|---|
| Random (expected, uniform over steps) | **18.2%** | — | 50.2% |
| Random (one seeded draw) | 21.1% | 18.3–23.9 | 49.0% |
| Position-only (mode per length, fit on dev) | **24.9%** | 21.9–27.9 | 65.6% |
| *Without "None of the above" (n = 724)* | | | |
| Random (expected) | 18.4% | — | 50.5% |
| Position-only | 24.7% | 21.7–27.8 | 65.8% |

- Position prior learned on dev, as solution length → step: 4→1, 5→3, 6→3, 7→1, 8→5, 9→3, 10→2, 13→5 (other lengths → 3).
- Any model must clear about **25%** on VtG to beat the position-only rule. GPT-4o's 54.5% (Srivatsa et al.) is well above it.
- **VtG label noise:** there are only 612 unique solutions. 235 solutions were annotated more than once, and those annotators agree on the first-error step only **60%** of the time (408/679 pairs).

**Artifacts**
- Commits `c9807ef` (code, split, docs), `bddef7d` (run-log fix) and the pre-registration commit (`git log -- PREREGISTRATION.md`).
- Run log `runs/20261015T124346Z_phase0_vtg_baselines.jsonl` (commit `bddef7d`, seed 0, config hash `0f6cb5c08526`).
- `results/phase0/vtg_baselines.json`, `notes/vtg_inspection.md`, `PREREGISTRATION.md`.

**Deviations from plan**
- The VtG dev/test split is **grouped by problem text** instead of plain random rows, because 390 rows repeat a problem. Dev still has exactly 200 rows.
- **Misconception count resolved:** Sonkar et al. Table 1 has 19 rows (the text says 20), so 15 seen + 4 held-out = 19, which is consistent with the proposal.
- **Equation types:** Sonkar et al. list only 15 forms (T13 is missing), so Phase 1 implements 15, not 16.
- Added a lenient VtG score (a prediction counts if it matches any teacher's label for that solution) as a secondary metric, because labels are noisy. The per-row score stays primary.
- The 30 inspected rows came from VtG dev only, so test stays unseen.

**Issues / open questions**
- Some VtG gold labels look wrong (ids 690, 688, 112). Leave them as they are and report the noise rather than relabel.
- The label-agreement figure came from a one-off check and is not yet saved as a script. Add it with the Phase 2 VtG evaluation code.
- M12_S15 and M13 have the same description in Table 1. Decide in Phase 1 whether they generate different steps (`(A ± B)x` vs `(A ± B)`), as the formulas suggest.

**Carry-over to Phase 1**
- [x] ~~Upload and run `notebooks/phase0_kaggle_env_check.ipynb` on Kaggle~~. Dropped on 16 Oct: all GPU work runs on Colab Pro.
- [ ] Rebuild the correct-reduction edges of Figure 1 (only T9→T7→T2→T1 is given in the text).
- [ ] M6 needs negative outer factors, so make sure the generator samples them.

---

## Phase 1 — Generator and checker
_Planned: 19 – 27 Oct 2026, ~16 h · Gate: checker 100% on 2,000 generated items (incorrect and clean); 50 hand-checked_

- **Status:** ✅ complete
- **Dates / hours:** 15 Oct 2026, ahead of plan.
- **Gate:** **passed.** On 2,000 generated items (1,500 incorrect, 500 clean), the checker finds the injected step on **100%** of incorrect items and reports no error on **100%** of clean items. The same holds on all 10,500 items (`results/phase1/gate.json`). 50 items were hand-checked, and all 50 agree (`notes/phase1_hand_check.md`).

**What was done**
- `core/checker.py`: the SymPy step checker.
  - Input: plain text through `parse_expr`, restricted to arithmetic on x because `parse_expr` evaluates its input, or LaTeX through `parse_latex(..., backend="lark")`.
  - Comparison: equations by `solveset` solution sets; expressions by `simplify(a - b) == 0` plus 5 numeric spot checks.
  - Output: the first changed step. Unreadable lines are flagged and skipped, never guessed.
- `core/generator.py`, rebuilt from Sonkar et al. (2024):
  - The 15 equation forms are one-step reductions. Correct edges are rebuilt from Figure 1; two intermediate states, T12d and T12m, are added.
  - The 19 misconceptions of Table 1 are alternative steps.
  - Labels come from exact `Fraction` arithmetic, so the gate tests the checker against an independent ground truth.
- `scripts/generate_synthetic.py`: train 8,000 / dev 500 / test-seen 1,000 / test-held-out 1,000.
  - One error per item, no accidental recovery, (length, position)-balanced cells, global deduplication by unevaluated SymPy form.
  - Coefficients in [−12, 12]; answers are integers or fractions with denominator ≤ 12; 3–6 steps.
  - Reproducible byte for byte from seed `20261019`.
- Dataset card: `data/synthetic/README.md`. File hashes and all counts: `data/synthetic/manifest.json`.
- `scripts/synthetic_baselines.py`: random and position-only baselines on the synthetic tests.
- `tests/` (pytest, 30 tests). `lark` and `pytest` added to `requirements.txt`.

**Key results / numbers**

| Split | Items | Incorrect | Clean | Misconceptions (incorrect items each) |
|---|---|---|---|---|
| train | 8,000 | 6,000 | 2,000 | 15 seen (341–510) |
| dev | 500 | 375 | 125 | 15 seen (20–32) |
| test_seen | 1,000 | 750 | 250 | 15 seen (42–64) |
| test_heldout | 1,000 | 750 | 250 | M2_S3 125, M6 125, M11 125, M20_S20 375 |

- **Accidental recovery:** 0 items dropped. With one wrong step followed by correct reductions, recovery cannot happen, but the check is kept. All other rejected candidates are counted per split in the dataset card.
- **Checker accuracy:** 100% / 100% on the gate sample and on all items. No unreadable or incomparable lines.

| Baseline (first-error acc.) | test_seen | test_heldout |
|---|---|---|
| Random (expected) | 24.9% | 21.7% |
| Position-only, fit on synthetic dev | **25.3%** (22.3–28.4) | **37.5%** (34.0–40.9) |
| Best possible position-only rule | 25.6% | 50.1% |

**Artifacts**
- Commit `2c10d15` (code).
- Run logs, all at `2c10d15`: `runs/20261015T133230Z_phase1_generate.jsonl`, `runs/20261015T133304Z_phase1_gate.jsonl` (one record per gate item), `runs/20261015T133745Z_phase1_synthetic_baselines.jsonl`.
- `results/phase1/gate.json`, `results/phase1/synthetic_baselines.json`, `data/synthetic/manifest.json`, `data/synthetic/README.md`, `notes/phase1_hand_check.md`.
- The `.jsonl` data files are git-ignored like VtG. They are regenerated with `python scripts/generate_synthetic.py`, and their hashes are in the manifest.

**Deviations from plan** (recorded as Amendment 1 in `PREREGISTRATION.md`)
- **Two intermediate states.** T12d (T12 after distributing) and T12m (T12 after moving B) were added. T12m gives 6-step solutions and lets distribution and M11 errors occur at steps 2–3.
- **Applicability narrowed or widened.**
  - M13 is applied only to T7; on T5/T6 it would leave no x.
  - M12_S15 and M13 reach T9/T12 only through the distributed T7 state.
  - The pair rules M14/M15/M17/M18 also apply to pairs inside T11 and T15.
  - M12_S15 and M13 are now distinct: M12_S15 gives (A ± B)x, while M13 drops the x.
- **Balanced positions cannot be fully met on the held-out test.** The four held-out misconceptions can only reach 8 (length, position) cells. Position-only fitted on dev scores 37.5% there. The H3 and anti-hypothesis comparisons on held-out must use that number, not random.
- **Misconceptions are balanced within reachable cells, not exactly.** Position balance was given priority.
- The proposal's 6,000/2,000 train sizes and 25% clean test sizes are met exactly.

**Issues / open questions**
- T12 is 34% of train and 63% of test-held-out, because only T12 gives 5–6-step solutions. Report results by start type or by length in Phase 2 to check this does not drive the numbers.
- Checker speed: the full 10,500-item check takes about 8.5 min because `solveset` dominates. This is fine offline. For the app, the per-line cache in `parse_line` is enough.

**Carry-over to Phase 2**
- [x] ~~Run the Phase 0 Kaggle notebook~~. Dropped: Colab Pro is used instead.
- [ ] Report the E1 held-out results against the 37.5% position-only baseline as well as random.
- [ ] Use `core.checker.check` for the E2 grounded condition and `first_error` from the data for E3's corrupted locations.

---

## Phase 2 — Prompted experiments E1–E3
_Planned: 28 Oct – 3 Nov 2026, ~15 h · Gate: all E1–E3 tables filled; extractor ≥ 90% agreement with hand labels_

- **Status:** done. All three models (Qwen3.5-2B, 4B, 27B) have been run on the full grid (dev + test), judged (Amendment 5) and scored.
- **Dates / hours:** started 16 Oct 2026. Qwen runs 16 Oct, 14:58–15:38 UTC; judge test run 17 Oct, 01:23–01:51 UTC; Colab A100.
- **Gate:** **passed** (via Amendment 5). The E1–E3 tables are filled for all three models. The rule-based extractor agrees with hand labels on only 21% (13–29%), but the LLM judge (j-v1) agrees on **97%** (93–100%) of the 100 audited items, above the 90% bar (`results/phase2/audit.json`).
- **What was done:**
  - Prompt template and strict parser (`core/prompts.py`, `PROMPT_VERSION` p2-v1, not yet frozen).
  - OpenAI client with an SQLite response cache and a hard $5 cap checked before each call (`core/llm.py`, `config/phase2.json`).
  - Faithfulness extractor and misconception mapping.
  - McNemar, paired bootstrap and Holm (`core/stats.py`).
  - Runners for the API model (`scripts/phase2_run.py`) and the open models (`scripts/phase2_run_vllm.py`), the scorer and audit scripts, and the Colab notebook (`notebooks/phase2_colab_vllm.ipynb`).
  - Design decisions recorded as Amendments 2 and 3 in `PREREGISTRATION.md`.
  - 27 new tests; 57 in total pass.
- **Key results / numbers:** (E1 accuracies/F1 per model, E2 grounding effect, E3 deference rate, extractor agreement, API spend)
  - Projected API cost of the full grid at ~400 output tokens per reply: `gpt-6-luna` ≈ $0.93. `gpt-6.1-sol` would cost about $18.6, over the $5 cap.
  - The frontier model was therefore replaced by Qwen3.5-27B (FP8), run on the Colab A100 like the small Qwen models (Amendment 3). All four models answer every item.
  - `gpt-6-luna` was then removed from the plan (Amendment 4), so the study has three open models and no API spend. Hypothesis thresholds became "at least 2 of 3 models"; no outcome changes.
  - Test results, prompt p2-v1, greedy decoding, 100% parse rate for every model. 95% bootstrap CIs.

  | First-error acc. (E1) | test_seen | test_heldout | VtG test (802) | VtG w/o NOTA |
  |---|---|---|---|---|
  | Random (expected) | 24.9 | 21.7 | 18.2 | |
  | Position-only | 25.3 | 37.5 | 24.9 | |
  | Qwen3.5-2B | 34.8 (31.5–38.1) | 26.7 (23.5–29.9) | 31.2 (27.9–34.4) | 32.9 |
  | Qwen3.5-4B | 67.9 (64.5–71.1) | 49.3 (45.7–52.9) | 46.3 (42.8–49.6) | 47.2 |
  | Qwen3.5-27B | **95.3** (93.7–96.8) | **87.2** (84.8–89.6) | **61.2** (57.7–64.6) | 62.7 |

  - Clean accuracy (answering 0 on correct solutions) is low: 27B 50.8 / 40.4%, 4B 36.4 / 24.4%, 2B ≈ 0%. Error F1 on seen / held-out: 27B 66.3 / 55.2, 4B 47.4 / 32.7, 2B 0.8 / 0.0. Every model is biased towards flagging an error.
  - Every pairwise model difference is significant (McNemar, Holm, all p < 1e-14).
  - 6-step items are much harder (27B 74% on seen, 68% on held-out; 4B 30% / 4%). Held-out is 63% T12 (6-step), so length explains part of the seen → held-out drop.
  - **H1 (solving):** localization is *higher* than solving for all three models (27B 95.3 vs 48.4, 4B 67.9 vs 10.5, 2B 34.8 vs 6.4; all CIs exclude 0). This is the opposite direction, so **H1 is not supported** (0 of 3).
  - **E2 (location given):** misconception accuracy does not rise. Seen: all diffs ≈ 0. Held-out: 27B −8.9 (p = 2e-14), 2B +3.6 (p = 0.001), 4B −0.5. With the true location supplied, 27B's step accuracy *falls* from 95.3 to 91.1 on seen. H2 is provisionally **not supported**, pending the mapping audit (see Issues).
  - **E3 (deference):** 27B 1.7 / 3.2% (one-off / random wrong, seen) and 4.1 / 7.1% (held-out); 4B 10.4 / 16.1% and 8.5 / 17.2%; 2B 99.9–100%. The 2B model copies whatever step it is given, true or wrong. Only 1 of 3 models is above 50%, so **H2b is not supported**.
  - **H1b (faithfulness):** among feedback that names a step, the share naming a different step is 27B 13.3% (11.1–15.6), 4B 11.8%, 2B 10.7% on seen. Supported if the extractor passes its audit.
  - **Hand audits** (100 items each, binary labels; see Deviations):
    - Faithfulness: by hand, **87%** (80–93%) of feedback is about the flagged step, so 13% is not. The extractor calls only 20% faithful. Agreement is 21%. 69 of the 87 faithful items are *unspecified* to the extractor, and where it does name a step it agrees 17 / 27 times. **The extractor fails Gate 2.** By hand, the unfaithful share is 13% (7–20%), above the 5% bar, so H1b is supported on hand labels (pooled over models and splits).
    - Misconception: by hand, **48%** (38–58%) of feedback correctly diagnoses the error. The mapping (m-v1) gives the true label for 25%. Agreement is 69% (60–78%). Of the 48 correct diagnoses, the mapping finds 21; 23 are unmapped and 4 get the wrong label. Automatic misconception accuracy therefore under-reports correct diagnoses by about half.
  - Dev results (`results/phase2/tables_dev.md`) show the same pattern (27B 95.7%, 4B 67.5%, 2B 33.1% on synthetic dev).
- **Artifacts:**
  - 39 run logs `runs/20261016T1458*Z_phase2_*` – `runs/20261016T153752Z_phase2_solve_test_seen_qwen-27b.jsonl`, all at commit `89dbe3b` (dirty), vLLM 0.31.0. Model revisions are in each header.
  - `results/phase2/tables.{json,md}`, `results/phase2/tables_dev.{json,md}`.
  - `notes/phase2_audit_faithfulness.csv`, `notes/phase2_audit_misconception.csv` (unlabelled).
- **Deviations from plan:**
  - The hand audits used binary labels instead of the step number / misconception ID in Amendment 2, item 5. Faithfulness: 1 = feedback is about the flagged step. Misconception: 1 = feedback correctly diagnoses the error. `scripts/phase2_audit.py score` scores both forms. This collapses *unfaithful* and *unspecified* into one class, and tests whether the mapping's verdict is right rather than whether it picks the same label as the annotator.
  - The dev and test grids were run in one session with p2-v1. The prompt was never revised on dev, so p2-v1 is the frozen prompt by default. No prompt or rule was changed after seeing test results.
  - The run logs record a dirty working tree at `89dbe3b`.
- **Issues / open questions:**
  - **The faithfulness extractor rarely finds a step.** Models describe the operation ("sign error when distributing the -3") instead of writing "step 2" or quoting a whole step. *Unspecified* is 53–65% on seen and 63–92% on held-out / VtG, so H1b rests on a minority of responses. The audit will show whether those are true "none"s or misses.
  - **The misconception mapping (m-v1) misses common wordings.** Example: "sign error when distributing the -3, as -3 × -7 should be +21" is unmapped, because the M6 rule needs the word "negative". "Forgot to multiply the -9 by 2 when distributing" maps to M1, not M2_S3. On test_seen, 63–79% of feedback is unmapped. Label accuracy on seen (3–6%) is therefore mostly a mapping failure, not a model failure, and the held-out numbers (27B 47.5%) are inflated by the M20_S20 rule matching "divide both sides". Any fix must be made on dev only and recorded as an amendment, followed by re-scoring. The test numbers above use m-v1 as preregistered.
  - The 2B model's 100% deference and ≈ 0% clean accuracy mean it is not reading the solution in E2/E3. Report it, but do not interpret its E2 numbers as an effect of grounding.
- **Carry-over:**
  - [x] Hand audits labelled and scored (`results/phase2/audit.json`).
  - [x] Decided: replace both with an LLM judge (Amendment 5). Code: `core/judge.py` (j-v1), `scripts/phase2_judge_vllm.py`, Steps 3–4 of the Colab notebook; the scorer and audit read the judge logs.
  - [x] Run the judge on dev (notebook Step 3), check the parse rate and outputs, then freeze j-v1.
    - 12 logs `runs/20261016T164132Z_phase2judge_*` – `runs/20261016T164803Z_phase2judge_diag_e2_dev_qwen-4b.jsonl`, at `799c293` (dirty: notebook only), vLLM 0.31.0, Qwen3.5-27B-FP8 @ `97f5941bf617`.
    - Parse rate 100% on all 4,190 judgements. Every output is a single `Step: n` / `Verdict: yes|no` line.
    - Read-through (~40 items over all classes): unfaithful cases are real (often the 2B model flags step 1 and then criticises step 2). `Step: 0` is almost always self-retracting feedback ("wait, let me re-evaluate … Step 1 is correct"). Diagnosis "no" covers wrong corrections and misread problems. A few borderline cases, but no systematic error. **j-v1 frozen unchanged.**
    - Unspecified falls from 53–92% (extractor) to 0–9%. Dev faithful / unfaithful / unspecified: 27B 94.6 / 1.6 / 3.9%, 4B 86.1 / 11.2 / 2.7%, 2B 65.2 / 25.8 / 9.0% (VtG dev: 95.9 / 4.1 / 0, 82.5 / 16.9 / 0.5, 83.0 / 13.1 / 4.0%).
    - Dev diagnosis accuracy, none → given: 27B 49.9 → 44.5%, 4B 19.7 → 19.7%, 2B 7.5 → 14.4%. This is the same pattern as the m-v1 test result.
  - [x] Run the judge on test (Step 4), then `python scripts/phase2_score.py` and `python scripts/phase2_audit.py score`. Gate 2 passes if judge faithfulness agreement is ≥ 90%.
    - 21 logs `runs/20261017T012327Z_phase2judge_faith_e1_test_seen_qwen-27b.jsonl` – `runs/20261017T015041Z_phase2judge_diag_e2_test_heldout_qwen-4b.jsonl`, at `8eb9479` (dirty), j-v1, vLLM 0.31.0, Qwen3.5-27B-FP8 @ `97f5941bf617`. Parse rate 100% on all 16,793 judgements.
    - A first Step 4 attempt crashed before judging anything: the synthetic `.jsonl` files are gitignored and the regenerate cell had not been run in that Colab session. The Step 4 zip pattern now matches test logs only, so a failed run can no longer ship the dev logs.
    - **Validation against the hand labels:** faithfulness agreement **97%** (93–100%), so **Gate 2 passes**. Diagnosis agreement 88% (81–94%); the judge calls 38% correct vs 48% by hand, so it is somewhat strict.
    - **H1b (judge):** unfaithful share on test_seen: 2B 24.5% (21.9–27.2), 4B 9.3% (7.3–11.2), 27B 0.8% (0.2–1.4). The CI lower bound is ≥ 5% for 2B and 4B, so **H1b is supported**. Held-out and VtG show the same order (2B 23.3 / 18.8%, 4B 5.4 / 17.2%, 27B 0.4 / 2.3%).
    - **H2 (judge diagnosis, none → given):** seen 27B 46.9 → 48.9 (p = 0.60), 4B 18.1 → 17.7 (p = 0.89), 2B 9.6 → 14.1 (p = 0.005); held-out 27B 76.5 → 77.5, 4B 31.9 → 35.1 (p = 0.14), 2B 12.8 → 17.7 (p = 0.005). Only 2B rises significantly, and 2B copies the given step 100% of the time (E3), so this is not evidence of grounding. 1 of 3 models: **H2 is not supported.**

---

## Phase 3 — Student app (cut line)
_Planned: 4 – 9 Nov 2026, ~12 h · Gate: a friend can solve, make a mistake and get feedback on a phone_

- **Status:** ✅ complete. App deployed as a static Space: https://huggingface.co/spaces/AbdulRehman420/firstslip.
- **Dates / hours:** started 17 Oct 2026.
- **Gate:** **passed** on 24 Oct 2026.
  - Friend test: a friend solved a problem on a phone, made a mistake and got the checker's feedback (reported by the author; no observations recorded).
  - Deliverables 1–4 exist: generator + checker (`core/`), synthetic benchmark + dataset card (`data/synthetic/README.md`), prompted results (`results/phase2/`), live app.
  - Resume entry written (below).
- **What was done:**
  - `app/main.py`: FastAPI. `POST /api/check` takes the problem and steps (MathLive LaTeX) and returns a status per step (`same` / `changed` / `unreadable` / `incomparable` / `empty`), the checker's verified claims, and, when a step is wrong, the model's explanation. `/` is the checker, `/results` the E1–E3 findings. No API docs routes.
  - `app/checking.py`: the Phase 1 checker (`core.checker.parse_line` / `same`, unchanged), applied line by line. Verified claims: the first step that changes the answer, with the solution before and after it; unreadable lines; or "every step keeps the solution".
  - `app/mathnorm.py`: MathLive LaTeX → plain text for the checker. The plain path reads `\cdot`, Unicode minus and decimals (as exact fractions), which SymPy's LaTeX parser rejects or turns into floats; `\sqrt` and the like fall back to the LaTeX parser.
  - `app/feedback.py`: Qwen3.5-27B through Hugging Face Inference Providers, with the frozen prompt p2-v1 in the E2 "true location" condition (the model is told the checker's step). The reply is shown as *not verified*; if its step differs from the checker's, the page warns that it may be about the wrong step (H1b). The model is only called when the checker finds an error.
  - `app/static/`: single page with one MathLive field per step, ✓ / ✗ / ? per step, a *Verified* panel and a separate *Not verified* panel; "New problem" and "Show an example with a mistake" buttons; results page with the Phase 2 charts.
  - Caps (in memory only): 40 checks and 15 model explanations per session cookie, 300 model explanations per day in total. No access log; nothing typed is stored.
  - `space/` (Dockerfile, Space README, requirements) and `scripts/deploy_space.py`, which uploads only `space/`, `app/` and the three `core` files the app needs.
  - Browser build: the page runs the checker itself with Pyodide 0.26.4, loading `core/checker.py`, `app/checking.py` and `app/mathnorm.py` unchanged and SymPy 1.14.0 / mpmath 1.3.0 / lark 1.3.1 from PyPI (the study's versions). First load about 10 s, then each check takes 40–600 ms (measured in Node's Pyodide on the five test cases; same results as the server). The model's guess comes from `POST api/explain` when a server provides it; on static hosting the page says no model is attached.
  - `scripts/deploy_space.py`: static bundle by default (`space/static/README.md`, `app/static/`, `py/<the five files>`); `--docker` deploys the FastAPI server (`space/docker/`).
  - 30 new tests (`tests/test_app.py`); 89 in total pass.
- **Key results / numbers:** one manual end-to-end test on a phone (the friend test). Automated: 30 app tests; the browser checker matches the server on the five test cases.
- **Resume entry.** The cut-line version, as Gate 3 requires:
  > **FirstSlip: verifiable error localization for LLM tutors** (live app, GitHub). Built a SymPy step checker and a controlled benchmark of 10,500 algebra solutions with known first errors across 19 misconception types. Showed that prompted LLMs locate the first error in 35–95% of cases (Qwen3.5 2B–27B) and adopt a deliberately wrong verifier location in 2–100% of cases. Deployed a tutor that marks which feedback the checker has verified.
- **Resume entry, current version** (Phase 4 done; to be finalised in Phase 6):
  > … Fine-tuned a 2B model using the checker as label and reward: first-error accuracy on held-out misconception types rose from 27% to 68% with SFT and 49% with GRPO, but neither transferred to 802 teacher-annotated solutions (base 31%, SFT 19%, GRPO 28%).
- **Artifacts:** Space https://huggingface.co/spaces/AbdulRehman420/firstslip (app: https://abdulrehman420-firstslip.static.hf.space, results page: `/results.html`).
- **Deviations from plan:**
  - **Static Space, checker only.** Hugging Face now requires PRO to host Docker or Gradio Spaces, even on free CPU (HTTP 402 on 17 Oct). The deployed app is therefore a static Space: the checker runs in the browser and there is no model explanation. The verified / not-verified split is in the page, but only the verified panel has content online. The per-session cap is not needed there, since nothing runs on a server; the caps are in the server version (`app/main.py`), which can be deployed with `--docker` if PRO is added.
  - In the server version, the app calls `Qwen/Qwen3.5-27B` (BF16, served by Inference Providers) rather than the FP8 checkpoint used in Phase 2, and providers may differ in numerics. The prompt is the same frozen p2-v1.
- **Issues / open questions:**
  - The Hugging Face account has no Inference Providers credit (HTTP 402 on 17 Oct), so the server version could not be tested against the live model; its model path is covered by tests with a fake client only.
  - The page has not been checked in a real browser by the assistant (no browser tool available); the Python path was checked in Node's Pyodide and the files on the Space were checked over HTTP.
- **Carry-over:**
  - [x] Deploy the Space (static).
  - [ ] Optional: HF PRO + inference credit, then `python scripts/deploy_space.py --repo AbdulRehman420/firstslip --docker` and a read token as the `HF_TOKEN` secret, to add the model's explanation.
  - [x] Gate: a friend solves a problem on a phone, makes a mistake and gets feedback (24 Oct).
  - [x] Short resume entry.
  - [ ] Readings D1–D6 (optional).
- **Order deviation:** Gate 3 was closed on 24 Oct, after Phase 4 had already run (21–24 Oct).

---

## Phase 4 — Training E4
_Planned: 10 – 17 Nov 2026, ~16 h · Go/no-go: 12 Nov · Gate: three seeds per condition evaluated, held-out results and position check reported_

- **Status:** ✅ complete
- **Dates / hours:** code 21 Oct, training and evaluation 23–24 Oct 2026, about 17 days ahead of plan. GPU: about 5 h of training on one A100 40 GB (SFT 8 min per seed, GRPO 1.5 h per seed) plus about 1.5 h of evaluation.
- **Go/no-go decision:** **GRPO kept.** For seed 0, mean reward rose from 0.46 (first 20 steps) to 0.95 (last 20). Dev first-error accuracy is above base (33.1%) at every checkpoint, from 77.9% at step 50 to 85.1% at step 400.
- **Gate:** **passed.** Three seeds each for SFT and GRPO, plus the greedy base model, are evaluated on dev, test-seen, test-held-out and VtG test. The position check is in `results/phase4/f_position.png`.

**What was done**
- `core/phase4.py`: the step-only SFT target, the checker reward (step + format), and training rows labelled by the SymPy checker. Pre-registered as Amendment 6 before any run.
- `scripts/phase4_prepare.py`: 8,000 train and 500 dev rows. The checker matches the generator label on every row. Hashes are in `data/phase4/manifest.json`.
- `scripts/phase4_train.py`: TRL 1.16 SFT/GRPO with LoRA; GRPO generates with vLLM in colocate mode. `scripts/phase4_eval.py` merges each adapter and decodes greedily with the frozen p2-v1 prompt. `scripts/phase4_score.py` computes the tables, H3, H4 and the position check.
- `notebooks/phase4_colab_train.ipynb`: smoke tests, then base, SFT ×3, GRPO seed 0 with dev checkpoints, then GRPO seeds 1–2.

**Key results.** Mean ± sd over 3 seeds, in %. Base is one greedy run. Full tables are in `results/phase4/tables.md`.

| Split | Condition | First-error | Clean | Error F1 | Within-one |
|---|---|---|---|---|---|
| Test-seen | Base | 34.8 | 0.4 | 0.8 | 55.2 |
| | SFT | 99.6 ± 0.3 | 99.5 ± 0.6 | 99.5 ± 0.3 | 99.6 ± 0.3 |
| | GRPO | 84.6 ± 3.1 | 73.5 ± 15.4 | 78.2 ± 9.7 | 88.3 ± 1.2 |
| Test-held-out | Base | 26.9 | 0.0 | 0.0 | 40.8 |
| | SFT | 67.9 ± 3.9 | 98.0 ± 0.8 | 80.1 ± 2.6 | 81.1 ± 1.4 |
| | GRPO | 48.6 ± 21.9 | 59.7 ± 20.4 | 51.6 ± 15.3 | 68.5 ± 20.8 |
| VtG test | Base | 31.2 | – | – | 58.5 |
| | SFT | 18.6 ± 4.3 | – | – | 42.1 ± 6.1 |
| | GRPO | 27.8 ± 2.3 | – | – | 54.7 ± 2.1 |

- **H3: supported for both, by the pre-registered F1 rule.**
  - Test-seen F1 gain over base: SFT +98.7 (sd 0.3), GRPO +77.4 (sd 9.7).
  - Held-out gain: SFT +80.1 and GRPO +51.6, both at least half the seen gain.
  - **But the prediction that only GRPO would hold its gain is not borne out.** SFT is better than GRPO on every synthetic metric, with gaps larger than either sd. GRPO is also much less stable across seeds: held-out first-error is 73.1 / 30.9 / 41.7%.
- **Caveat on the F1 rule (not pre-registered).** Base never answers "no error", so its F1 is 0, and part of every F1 gain is just learning to say 0 on clean items. On first-error accuracy alone, the held-out gain is 63% of the seen gain for SFT (+41.0 vs +64.8), but 44% for GRPO (+21.7 vs +49.8), below half.
- **Anti-hypothesis (position prior): rejected for SFT; GRPO is mixed.**
  - Held-out first-error vs. the 37.5% position-only baseline: SFT beats it on every seed (72.1 / 64.5 / 66.9). GRPO's mean beats it (48.6), but seed 1 (30.9) does not.
  - The predicted-step distributions of both trained models follow the gold distribution. The **base** model is the one with a position bias: it answers step 1 on 88% (seen) and 93% (held-out) of incorrect items.
- **Error pattern on held-out.** SFT is never too early or too late: when it misses, it says "no error" (27–35% of incorrect items). GRPO misses in every direction.
- **H4 (computed early; E5 is Phase 5): not supported.** Transfer to VtG is negative for both: SFT −12.6 (sd 4.3), GRPO −3.4 (sd 2.3). SFT answers "no error" on 40–51% of VtG items, all of which contain an error; base does so on 7%.

**Artifacts**
- Code commit `197b6e7`, which all 45 run logs carry, with no local changes.
- Run logs: `runs/*_phase4train_*.jsonl` (config, versions, model SHA `15852e8c16…`, full trainer log history) and `runs/*_phase4_*.jsonl` (evaluations, Phase 2 record format).
- `results/phase4/tables.{json,md}` and `results/phase4/f_position.png`.

**Deviations from plan**
- Code was written before the C3/C4 reading (agreed 21 Oct), and Phase 4 ran before Gate 3 was closed.
- Unsloth was not used; plain TRL + PEFT on an A100 instead (Amendment 6, item 4).
- Qwen3.5-2B trained without problems, so the Qwen3-1.7B fallback was not needed.

**Issues / open questions**
- **GRPO saturates.** By the last 20 steps, 94–99% of groups have zero reward variance (`frac_reward_zero_std`), so the final steps carry almost no learning signal. Clean accuracy jumps between checkpoints (dev: 0.8% at step 200, 84.8% at 350, 69.6% at 400), which explains the large sd.
- **Long feedback.** Every trained output has a feedback sentence, but some run on to the 256-token cap (SFT seed 0: 42% on VtG, base 7%). Feedback length must be reported with E6, and the judge should read only the first sentence.
- **SFT near 100% on test-seen** is expected: the generator's 15 seen misconceptions are learnable patterns. Held-out and VtG are the informative splits.

**Carry-over to Phase 5**
- E5: the VtG results are already in the run logs. Add the "None of the above" and per-category breakdowns.
- E6: run the faithfulness judge (j-v1) on the trained models' feedback, Base vs. SFT vs. GRPO.
- Resume numbers (Phase 6 template): GRPO held-out first-error 26.9% → 48.6% (SFT 67.9%), VtG 27.8% (SFT 18.6%, base 31.2%).

---

## Phase 5 — Transfer and faithfulness E5, E6
_Planned: 18 – 21 Nov 2026, ~8 h · Gate: every hypothesis marked supported / not supported / inconclusive with evidence_

- **Status:** not started
- **Dates / hours:**
- **Gate:**
- **What was done:**
- **Key results / numbers:** (VtG results overall, by category, without "None of the above"; faithfulness before vs. after training)

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1 | | |
| H1b | | |
| H2 | | |
| H2b | | |
| H3 | | |
| Anti-hypothesis (position prior) | | |
| H4 | | |
| H4b | | |

- **Artifacts:**
- **Deviations from plan:**
- **Issues / open questions:**
- **Carry-over:**

---

## Phase 6 — Release and write-up
_Planned: 22 – 24 Nov 2026, ~9 h · Gate: a stranger can reproduce the E1 table from the README_

- **Status:** not started
- **Dates / hours:**
- **Gate:**
- **What was done:**
- **Key results / numbers:**
- **Artifacts:** (GitHub release, HF dataset, report PDF, screen recording)
- **Deviations from plan:**
- **Issues / open questions:**
- **Final resume entry:**
