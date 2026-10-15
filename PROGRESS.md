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

- **Status:** ✅ complete (one small item open: run the Kaggle notebook)
- **Dates / hours:** 15 Oct 2026, one day ahead of plan. Reading A1–A5 and B1–B3 done beforehand.
- **Gate:** **passed.** Both VtG baselines are computed (`results/phase0/vtg_baselines.json`), and `PREREGISTRATION.md` is committed.

**What was done**
- Repo set up with `.venv`, pinned `requirements.txt` (Python 3.12.4; `datasets` 5.1.0, `sympy` 1.14.0, `numpy` 2.5.4, `pandas` 3.0.6, `scipy` 1.18.1) and `.gitignore`.
- `firstslip/` package:
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
- [ ] Upload and run `notebooks/phase0_kaggle_env_check.ipynb` on Kaggle (GPU T4 ×2, internet on), and confirm Colab as backup.
- [ ] Rebuild the correct-reduction edges of Figure 1 (only T9→T7→T2→T1 is given in the text).
- [ ] M6 needs negative outer factors, so make sure the generator samples them.

---

## Phase 1 — Generator and checker
_Planned: 19 – 27 Oct 2026, ~16 h · Gate: checker 100% on 2,000 generated items (incorrect and clean); 50 hand-checked_

- **Status:** not started
- **Dates / hours:**
- **Gate:**
- **What was done:**
- **Key results / numbers:** (split sizes, items dropped for accidental recovery, checker accuracy)
- **Artifacts:**
- **Deviations from plan:**
- **Issues / open questions:**
- **Carry-over:**

---

## Phase 2 — Prompted experiments E1–E3
_Planned: 28 Oct – 3 Nov 2026, ~15 h · Gate: all E1–E3 tables filled; extractor ≥ 90% agreement with hand labels_

- **Status:** not started
- **Dates / hours:**
- **Gate:**
- **What was done:**
- **Key results / numbers:** (E1 accuracies/F1 per model, E2 grounding effect, E3 deference rate, extractor agreement, API spend)
- **Artifacts:**
- **Deviations from plan:**
- **Issues / open questions:**
- **Carry-over:**

---

## Phase 3 — Student app (cut line)
_Planned: 4 – 9 Nov 2026, ~12 h · Gate: a friend can solve, make a mistake and get feedback on a phone_

- **Status:** not started
- **Dates / hours:**
- **Gate:**
- **What was done:**
- **Key results / numbers:**
- **Artifacts:** (Space URL, results page)
- **Deviations from plan:**
- **Issues / open questions:**
- **Carry-over:**

---

## Phase 4 — Training E4
_Planned: 10 – 17 Nov 2026, ~16 h · Go/no-go: 12 Nov · Gate: three seeds per condition evaluated, held-out results and position check reported_

- **Status:** not started
- **Dates / hours:**
- **Go/no-go decision (12 Nov):** GRPO kept / switched to rejection-sampling FT — reason:
- **Gate:**
- **What was done:**
- **Key results / numbers:** (Base / SFT / GRPO mean ± sd on seen and held-out tests, position-bias check, GPU hours used)
- **Artifacts:**
- **Deviations from plan:**
- **Issues / open questions:**
- **Carry-over:**

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
