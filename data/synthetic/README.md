# FirstSlip synthetic algebra benchmark: dataset card

Linear equations in one variable, solved step by step, where each incorrect solution contains **exactly one injected misconception** at a known step. Built in Phase 1 by `scripts/generate_synthetic.py` (seed `20261019`, code commit `2c10d15`). The `.jsonl` files are not committed. The same command regenerates them byte for byte, and `manifest.json` holds their SHA-256 hashes.

## Splits

| Split | Misconceptions | Items | Incorrect | Clean | Use |
|---|---|---|---|---|---|
| `train` | 15 seen | 8,000 | 6,000 | 2,000 | SFT and GRPO |
| `dev` | 15 seen | 500 | 375 | 125 | Prompt tuning, early stopping, GRPO go/no-go, position-prior fit |
| `test_seen` | 15 seen | 1,000 | 750 | 250 | In-domain results |
| `test_heldout` | 4 held-out | 1,000 | 750 | 250 | Checking vs. pattern recognition |

Every problem equation appears once across all four splits. Clean items in `test_heldout` are new equations with no misconception.

## Record format

```json
{"id": "dev-00343", "split": "dev", "start_type": "T12", "coefficients": [-9, 9, -5, 1, -4],
 "problem": "-9x = 9 - 5(x - 4)",
 "steps": ["-9x = 9 - 5x + 20", "-9x + 5x = 9 + 20", "-9x + 5x = 11", "-4x = 11", "x = -11/4"],
 "n_steps": 5, "first_error": 3, "misconception": "M17", "family": "sign", "rule": "A + B -> B - A",
 "answer": "x = -29/4", "path": ["T12", "T12d", "T15", "T4", "T1", "X"]}
```

- `first_error` is 1-based, and `0` means a clean solution, the same convention as VtG in `core/vtg.py`. The problem is step 0 and is not counted.
- `answer` is the correct solution. The last step holds the student's answer.
- `path` lists the state type after each step (see below).
- Steps are plain text: implicit multiplication (`3x`, `2(x + 1)`), `*` for products, and negative factors in parentheses (`3*(-4)`).

## How items are built

**Source.** MalAlgoPy (Sonkar et al., 2024) has no public code, so the generator was rebuilt from scratch from the paper's Table 1 (misconceptions) and Figure 1 (equation forms).

**States and steps.** A state is an equation type plus integer coefficients. A *correct reduction* maps a state to the next state in one step. A *misconception* maps it to a wrong state. After the wrong step, the solution continues with correct reductions from the wrong state, so the injected step is the only error. Each state's solution is computed exactly with `Fraction`, so the labels never depend on the SymPy checker.

**Equation types.** Sonkar et al.'s 15 forms (T13 is absent from their Figure 1), plus two intermediate states (marked ✚):

| Type | Form | Correct next step |
|---|---|---|
| T1 | Ax = B | x = B/A |
| T2 | Ax = B + C | T1 |
| T3 | Ax = B·C | T1 |
| T4 | Ax + Bx = C | T1 |
| T5 | Ax + B = C | T2 (move B) |
| T6 | A + Bx = C | T2 (move A) |
| T7 | Ax = Bx + C | T4 (move Bx) |
| T8 | Ax = B(C·D) | T3 (multiply inside) |
| T9 | Ax = B(Cx + D) | T7 (distribute) |
| T10 | Ax = B + C·D | T2 (multiply) |
| T11 | A + Bx + Cx = D | T6 (combine x terms) |
| T12 | Ax = B + C(Dx + E) | T12d (distribute) **or** T12m (move B) |
| ✚ T12d | Ax = B + Cx + D | T15 (move Cx) |
| ✚ T12m | Ax + B = C(Dx + E) | T14 (distribute) |
| T14 | Ax + B = Cx + D | T15 (move Cx and B) |
| T15 | Ax + Bx = C + D | T2 (combine x) **or** T4 (combine constants) |
| T16 | Ax = Bx + C + D | T15 (move Bx) |

Start types are T5–T12 and T14–T16, because T1–T4 are solved in fewer than 3 steps. Correct solutions run 3 steps (T5, T6, T7, T8, T10, T15), 4 steps (T9, T11, T14, T16), or 5–6 steps (T12, by its two routes). T12m was added so that 6-step solutions exist, and so that the distribution and M11 misconceptions can occur at steps 2 and 3, not only at step 1.

**Misconceptions.** These are the 19 rows of Sonkar et al. (2024), Table 1. The split and family assignment are fixed in `PREREGISTRATION.md` §2.

| ID | Rule | Applied to here | Split |
|---|---|---|---|
| M1 | A(part) → A + (part) | T8, T9, T12, T12m | seen |
| M2_S3 | A(Bx ± C) → ABx ± C | T9, T12, T12m | **held-out** |
| M3 | A ± B(part) → (A ± B)(part) | T10, T12 | seen |
| M4 | A(B·C) → AB·AC | T8 | seen |
| M5 | A(Bx ± C) → A(ABx ± AC) | T9, T12, T12m | seen |
| M6 | −A(Bx − C) → −ABx − AC | T9, T12, T12m (negative factor and minus inside only) | **held-out** |
| M8 | A(Bx ± C) → Bx ± AC | T9, T12, T12m | seen |
| M11 | Ax ± B = Cx ± D → Ax + Cx = B + D | T14 | **held-out** |
| M12_S15 | Ax ± B → (A ± B)x | T5, T6, T7 | seen |
| M13 | Ax ± B → (A ± B) | T7 | seen |
| M14 | part1 + part2 → part1 − part2 | T2, T4, T11, T15 (any "+" pair) | seen |
| M15 | part1 − part2 → part1 + part2 | T2, T4, T11, T15 (any "−" pair) | seen |
| M16 | part1 · part2 → part1 + part2 | T3, T10 | seen |
| M17 | A + B → B − A | T2, T4, T11, T15 | seen |
| M18 | A − B → B − A | T2, T4, T11, T15 | seen |
| M19 | Ax = B → x = A + B | T1 | seen |
| M20_S20 | Ax = B → x = B | T1 | **held-out** |
| M21 | Ax = B → x = A − B | T1 | seen |
| M22_S1 | Ax = B → x = A / B | T1 | seen |

The "applied to" column differs from Table 1's type lists in four places:

- **M13** is applied only to T7 (`Ax = Bx + C → Ax = B + C`). On T5 and T6 it would delete the only x term and leave nothing to solve.
- **M12_S15 and M13** are not applied to T9 or T12 directly. They reach those problems through the T7 state that T9 becomes after distributing.
- **The pair rules (M14, M15, M17, M18)** also apply to the "+"/"−" pairs inside T11 and T15. Table 1 lists only T2 and T4.
- **M12_S15 and M13 now produce different steps.** Table 1 gives them the same description. Here M12_S15 keeps the x, giving (A ± B)x, and M13 drops it, giving (A ± B).

## Generator rules and how they are enforced

1. **One error per item.** The wrong step changes the exact solution, and every later step is a correct reduction from it. The SymPy checker confirms this independently (see *Validation*).
2. **No accidental recovery.** No step from the error onwards may have the correct solution. Such candidates are rejected and counted. None occurred, because a correct continuation cannot change the solution set back. The check stays in place in both the generator and the gate.
3. **Balanced positions.** A pilot run finds which (solution length, first-error step) cells each split's misconceptions can reach. Generation then fills the emptiest cell first, using the least-used misconception that can land there. The seen splits use length shares of 30 / 30 / 25 / 15% for 3 / 4 / 5 / 6 steps, with a uniform position within each length. The one exception is the (6, 3) cell, which no seen misconception reaches. Clean items follow the incorrect items' length distribution.
4. **Deduplication.** Each problem's canonical form is its unevaluated SymPy tree (`srepr` of each side, `evaluate=False`). A problem is used at most once across all splits.
5. **Ranges.** Coefficients are integers in [−12, 12] without 0. Multiplicative factors have |factor| ≥ 2. The correct answer is an integer or a fraction with denominator ≤ 12. Solutions have 3–6 steps. Lines that would repeat the previous line, show a 0·x term or a 0(…) factor, or have no unique solution are rejected.

### Rejected candidates (counted during generation)

| Reason | train | dev | test_seen | test_heldout |
|---|---|---|---|---|
| Answer not an integer or simple fraction | 16,466 | 979 | 2,196 | 3,121 |
| Sampled problem cannot reach the target cell | 3,978 | 243 | 559 | 787 |
| Injection too long or short (outside 3–6 steps) | 346 | 34 | 40 | 0 |
| Degenerate line (0·x, repeated line, …) | 284 | 15 | 33 | 4 |
| Degenerate correct chain | 343 | 21 | 47 | 36 |
| Wrong step does not change the solution | 160 | 17 | 23 | 17 |
| Duplicate equation | 34 | 3 | 6 | 5 |
| **Accidental recovery** | **0** | **0** | **0** | **0** |

These count rejected *candidates* (a sampled problem or one possible injection), not finished items.

## Distributions

**Misconceptions (incorrect items).** In train, each distribution rule has 341–342 items, M12_S15–M18 have 394–395 each, and M19/M21/M22_S1 have 510 each. Test-seen has 42–64 per misconception. Test-held-out has M2_S3 125, M6 125, M11 125 and M20_S20 375. M20_S20 is the only held-out rule that can occur at the last step, so it fills half the cells.

**Lengths.** Seen splits are 30 / 30 / 25 / 15% at 3 / 4 / 5 / 6 steps. Test-held-out (incorrect) has 94 / 187 / 187 / 282 items at 3 / 4 / 5 / 6 steps.

**Start types.** T12 is the only type with 5- and 6-step solutions, so it is the most common start type: 34% of train and 63% of test-held-out.

**First-error position.** Seen splits are uniform within each length, except that (6, 3) is empty. Test-held-out can only reach 8 cells: (3,3), (4,1), (4,4), (5,1), (5,5), (6,2), (6,3), (6,6). Each holds 1/8 of the items.

## Baselines (first-error accuracy on incorrect items)

From `scripts/synthetic_baselines.py` (`results/phase1/synthetic_baselines.json`). The position-only rule is fitted on synthetic dev: 3→1, 4→1, 5→1, 6→2.

| Split | Random (expected) | Position-only (fit on dev) | 95% CI | Best possible position-only rule |
|---|---|---|---|---|
| test_seen | 24.9% | **25.3%** | 22.3–28.4 | 25.6% |
| test_heldout | 21.7% | **37.5%** | 34.0–40.9 | 50.1% |

On test-seen, a position guess is no better than random, as intended. On test-held-out, position alone scores 37.5%: the held-out misconceptions can only occur at step 1, at the last step, or at steps 2–3 of T12m. Any held-out result in Phase 4 must be compared with this number, not with random.

## Validation

- **Gate 1** (`scripts/phase1_gate.py`, `results/phase1/gate.json`): on 2,000 items (1,500 incorrect, 500 clean, drawn from all splits), the SymPy checker, which reads only the rendered text, returns the injected step on **100%** of incorrect items and 0 on **100%** of clean items. It does the same on **all 10,500 items**. It found no unreadable lines and no recoveries.
- **Hand check:** 50 items (35 incorrect, 15 clean) were recomputed by hand, and all 50 agree (`notes/phase1_hand_check.md`).
- **Tests:** `pytest` covers the checker, the rendering, Table 1 examples, and every misconception's injections against the checker.

## Known limitations

- **Forms are templated.** Each type always prints its terms in the same order, so every problem of a given type has the same surface shape.
- **Compressed correct steps.** When a wrong step is printed uncombined (M1 on T12/T12m, M16 on T10), the next correct step also combines those terms, which is two operations in one line.
- **Wrong answers are unrestricted.** Wrong final answers may be awkward fractions (e.g. `x = 48/29`). Only the correct answer is limited to simple fractions.
- **Uneven start types.** Start types are not balanced: T12 dominates long solutions. The two T15 routes (combine x first or constants first) are chosen at random.
- **Not real student work.** These are synthetic solutions from a rule-based generator. They are not student work and say nothing about how often real students make each error.

## Licence and sources

Code and data: same licence as this repository. Misconception taxonomy: Sonkar et al. (2024), *LLM-based Cognitive Models of Students with Misconceptions* (arXiv:2410.12294), which builds on Payne & Squibb (1990).
