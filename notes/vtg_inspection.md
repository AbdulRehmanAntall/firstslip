# VtG hand inspection (Phase 0)

30 rows sampled from **VtG dev** (`random.Random(30)`; ids in `vtg_inspection_ids.json`). Only dev rows were read, so the 802 test rows stay unseen.

## Dataset facts (all 1,002 rows)

| Fact | Value |
|---|---|
| Rows | 1,002, all `Math Word Problem` (GSM8K-style), all incorrect (no clean solutions) |
| Steps per solution | 3–15 (median 5; mean 5.9) |
| First-error index | 0-based in the dataset; FirstSlip uses 1-based (`first_error = incorrect_index + 1`, 0 = no error) |
| Last list element | Always the bare final answer (e.g. `" 4"`), not a reasoning step; 16 rows mark it as the first error |
| Error categories | Misunderstanding of a question 287 · Extra/Missing quantity 240 · Missing/Wrong factual knowledge 140 · Calculation error 128 · None of the above 87 (8.7%) · Reached correct solution but proceeded further 70 · Unit conversion 50 |
| Missing teacher description | 295 rows (29%) |
| Repeated problems | 390 rows share their problem text with another row |
| Unique solutions | **612**. 235 solutions are annotated more than once (625 rows) |
| Label agreement on repeats | **60%** pairwise agreement on the first-error step (408 / 679 pairs); 111 of the 235 repeated solutions have conflicting labels |

The agreement figure comes from a one-off check during Phase 0. It was not saved as a script yet; rerun it in Phase 2 when VtG evaluation code is written.

## Observations from the 30 rows

1. **Identical solutions with different gold steps.** ids 531 and 542 (same solution, labelled step 1 vs step 2); ids 86 and 323 (step 1 vs step 3); id 768 is the same solution as row 0. VtG first-error labels are noisy, and the same solution can count as both right and wrong for a model depending on which annotator's row is scored.
2. **Debatable labels.** id 690 marks step 2 (`2 × 500 = 1000`, which looks correct; the slip is step 3/4). id 688 marks step 2, but the missed quantity (black balloons) is already in step 1. id 112 marks the final sum instead of the double-counted hours in step 2. id 52 marks a step that is arguably fine on its own.
3. **Errors are mostly comprehension, not algebra.** Most errors misread the question (wrong quantity, extra or missing term, wrong fact), not algebraic slips. This supports H4's prediction that transfer from synthetic algebra will be small.
4. **Filler steps.** Some steps are connective text (`"Simplifying, we get:"`, id 23), so step counts include non-mathematical lines.
5. **Teacher descriptions are uneven.** They range from precise ("Student computes charges for a full hour…") to unhelpful ("Distance", "Incorrect answer", missing).
6. **Ambiguous problems.** id 805 ("twice as young") has no clear correct reading.

## Consequences for the design (carried into PREREGISTRATION.md)

- Split dev/test **by problem text** so no problem or duplicate solution appears in both (verified: 0 shared problems).
- Report VtG per row (as planned) **and** a lenient score that accepts any teacher's label for that solution, with the 60% inter-annotator agreement as a reference ceiling.
- Keep the final-answer element as a step (the 18.3% random baseline from Srivatsa et al. is reproduced only when it is counted: we get 18.2%).
- No clean-solution accuracy or error F1 on VtG, because every row is incorrect.
