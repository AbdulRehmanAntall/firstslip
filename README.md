# FirstSlip

**Finding the first wrong step in student algebra with a symbolic checker.**

> Status: project idea / pre-registration stage. Code, data and results will be added phase by phase (see [PHASES.md](PHASES.md) and [PROGRESS.md](PROGRESS.md)).

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
| Solution and error generator | Own Python module (16 equation types, misconception table from Sonkar et al., 2024) |
| Step checker | SymPy |
| Teacher-annotated test set | [VtG on Hugging Face](https://huggingface.co/datasets/eth-nlped/stepverify) |
| Open models | Qwen3.5-2B / 4B (fallback: Qwen3-1.7B) |
| Training | TRL `GRPOTrainer` / `SFTTrainer`, Unsloth + LoRA, Kaggle T4 GPUs |
| Student app | FastAPI + MathLive, hosted on Hugging Face Spaces |

## Planned deliverables

1. An open-source generator and SymPy checker for algebra solutions with known first errors
2. A benchmark of synthetic test sets (seen and held-out misconceptions) with a dataset card
3. Prompted results for four models on localization, faithfulness and deference to a wrong verifier
4. A live student app that separates verified feedback from the model's guesses
5. Trained checkpoints (SFT and GRPO, three seeds each) with held-out and VtG results
6. A four- to six-page technical report
7. A 60-second screen recording of the app

## Scope note

No learner data is collected and no learner study is run. VtG solutions were written by an LLM simulating a student, not by real students. Results are about model behaviour, not learning outcomes.

The full proposal is in [`FirstSlip Project Proposal.pdf`](FirstSlip%20Project%20Proposal.pdf).
