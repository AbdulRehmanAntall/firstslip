# FirstSlip — Pre-registration

- **Fixed on:** 2026-10-15 (Phase 0), before any data generation or model run.
- **Author:** Abdul Rehman
- **Rule:** once committed, this file is not edited. Any later change goes in the *Amendments* section at the bottom, with a date and a reason. Every hypothesis is reported as supported, not supported or inconclusive, and a null result is reported as a null result.

The only results that existed before this file are the VtG baselines (random and position-only; `results/phase0/vtg_baselines.json`). They involve no model.

---

## 1. Research questions and hypotheses

### RQ1 — Measurement
How often do current LLMs locate the first wrong step in a student's algebra solution, name the misconception, and write feedback about the same step they flagged?

- **H1:** Localization accuracy on synthetic algebra will be well below the models' accuracy at solving the same equations, as reported for word problems.
  - *Test:* for each model, first-error accuracy on test-seen vs. solving accuracy on the same equations (each model is asked to solve each equation once). Supported if localization accuracy is lower and the paired bootstrap 95% CI of the difference excludes 0, for at least 3 of the 4 models.
- **H1b:** In a measurable share of responses, the written feedback discusses a step other than the one the model flagged.
  - *Test:* 1 − faithfulness on E1 responses. Supported if the lower bound of its 95% CI is ≥ 5% for at least one model.

### RQ2 — Grounding and trust
Does giving the model the checker's error location improve its feedback, and when that location is deliberately wrong, how often does the model repeat it?

- **H2:** Correct locations raise feedback accuracy, consistent with Daheim et al. (2024).
  - *Test:* E2, location given vs. not given. Supported if misconception accuracy is higher with the location (McNemar, Holm-corrected p < 0.05) for at least 3 of 4 models.
- **H2b:** Models will adopt a wrong location in most cases rather than contradict it.
  - *Test:* E3 deference rate under the one-off and random-wrong conditions. Supported if the deference rate is > 50% (95% CI lower bound > 50%) for at least 3 of 4 models.

### RQ3 — Training from the checker
Does reinforcement learning with the checker as reward improve error localization in a small open model, compared with SFT on the same labels?

- **H3:** Both SFT and GRPO improve over the base model on misconception types seen in training. Only a model that learned to check steps, rather than recognise error patterns, will hold its gain on held-out misconception types.
  - *Test:* error F1 on test-seen and test-held-out, mean ± sd over 3 seeds. "Improves" means the mean gain over base is larger than the between-seed sd. "Holds its gain" means the held-out gain is at least half the seen gain.
- **Anti-hypothesis (position prior):** the gain reduces to guessing the most common error step for each solution length.
  - *Test:* compare trained models with the position-only baseline (fitted on synthetic dev) and plot the predicted-step distribution against the gold distribution. If a trained model does not beat the position-only baseline on held-out data, its gain is reported as explained by the position prior.

### RQ4 — Transfer and side effects
Does the gain carry over to VtG, where no checker applies? Does rewarding only the step number change how faithful the explanations are?

- **H4:** Transfer to VtG will be positive but much smaller than the in-domain gain, because VtG errors are mostly misreadings of word problems rather than algebraic slips.
  - *Test:* VtG-test first-error accuracy gain over base (mean over seeds) > between-seed sd, and smaller than the test-seen gain.
- **H4b:** No prediction is made about faithfulness. The direction of the change after training is the finding (E6).

---

## 2. Misconceptions and the held-out choice

Source: Sonkar et al. (2024), Table 1. The table lists **19 misconceptions**, although the paper's text says "20 common misconceptions". FirstSlip uses the 19 table rows, so **15 seen + 4 held-out = 19**, which matches the proposal. The table does not group misconceptions into families. The family assignment below is FirstSlip's own.

| ID | Rule (A, B, C, D are coefficients) | Applies to | Family | Split |
|---|---|---|---|---|
| M1 | A(part) → A + (part) | T8, T9, T10, T12 | Distribution | seen |
| **M2_S3** | A(Bx ± C) → ABx ± C (distributes to the first term only) | T9, T12 | Distribution | **held-out** |
| M3 | A ± B(part) → (A ± B)(part) | T10, T12 | Distribution | seen |
| M4 | A(B·C) → AB·AC | T8 | Distribution | seen |
| M5 | A(Bx ± C) → A(ABx ± AC) | T9, T12 | Distribution | seen |
| **M6** | −A(Bx − C) → −ABx − AC (sign error with a negative factor) | T9, T12 | Sign / operation | **held-out** |
| M8 | A(Bx ± C) → Bx ± AC | T9, T12 | Distribution | seen |
| **M11** | Ax ± B = Cx ± D → Ax + Cx = B + D (combines terms across `=` without changing signs) | T14 | Term-combining | **held-out** |
| M12_S15 | Ax ± B → (A ± B)x | T5, T6, T7, T9, T12 | Term-combining | seen |
| M13 | Ax ± B → (A ± B) | T5, T6, T7, T9, T12 | Term-combining | seen |
| M14 | part1 + part2 → part1 − part2 | T2, T4 | Sign / operation | seen |
| M15 | part1 − part2 → part1 + part2 | T2, T4 | Sign / operation | seen |
| M16 | part1 · part2 → part1 + part2 | T3, T10 | Sign / operation | seen |
| M17 | A + B → B − A | T2, T4 | Sign / operation | seen |
| M18 | A − B → B − A | T2, T4 | Sign / operation | seen |
| M19 | Ax = B → x = A + B | all | Division | seen |
| **M20_S20** | Ax = B → x = B (divides one side only) | all | Division | **held-out** |
| M21 | Ax = B → x = A − B | all | Division | seen |
| M22_S1 | Ax = B → x = A / B (inverted division) | all | Division | seen |

**Held-out set (fixed): M2_S3 (distribution), M6 (sign), M20_S20 (division), M11 (term-combining).**

Why these four:
- M2_S3 and M20_S20 are the proposal's own examples: distributing to the first term only, and dividing one side only.
- M6 is the clearest sign error. It needs a negative outer factor, which seen items also contain, so the held-out items are not out of distribution in their surface form.
- M11 rather than M12/M13: Table 1 gives M12_S15 and M13 the same description, so holding out one would leave a near-twin in training. Holding out both would make five held-out misconceptions.

Held-out misconceptions never appear in train, dev or test-seen.

## 3. Equation types

Sonkar et al. define V = {T1, …, T16}, but Figure 1 lists only **15 forms (T13 is absent)**. FirstSlip implements these 15 forms. The proposal's "16 equation types" means this set.

T1 Ax = B · T2 Ax = B + C · T3 Ax = B·C · T4 Ax + Bx = C · T5 Ax + B = C · T6 A + Bx = C · T7 Ax = Bx + C · T8 Ax = B(C·D) · T9 Ax = B(Cx + D) · T10 Ax = B + C·D · T11 A + Bx + Cx = D · T12 Ax = B + C(Dx + E) · T14 Ax + B = Cx + D · T15 Ax + Bx = C + D · T16 Ax = Bx + C + D

Each correct reduction is one step and ends at T1 (for example T9 → T7 → T2 → T1). The full set of correct edges is rebuilt in Phase 1 and documented in the dataset card.

## 4. Data

### Generator rules
1. Each incorrect solution contains exactly one injected misconception, and the checker must confirm the solution set changes at that step.
2. No later step may return to the correct answer by chance. Such items are dropped and counted.
3. The first-error position is balanced across step indices.
4. Equations are deduplicated by canonical SymPy form across all splits.
5. Coefficients are integers in [−12, 12]. Answers are integers or simple fractions. Solutions have 3–6 steps.

### Splits

| Split | Source | Size | Use |
|---|---|---|---|
| Train | Generator, 15 seen misconceptions | 6,000 incorrect + 2,000 clean | SFT and GRPO |
| Dev | Generator, 15 seen | 500 | Prompt tuning, early stopping, GRPO go/no-go, position-prior fit |
| Test-seen | Generator, 15 seen, new equations | 1,000 (25% clean) | In-domain results |
| Test-held-out | Generator, 4 held-out only | 1,000 (25% clean) | Checking vs. pattern recognition |
| VtG dev | VtG, 200 rows | 200 | Prompt format only; never for training |
| VtG test | VtG, remaining rows | 802 | Transfer test |

**VtG split (already fixed):** seed `20261016`, **grouped by problem text** so that no problem, and so no repeated solution, appears in both dev and test. Dev has exactly 200 rows. Row ids are in `data/vtg/split_ids.json`. This differs from the proposal's plain random 200 rows because 390 VtG rows repeat a problem (see `notes/vtg_inspection.md`).

### VtG handling
- Step numbers are 1-based with 0 meaning "no error". VtG's 0-based `incorrect_index` is shifted by 1.
- The final list element (the bare answer) counts as a step, which matches the 18.3% random baseline of Srivatsa et al.
- Report all 802 test rows **and** the same set without "None of the above".
- *Added after inspection:* VtG has 612 unique solutions, and teachers who annotated the same solution agree on the first-error step only 60% of the time. Also report a **lenient** score that counts a prediction as correct if it matches any teacher's label for that solution, and quote the 60% agreement as a reference ceiling. The per-row score stays the primary VtG metric.
- Limitation stated in every write-up: VtG problems come from GSM8K and may be in pre-training data, and VtG solutions are LLM-simulated (MathDial), not real student work.

## 5. Output format, metrics and statistics

**Output format:** the first wrong step number (or 0 for no error), then one sentence of feedback. The same prompt template and parser are used for every model and frozen on the dev splits before any test run.

**Metrics**
- First-error accuracy: exact match on incorrect solutions.
- Clean accuracy: answering 0 on correct solutions (synthetic only).
- Error F1: harmonic mean of the two above, as in ProcessBench (synthetic only).
- Within-one accuracy.
- Misconception accuracy (synthetic only), using a fixed text-to-label mapping audited on 100 items.
- Faithfulness: share of feedback sentences that refer to the flagged step. Rule-based extractor; 100 items hand-labelled; agreement reported (≥ 90% needed to pass Gate 2).
- Deference rate (E3): share of responses that adopt the supplied wrong location.

**Statistics:** paired bootstrap (10,000 resamples) and McNemar's test on the same items, with Holm correction within each experiment. Trained models: mean and sd over 3 seeds, and a difference counts as stable only when it exceeds the between-seed sd.

**Baselines:** random (uniform over steps) and position-only (most common first-error step per solution length, fitted on the matching dev split and scored on test).

## 6. Experiments

| Exp. | RQ | Conditions | Data |
|---|---|---|---|
| E1 | RQ1 | Random; position-only; 2 API models; Qwen3.5-2B; Qwen3.5-4B | Test-seen, test-held-out, VtG test |
| E2 | RQ2 | No location vs. checker location given | Synthetic tests |
| E3 | RQ2 | Supplied location: true / one step off / random wrong | Synthetic tests |
| E4 | RQ3 | Base vs. SFT vs. GRPO (3 seeds each); rejection-sampling FT if GRPO fails the 12 Nov gate | Train → synthetic tests |
| E5 | RQ4 | E4 checkpoints | VtG test |
| E6 | RQ4 | E4 checkpoints, asked to explain the flagged step | Synthetic tests and VtG test |

**GRPO reward:** 1.0 for the correct step, or a correct "0" on a clean solution; 0.2 if one step off; 0 otherwise; +0.1 if the output parses. The feedback sentence is never rewarded.

**GRPO go/no-go (12 Nov):** if mean reward has not risen **and** dev accuracy is not above base, switch to rejection-sampling fine-tuning.

**Model fallback:** Qwen3-1.7B if Qwen3.5 does not run efficiently on a T4.

---

## Amendments

_None yet._
