# FirstSlip

**Finding the first wrong step in student algebra with a symbolic checker.**

> Status: Phase 1 complete (generator, checker and synthetic benchmark). Later phases are added as they finish; see [PHASES.md](PHASES.md) and [PROGRESS.md](PROGRESS.md).

## The idea

Large language models solve grade-school maths well, but they are often poor at saying *where* a student went wrong. On the VtG set of 1,002 teacher-annotated student solutions, GPT-4o located the first wrong step in only 54.5% of cases without a reference solution (random guessing: 18.3%). Models tend to correct an error well once told where it is, but rarely find it themselves.

For tutoring this matters: feedback aimed at the wrong step can send a learner off to "fix" something that was already correct, and a tutor that sounds confident while pointing at the wrong step is a real risk to learning.

FirstSlip tackles this with one central component: **an exact SymPy step checker**. Given a student's algebra solution, it returns the first step whose solution set differs from the step before it. Every step of every synthetic solution is labelled exactly by this checker, and those labels are used in three ways:

1. **To measure** how well off-the-shelf LLMs locate the first error, name the misconception, and write feedback about the step they actually flagged.
2. **To ground** LLM feedback in the checker's verified error location, and to test whether models blindly repeat a deliberately wrong location.
3. **To train** a small open model (~2B parameters) with reinforcement learning (GRPO), using the checker as the reward.

The trained model is then tested on the teacher-annotated VtG solutions, where no checker applies, to see whether the skill transfers. A small web tutor shows learners which parts of its feedback the checker has verified and which are the model's own guess.

## Research questions

- **RQ1 – Measurement:** How often do current LLMs locate the first wrong step, name the misconception, and write feedback about the same step they flagged?
- **RQ2 – Grounding and trust:** Does giving the model the checker's error location improve its feedback, and how often does the model repeat a location that is deliberately wrong?
- **RQ3 – Training from the checker:** Does RL with the checker as reward improve error localization in a small open model compared with supervised fine-tuning on the same labels, including on held-out misconception types?
- **RQ4 – Transfer and side effects:** Does the gain carry over to teacher-annotated VtG solutions, and does rewarding only the step number change how faithful the model's explanations are?

## Planned components

| Component | Planned tool |
|---|---|
| Solution and error generator | `core/generator.py` (15 equation forms and 19 misconceptions from Sonkar et al., 2024) |
| Step checker | `core/checker.py` (SymPy) |
| Teacher-annotated test set | [VtG on Hugging Face](https://huggingface.co/datasets/eth-nlped/stepverify) |
| Open models | Qwen3.5-2B / 4B (fallback: Qwen3-1.7B) |
| Training | TRL `GRPOTrainer` / `SFTTrainer`, Unsloth + LoRA, Colab Pro GPU |
| Student app | FastAPI + MathLive, hosted on Hugging Face Spaces |

## Reproducing Phase 1

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Python 3.12
python scripts/generate_synthetic.py   # data/synthetic/*.jsonl; hashes in data/synthetic/manifest.json
python scripts/phase1_gate.py          # checker vs. generator labels (Gate 1), ~9 min
python scripts/synthetic_baselines.py  # random and position-only baselines
python -m pytest
```

Checking a solution:

```python
from core.checker import check
check("2x = 3(x + 4)", ["2x = 3x + 4", "-x = 4", "x = -4"]).first_error  # -> 1
```

The benchmark is described in its [dataset card](data/synthetic/README.md).

## Planned deliverables

1. An open-source generator and SymPy checker for algebra solutions with known first errors
2. A benchmark of synthetic test sets (seen and held-out misconceptions) with a dataset card
3. Prompted results for three open models (Qwen3.5 2B, 4B, 27B) on localization, faithfulness and deference to a wrong verifier
4. A live student app that separates verified feedback from the model's guesses
5. Trained checkpoints (SFT and GRPO, three seeds each) with held-out and VtG results
6. A four- to six-page technical report
7. A 60-second screen recording of the app

## Scope note

No learner data is collected and no learner study is run. VtG solutions were written by an LLM simulating a student, not by real students. Results are about model behaviour, not learning outcomes.

The full proposal is in [`FirstSlip Project Proposal.pdf`](FirstSlip%20Project%20Proposal.pdf).
