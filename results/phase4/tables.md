# Phase 4 (E4): Base vs. SFT vs. GRPO

Mean ± sd over seeds (Base is greedy and has one run). Percentages.

## dev

| Condition | Seeds | First-error | Clean | Error F1 | Within-one |
|---|---|---|---|---|---|
| Base | 1 | 33.1 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 53.9 ± 0.0 |
| SFT | 3 | 99.0 ± 0.7 | 99.2 ± 0.8 | 99.1 ± 0.7 | 99.3 ± 0.6 |
| GRPO | 3 | 83.5 ± 2.5 | 71.7 ± 12.9 | 76.8 ± 8.2 | 87.6 ± 0.9 |

## test_seen

| Condition | Seeds | First-error | Clean | Error F1 | Within-one |
|---|---|---|---|---|---|
| Base | 1 | 34.8 ± 0.0 | 0.4 ± 0.0 | 0.8 ± 0.0 | 55.2 ± 0.0 |
| SFT | 3 | 99.6 ± 0.3 | 99.5 ± 0.6 | 99.5 ± 0.3 | 99.6 ± 0.3 |
| GRPO | 3 | 84.6 ± 3.1 | 73.5 ± 15.4 | 78.2 ± 9.7 | 88.3 ± 1.2 |

## test_heldout

| Condition | Seeds | First-error | Clean | Error F1 | Within-one |
|---|---|---|---|---|---|
| Base | 1 | 26.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 40.8 ± 0.0 |
| SFT | 3 | 67.9 ± 3.9 | 98.0 ± 0.8 | 80.1 ± 2.6 | 81.1 ± 1.4 |
| GRPO | 3 | 48.6 ± 21.9 | 59.7 ± 20.4 | 51.6 ± 15.3 | 68.5 ± 20.8 |

## vtg_test

| Condition | Seeds | First-error | Clean | Error F1 | Within-one |
|---|---|---|---|---|---|
| Base | 1 | 31.2 ± 0.0 | - | - | 58.5 ± 0.0 |
| SFT | 3 | 18.6 ± 4.3 | - | - | 42.1 ± 6.1 |
| GRPO | 3 | 27.8 ± 2.3 | - | - | 54.7 ± 2.1 |

## Pre-registered tests

```json
{
 "H3": {
  "grpo": {
   "seen_gain": 0.7736205599720031,
   "seen_sd": 0.09652803026318421,
   "improves": true,
   "heldout_gain": 0.5161379547104888,
   "heldout_sd": 0.15304212175486911,
   "holds_gain": true
  },
  "sft": {
   "seen_gain": 0.9871897976994678,
   "seen_sd": 0.0025326611002548308,
   "improves": true,
   "heldout_gain": 0.8014950416274269,
   "heldout_sd": 0.02625411197176742,
   "holds_gain": true
  }
 },
 "H4": {
  "grpo": {
   "vtg_gain": -0.03408146300914383,
   "vtg_sd": 0.023070139794476995,
   "seen_gain": 0.49777777777777776,
   "supported": false
  },
  "sft": {
   "vtg_gain": -0.12551953449709063,
   "vtg_sd": 0.04263780084200219,
   "seen_gain": 0.6475555555555556,
   "supported": false
  }
 },
 "anti_position": {
  "base": {
   "mean": 0.2693333333333333,
   "seeds": [
    0.2693333333333333
   ],
   "position_only": 0.37466666666666665,
   "beats_mean": false,
   "beats_every_seed": false
  },
  "sft": {
   "mean": 0.6786666666666666,
   "seeds": [
    0.7213333333333334,
    0.6453333333333333,
    0.6693333333333333
   ],
   "position_only": 0.37466666666666665,
   "beats_mean": true,
   "beats_every_seed": true
  },
  "grpo": {
   "mean": 0.4857777777777778,
   "seeds": [
    0.7306666666666667,
    0.30933333333333335,
    0.41733333333333333
   ],
   "position_only": 0.37466666666666665,
   "beats_mean": true,
   "beats_every_seed": false
  }
 }
}
```

## Checkpoints (go/no-go)

| Label | Split | First-error | Clean | Error F1 |
|---|---|---|---|---|
| grpo-s0-step100 | dev | 69.9 | 1.6 | 3.1 |
| grpo-s0-step150 | dev | 72.5 | 0.8 | 1.6 |
| grpo-s0-step200 | dev | 81.6 | 0.8 | 1.6 |
| grpo-s0-step250 | dev | 77.1 | 5.6 | 10.4 |
| grpo-s0-step300 | dev | 77.3 | 28.0 | 41.1 |
| grpo-s0-step350 | dev | 73.6 | 84.8 | 78.8 |
| grpo-s0-step400 | dev | 85.1 | 69.6 | 76.6 |
| grpo-s0-step50 | dev | 77.9 | 0.0 | 0.0 |
| smoke-grpo | dev | 40.0 | 0.0 | 0.0 |
