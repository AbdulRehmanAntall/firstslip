# Phase 1 hand check: 50 generated items

Drawn with `random.Random(1)` from all four splits (35 incorrect, 15 clean). For each item, every step was re-derived by hand from the one before it. *Verdict* says whether the hand check agrees with the gold first-error step and misconception.

**Checked:** 15 Oct 2026. Every step of all 50 items was recomputed by hand.

**Result: 50 / 50 agree** (35 incorrect: the error is at the gold step, every step before it is correct, every step after it follows correctly from the wrong line, and the wrong step matches the named misconception; 15 clean: every step is correct).

**Observation:** when a misconception's wrong line is shown without combining terms (M1 on T12/T12m, M16 on T10), the next correct step also combines those terms (items 17, 33). It is still a correct step, but it does two operations at once. This is left as it is and noted in the dataset card.

## 1. `test_heldout-00262` (T6), gold step **3**, M20_S20: Ax = B -> x = B (divides one side only)

- 0: `1 + 5x = 3`
- 1: `5x = 3 - 1`
- 2: `5x = 2`
- 3: `x = 2`  ← injected
- correct answer: `x = 2/5`
- **Verdict:** agrees

## 2. `test_seen-00343` (T12), gold step **0**, clean

- 0: `-2x = 2 - 7(8x - 4)`
- 1: `-2x = 2 - 56x + 28`
- 2: `-2x + 56x = 2 + 28`
- 3: `54x = 2 + 28`
- 4: `54x = 30`
- 5: `x = 5/9`
- correct answer: `x = 5/9`
- **Verdict:** agrees

## 3. `dev-00343` (T12), gold step **3**, M17: A + B -> B - A

- 0: `-9x = 9 - 5(x - 4)`
- 1: `-9x = 9 - 5x + 20`
- 2: `-9x + 5x = 9 + 20`
- 3: `-9x + 5x = 11`  ← injected
- 4: `-4x = 11`
- 5: `x = -11/4`
- correct answer: `x = -29/4`
- **Verdict:** agrees

## 4. `train-00474` (T9), gold step **0**, clean

- 0: `11x = 3(6x - 3)`
- 1: `11x = 18x - 9`
- 2: `11x - 18x = -9`
- 3: `-7x = -9`
- 4: `x = 9/7`
- correct answer: `x = 9/7`
- **Verdict:** agrees

## 5. `train-01483` (T16), gold step **4**, M19: Ax = B -> x = A + B

- 0: `7x = 2x - 7 - 9`
- 1: `7x - 2x = -7 - 9`
- 2: `7x - 2x = -16`
- 3: `5x = -16`
- 4: `x = -11`  ← injected
- correct answer: `x = -16/5`
- **Verdict:** agrees

## 6. `train-06919` (T15), gold step **0**, clean

- 0: `9x - 12x = -12 + 1`
- 1: `9x - 12x = -11`
- 2: `-3x = -11`
- 3: `x = 11/3`
- correct answer: `x = 11/3`
- **Verdict:** agrees

## 7. `test_seen-00263` (T16), gold step **4**, M19: Ax = B -> x = A + B

- 0: `2x = 9x + 4 + 4`
- 1: `2x - 9x = 4 + 4`
- 2: `-7x = 4 + 4`
- 3: `-7x = 8`
- 4: `x = 1`  ← injected
- correct answer: `x = -8/7`
- **Verdict:** agrees

## 8. `dev-00325` (T12), gold step **3**, M14: part1 + part2 -> part1 - part2

- 0: `-2x = 8 + 2(-2x + 9)`
- 1: `-2x = 8 - 4x + 18`
- 2: `-2x + 4x = 8 + 18`
- 3: `-6x = 8 + 18`  ← injected
- 4: `-6x = 26`
- 5: `x = -13/3`
- correct answer: `x = 13`
- **Verdict:** agrees

## 9. `train-00373` (T15), gold step **0**, clean

- 0: `9x - 11x = -4 - 4`
- 1: `9x - 11x = -8`
- 2: `-2x = -8`
- 3: `x = 4`
- correct answer: `x = 4`
- **Verdict:** agrees

## 10. `test_seen-00646` (T14), gold step **4**, M19: Ax = B -> x = A + B

- 0: `x + 8 = -x + 12`
- 1: `x + x = 12 - 8`
- 2: `x + x = 4`
- 3: `2x = 4`
- 4: `x = 6`  ← injected
- correct answer: `x = 2`
- **Verdict:** agrees

## 11. `train-03617` (T12), gold step **0**, clean

- 0: `-3x = -1 + 9(-11x + 1)`
- 1: `-3x = -1 - 99x + 9`
- 2: `-3x + 99x = -1 + 9`
- 3: `96x = -1 + 9`
- 4: `96x = 8`
- 5: `x = 1/12`
- correct answer: `x = 1/12`
- **Verdict:** agrees

## 12. `train-06639` (T12), gold step **3**, M15: part1 - part2 -> part1 + part2

- 0: `-2x = 4 + 2(6x - 5)`
- 1: `-2x = 4 + 12x - 10`
- 2: `-2x - 12x = 4 - 10`
- 3: `10x = 4 - 10`  ← injected
- 4: `10x = -6`
- 5: `x = -3/5`
- correct answer: `x = 3/7`
- **Verdict:** agrees

## 13. `train-05402` (T10), gold step **3**, M21: Ax = B -> x = A - B

- 0: `-2x = -4 + 10*5`
- 1: `-2x = -4 + 50`
- 2: `-2x = 46`
- 3: `x = -48`  ← injected
- correct answer: `x = -23`
- **Verdict:** agrees

## 14. `train-04917` (T10), gold step **1**, M3: A ± B(part) -> (A ± B)(part)

- 0: `4x = 4 + 7*12`
- 1: `4x = 11*12`  ← injected
- 2: `4x = 132`
- 3: `x = 33`
- correct answer: `x = 22`
- **Verdict:** agrees

## 15. `test_heldout-00819` (T12), gold step **1**, M6: -A(Bx - C) -> -ABx - AC

- 0: `-12x = -8 - 8(-9x - 7)`
- 1: `-12x = -8 + 72x - 56`  ← injected
- 2: `-12x - 72x = -8 - 56`
- 3: `-12x - 72x = -64`
- 4: `-84x = -64`
- 5: `x = 16/21`
- correct answer: `x = -4/7`
- **Verdict:** agrees

## 16. `test_seen-00767` (T10), gold step **3**, M21: Ax = B -> x = A - B

- 0: `3x = -5 + 2*11`
- 1: `3x = -5 + 22`
- 2: `3x = 17`
- 3: `x = -14`  ← injected
- correct answer: `x = 17/3`
- **Verdict:** agrees

## 17. `train-05321` (T12), gold step **2**, M1: A(part) -> A + (part)

- 0: `-12x = -12 - 12(2x - 11)`
- 1: `-12x + 12 = -12(2x - 11)`
- 2: `-12x + 12 = -12 + 2x - 11`  ← injected
- 3: `-12x - 2x = -23 - 12`
- 4: `-14x = -23 - 12`
- 5: `-14x = -35`
- 6: `x = 5/2`
- correct answer: `x = 10`
- **Verdict:** agrees. Step 3 is correct but does two things at once: it combines −12 − 11 = −23 and moves the terms, because the M1 line is shown uncombined and the next state is the combined one.

## 18. `train-00505` (T12), gold step **0**, clean

- 0: `-4x = -10 + 10(-x - 5)`
- 1: `-4x = -10 - 10x - 50`
- 2: `-4x + 10x = -10 - 50`
- 3: `6x = -10 - 50`
- 4: `6x = -60`
- 5: `x = -10`
- correct answer: `x = -10`
- **Verdict:** agrees

## 19. `train-00703` (T8), gold step **1**, M4: A(B·C) -> AB·AC

- 0: `3x = 10(3*9)`
- 1: `3x = 30*90`  ← injected
- 2: `3x = 2700`
- 3: `x = 900`
- correct answer: `x = 90`
- **Verdict:** agrees

## 20. `train-04147` (T9), gold step **2**, M13: Ax ± B -> (A ± B)

- 0: `10x = -4(-2x - 9)`
- 1: `10x = 8x + 36`
- 2: `10x = 44`  ← injected
- 3: `x = 22/5`
- correct answer: `x = 18`
- **Verdict:** agrees

## 21. `dev-00379` (T15), gold step **3**, M19: Ax = B -> x = A + B

- 0: `-7x + 3x = -6 + 7`
- 1: `-4x = -6 + 7`
- 2: `-4x = 1`
- 3: `x = -3`  ← injected
- correct answer: `x = -1/4`
- **Verdict:** agrees

## 22. `train-00408` (T12), gold step **0**, clean

- 0: `-12x = -8 + 4(2x + 9)`
- 1: `-12x + 8 = 4(2x + 9)`
- 2: `-12x + 8 = 8x + 36`
- 3: `-12x - 8x = 36 - 8`
- 4: `-20x = 36 - 8`
- 5: `-20x = 28`
- 6: `x = -7/5`
- correct answer: `x = -7/5`
- **Verdict:** agrees

## 23. `train-06453` (T12), gold step **5**, M17: A + B -> B - A

- 0: `6x = 2 + 2(9x + 9)`
- 1: `6x - 2 = 2(9x + 9)`
- 2: `6x - 2 = 18x + 18`
- 3: `6x - 18x = 18 + 2`
- 4: `-12x = 18 + 2`
- 5: `-12x = -16`  ← injected
- 6: `x = 4/3`
- correct answer: `x = -5/3`
- **Verdict:** agrees

## 24. `train-00137` (T12), gold step **0**, clean

- 0: `-10x = 12 - 4(6x + 5)`
- 1: `-10x - 12 = -4(6x + 5)`
- 2: `-10x - 12 = -24x - 20`
- 3: `-10x + 24x = -20 + 12`
- 4: `-10x + 24x = -8`
- 5: `14x = -8`
- 6: `x = -4/7`
- correct answer: `x = -4/7`
- **Verdict:** agrees

## 25. `train-04874` (T8), gold step **1**, M4: A(B·C) -> AB·AC

- 0: `7x = -7(-3*(-9))`
- 1: `7x = 21*63`  ← injected
- 2: `7x = 1323`
- 3: `x = 189`
- correct answer: `x = -27`
- **Verdict:** agrees

## 26. `test_seen-00257` (T10), gold step **3**, M21: Ax = B -> x = A - B

- 0: `7x = -2 - 7*(-12)`
- 1: `7x = -2 + 84`
- 2: `7x = 82`
- 3: `x = -75`  ← injected
- correct answer: `x = 82/7`
- **Verdict:** agrees

## 27. `train-01040` (T16), gold step **4**, M21: Ax = B -> x = A - B

- 0: `-10x = -12x - 6 - 9`
- 1: `-10x + 12x = -6 - 9`
- 2: `-10x + 12x = -15`
- 3: `2x = -15`
- 4: `x = 17`  ← injected
- correct answer: `x = -15/2`
- **Verdict:** agrees

## 28. `train-02298` (T10), gold step **2**, M17: A + B -> B - A

- 0: `-3x = 10 + 12*11`
- 1: `-3x = 10 + 132`
- 2: `-3x = 122`  ← injected
- 3: `x = -122/3`
- correct answer: `x = -142/3`
- **Verdict:** agrees

## 29. `train-05198` (T12), gold step **0**, clean

- 0: `4x = -8 - 8(4x + 10)`
- 1: `4x + 8 = -8(4x + 10)`
- 2: `4x + 8 = -32x - 80`
- 3: `4x + 32x = -80 - 8`
- 4: `36x = -80 - 8`
- 5: `36x = -88`
- 6: `x = -22/9`
- correct answer: `x = -22/9`
- **Verdict:** agrees

## 30. `train-07886` (T9), gold step **1**, M5: A(Bx ± C) -> A(ABx ± AC)

- 0: `12x = 8(2x - 3)`
- 1: `12x = 8(16x - 24)`  ← injected
- 2: `12x = 128x - 192`
- 3: `12x - 128x = -192`
- 4: `-116x = -192`
- 5: `x = 48/29`
- correct answer: `x = 6`
- **Verdict:** agrees

## 31. `dev-00307` (T9), gold step **1**, M8: A(Bx ± C) -> Bx ± AC

- 0: `-5x = 8(2x - 9)`
- 1: `-5x = 2x - 72`  ← injected
- 2: `-5x - 2x = -72`
- 3: `-7x = -72`
- 4: `x = 72/7`
- correct answer: `x = 24/7`
- **Verdict:** agrees

## 32. `train-07109` (T12), gold step **6**, M19: Ax = B -> x = A + B

- 0: `2x = 6 + 6(2x - 6)`
- 1: `2x - 6 = 6(2x - 6)`
- 2: `2x - 6 = 12x - 36`
- 3: `2x - 12x = -36 + 6`
- 4: `2x - 12x = -30`
- 5: `-10x = -30`
- 6: `x = -40`  ← injected
- correct answer: `x = 3`
- **Verdict:** agrees

## 33. `train-07604` (T12), gold step **2**, M1: A(part) -> A + (part)

- 0: `11x = 2 - 12(-x + 11)`
- 1: `11x - 2 = -12(-x + 11)`
- 2: `11x - 2 = -12 - x + 11`  ← injected
- 3: `11x + x = -1 + 2`
- 4: `11x + x = 1`
- 5: `12x = 1`
- 6: `x = 1/12`
- correct answer: `x = 130`
- **Verdict:** agrees. Same pattern as item 17: step 3 combines −12 + 11 = −1 while moving terms (correct, but two operations in one line).

## 34. `train-02509` (T10), gold step **3**, M22_S1: Ax = B -> x = A / B

- 0: `5x = 8 - 6*5`
- 1: `5x = 8 - 30`
- 2: `5x = -22`
- 3: `x = -5/22`  ← injected
- correct answer: `x = -22/5`
- **Verdict:** agrees

## 35. `train-04263` (T9), gold step **2**, M13: Ax ± B -> (A ± B)

- 0: `4x = -12(2x - 2)`
- 1: `4x = -24x + 24`
- 2: `4x = 0`  ← injected
- 3: `x = 0`
- correct answer: `x = 6/7`
- **Verdict:** agrees. M13 here gives `4x = 0`, so the wrong answer is 0; correct is 6/7.

## 36. `train-01303` (T11), gold step **3**, M17: A + B -> B - A

- 0: `-11 + 11x - x = -11`
- 1: `-11 + 10x = -11`
- 2: `10x = -11 + 11`
- 3: `10x = 22`  ← injected
- 4: `x = 11/5`
- correct answer: `x = 0`
- **Verdict:** agrees

## 37. `train-06247` (T14), gold step **0**, clean

- 0: `4x - 5 = 8x + 10`
- 1: `4x - 8x = 10 + 5`
- 2: `4x - 8x = 15`
- 3: `-4x = 15`
- 4: `x = -15/4`
- correct answer: `x = -15/4`
- **Verdict:** agrees

## 38. `train-05159` (T9), gold step **1**, M8: A(Bx ± C) -> Bx ± AC

- 0: `-3x = -3(8x - 5)`
- 1: `-3x = 8x + 15`  ← injected
- 2: `-3x - 8x = 15`
- 3: `-11x = 15`
- 4: `x = -15/11`
- correct answer: `x = 5/7`
- **Verdict:** agrees

## 39. `train-02792` (T8), gold step **2**, M16: part1 · part2 -> part1 + part2

- 0: `6x = -9(-9*(-4))`
- 1: `6x = -9*36`
- 2: `6x = -9 + 36`  ← injected
- 3: `6x = 27`
- 4: `x = 9/2`
- correct answer: `x = -54`
- **Verdict:** agrees

## 40. `dev-00119` (T12), gold step **0**, clean

- 0: `-5x = 9 - 3(10x - 7)`
- 1: `-5x = 9 - 30x + 21`
- 2: `-5x + 30x = 9 + 21`
- 3: `25x = 9 + 21`
- 4: `25x = 30`
- 5: `x = 6/5`
- correct answer: `x = 6/5`
- **Verdict:** agrees

## 41. `train-00025` (T14), gold step **4**, M22_S1: Ax = B -> x = A / B

- 0: `8x - 2 = 6x - 11`
- 1: `8x - 6x = -11 + 2`
- 2: `2x = -11 + 2`
- 3: `2x = -9`
- 4: `x = -2/9`  ← injected
- correct answer: `x = -9/2`
- **Verdict:** agrees

## 42. `train-06211` (T12), gold step **4**, M14: part1 + part2 -> part1 - part2

- 0: `10x = 11 - 4(-10x + 4)`
- 1: `10x - 11 = -4(-10x + 4)`
- 2: `10x - 11 = 40x - 16`
- 3: `10x - 40x = -16 + 11`
- 4: `10x - 40x = -27`  ← injected
- 5: `-30x = -27`
- 6: `x = 9/10`
- correct answer: `x = 1/6`
- **Verdict:** agrees

## 43. `train-00309` (T9), gold step **2**, M12_S15: Ax ± B -> (A ± B)x

- 0: `-12x = 8(x + 9)`
- 1: `-12x = 8x + 72`
- 2: `-12x = 80x`  ← injected
- 3: `-12x - 80x = 0`
- 4: `-92x = 0`
- 5: `x = 0`
- correct answer: `x = -18/5`
- **Verdict:** agrees

## 44. `train-02913` (T5), gold step **3**, M19: Ax = B -> x = A + B

- 0: `-7x + 3 = -1`
- 1: `-7x = -1 - 3`
- 2: `-7x = -4`
- 3: `x = -11`  ← injected
- correct answer: `x = 4/7`
- **Verdict:** agrees

## 45. `test_seen-00142` (T14), gold step **0**, clean

- 0: `-3x - 10 = 4x + 7`
- 1: `-3x - 4x = 7 + 10`
- 2: `-3x - 4x = 17`
- 3: `-7x = 17`
- 4: `x = -17/7`
- correct answer: `x = -17/7`
- **Verdict:** agrees

## 46. `train-03541` (T5), gold step **0**, clean

- 0: `6x + 7 = -2`
- 1: `6x = -2 - 7`
- 2: `6x = -9`
- 3: `x = -3/2`
- correct answer: `x = -3/2`
- **Verdict:** agrees

## 47. `train-07191` (T11), gold step **0**, clean

- 0: `-7 + 12x + 3x = -7`
- 1: `-7 + 15x = -7`
- 2: `15x = -7 + 7`
- 3: `15x = 0`
- 4: `x = 0`
- correct answer: `x = 0`
- **Verdict:** agrees. Clean, with answer 0.

## 48. `train-04736` (T9), gold step **1**, M5: A(Bx ± C) -> A(ABx ± AC)

- 0: `-8x = 4(12x - 7)`
- 1: `-8x = 4(48x - 28)`  ← injected
- 2: `-8x = 192x - 112`
- 3: `-8x - 192x = -112`
- 4: `-200x = -112`
- 5: `x = 14/25`
- correct answer: `x = 1/2`
- **Verdict:** agrees

## 49. `test_seen-00116` (T9), gold step **1**, M5: A(Bx ± C) -> A(ABx ± AC)

- 0: `-6x = 8(3x + 6)`
- 1: `-6x = 8(24x + 48)`  ← injected
- 2: `-6x = 192x + 384`
- 3: `-6x - 192x = 384`
- 4: `-198x = 384`
- 5: `x = -64/33`
- correct answer: `x = -8/5`
- **Verdict:** agrees

## 50. `train-01660` (T8), gold step **0**, clean

- 0: `-3x = 5(7*(-5))`
- 1: `-3x = 5*(-35)`
- 2: `-3x = -175`
- 3: `x = 175/3`
- correct answer: `x = 175/3`
- **Verdict:** agrees
