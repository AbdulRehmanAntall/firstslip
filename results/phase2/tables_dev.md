# Phase 2 tables

95% bootstrap CIs in brackets. n = items scored.

## E1 — prompted localization

### dev

| Model | n | First-error acc. | Clean acc. | Error F1 | Within-one | Misconception (label) | Family | Unfaithful | Parse |
|---|---|---|---|---|---|---|---|---|---|
| qwen-27b | 500 | 95.7 (93.6–97.6) | 46.4 (37.6–55.2) | 62.5 | 96.8 (94.9–98.4) | 8.5 (5.9–11.5) | 12.0 (8.8–15.5) | 11.8 (8.8–14.7) | 100.0 (100.0–100.0) |
| qwen-2b | 500 | 33.1 (28.5–37.9) | 0.0 (0.0–0.0) | 0.0 | 53.9 (48.8–58.9) | 2.4 (1.1–4.0) | 15.5 (12.0–19.2) | 9.4 (7.0–12.0) | 100.0 (100.0–100.0) |
| qwen-4b | 500 | 67.5 (62.7–72.3) | 29.6 (21.6–37.6) | 41.1 | 76.3 (72.0–80.5) | 2.4 (1.1–4.0) | 14.4 (10.9–18.1) | 12.8 (9.8–15.9) | 100.0 (100.0–100.0) |

### vtg_dev

| Model | n | First-error acc. | Clean acc. | Error F1 | Within-one | Misconception (label) | Family | Unfaithful | Parse |
|---|---|---|---|---|---|---|---|---|---|
| qwen-27b | 200 | 65.0 (58.5–71.5) | — | — | 84.5 (79.5–89.5) | — | — | 5.2 (2.1–8.8) | 100.0 (100.0–100.0) |
| qwen-2b | 200 | 34.0 (27.5–40.5) | — | — | 59.5 (53.0–66.0) | — | — | 9.1 (5.1–13.6) | 100.0 (100.0–100.0) |
| qwen-4b | 200 | 51.0 (44.5–58.0) | — | — | 75.0 (69.0–81.0) | — | — | 1.6 (0.0–3.8) | 100.0 (100.0–100.0) |

| Model | Without NOTA | Lenient (any teacher label) |
|---|---|---|
| qwen-27b | 64.9 (58.1–71.7) | 77.5 (71.5–83.0) |
| qwen-2b | 33.5 (27.2–40.3) | 40.5 (34.0–47.5) |
| qwen-4b | 50.8 (44.0–57.6) | 62.0 (55.0–69.0) |

Model vs model (first-error acc., McNemar, Holm within E1):

| Split | A | B | n | A − B | p (Holm) |
|---|---|---|---|---|---|
| dev | qwen-27b | qwen-2b | 375 | +62.7 (+57.6–+67.5) | 2.17e-70 |
| dev | qwen-27b | qwen-4b | 375 | +28.3 (+23.5–+33.1) | 3.76e-29 |
| dev | qwen-2b | qwen-4b | 375 | -34.4 (-39.2–-29.6) | 1.47e-38 |
| vtg_dev | qwen-27b | qwen-2b | 200 | +31.0 (+23.5–+38.5) | 1.93e-13 |
| vtg_dev | qwen-27b | qwen-4b | 200 | +14.0 (+8.0–+20.0) | 2.54e-05 |
| vtg_dev | qwen-2b | qwen-4b | 200 | -17.0 (-23.5–-10.5) | 2.33e-06 |

## H1 — localization vs solving (same equations, incorrect items)

| Model | Localization | Solving | Loc − solve | p |
|---|---|---|---|---|
| qwen-27b | 95.7 (93.6–97.6) | 52.0 (46.9–57.1) | +43.7 (+38.4–+49.1) | 1.08e-43 |
| qwen-2b | 33.1 (28.5–37.9) | 6.4 (4.0–9.1) | +26.7 (+21.1–+32.3) | 1.42e-18 |
| qwen-4b | 67.5 (62.7–72.3) | 7.7 (5.1–10.4) | +59.7 (+54.4–+64.8) | 2.35e-63 |

## E2 — checker location given vs not given (misconception acc.)

| Split | Model | n | Given − none | p (Holm) | Given: first-error acc. |
|---|---|---|---|---|---|
| dev | qwen-27b | 375 | -1.6 (-3.7–+0.5) | 0.63 | 91.5 (88.5–94.1) |
| dev | qwen-2b | 375 | +0.5 (-1.3–+2.4) | 1 | 100.0 (100.0–100.0) |
| dev | qwen-4b | 375 | +0.0 (-1.9–+1.9) | 1 | 60.3 (55.5–65.3) |

## E3 — corrupted tool

| Split | Model | Acc. (true loc.) | Deference (one-off) | Deference (random wrong) | Acc. (one-off) | Acc. (random wrong) |
|---|---|---|---|---|---|---|
| dev | qwen-27b | 91.5 (88.5–94.1) | 1.6 (0.5–2.9) | 3.2 (1.6–5.1) | 89.3 (86.1–92.3) | 81.6 (77.6–85.6) |
| dev | qwen-2b | 100.0 (100.0–100.0) | 100.0 (100.0–100.0) | 99.7 (99.2–100.0) | 0.0 (0.0–0.0) | 0.3 (0.0–0.8) |
| dev | qwen-4b | 60.3 (55.5–65.3) | 9.6 (6.7–12.8) | 18.4 (14.7–22.4) | 57.1 (52.0–62.1) | 51.7 (46.7–56.8) |

## Judge — faithfulness (E1, Amendment 5)

| Split | Model | n | Faithful | Unfaithful | Unspecified | Parse |
|---|---|---|---|---|---|---|
| dev | qwen-27b | 441 | 94.6 (92.3–96.6) | 1.6 (0.5–2.7) | 3.9 | 100.0 |
| dev | qwen-2b | 500 | 65.2 (60.8–69.4) | 25.8 (22.0–29.8) | 9.0 | 100.0 |
| dev | qwen-4b | 447 | 86.1 (82.8–89.3) | 11.2 (8.3–14.1) | 2.7 | 100.0 |
| vtg_dev | qwen-27b | 193 | 95.9 (92.7–98.4) | 4.1 (1.6–7.3) | 0.0 | 100.0 |
| vtg_dev | qwen-2b | 176 | 83.0 (77.3–88.1) | 13.1 (8.5–18.2) | 4.0 | 100.0 |
| vtg_dev | qwen-4b | 183 | 82.5 (77.0–88.0) | 16.9 (11.5–22.4) | 0.5 | 100.0 |

## Judge — correct diagnosis (E1 no location vs E2 location given, Amendment 5)

| Split | Model | None | Given | Given − none | p (Holm) |
|---|---|---|---|---|---|
| dev | qwen-27b | 49.9 (44.8–54.9) | 44.5 (39.5–49.6) | -5.3 (-9.3–-1.3) | 0.027 |
| dev | qwen-2b | 7.5 (4.8–10.1) | 14.4 (10.9–18.1) | +6.9 (+3.7–+10.4) | 0.000318 |
| dev | qwen-4b | 19.7 (15.7–23.7) | 19.7 (15.7–23.7) | +0.0 (-2.9–+2.9) | 1 |
