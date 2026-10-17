"""The model's explanation: Qwen3.5-27B via Hugging Face Inference Providers.

Uses the frozen Phase 2 prompt (p2-v1) in the "true location" condition of E2:
the model is told the checker's first wrong step and writes one sentence. The
reply is shown as the model's guess, never as a verified claim.
"""
import os

from core.prompts import PROMPT_VERSION, build_request, parse_response

MODEL = os.environ.get("FEEDBACK_MODEL", "Qwen/Qwen3.5-27B")
TIMEOUT = float(os.environ.get("FEEDBACK_TIMEOUT", "30"))


class Unavailable(RuntimeError):
    """The model could not be reached (no token, no credit, timeout, provider error)."""


def _client():
    from huggingface_hub import InferenceClient
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise Unavailable("no HF_TOKEN set")
    return InferenceClient(model=MODEL, token=token, timeout=TIMEOUT)


def explain(problem: str, steps: list[str], first_error: int, client=None) -> dict:
    item = {"id": "app", "source": "synthetic", "problem": problem, "steps": steps, "first_error": first_error}
    req = build_request(item, "true")
    try:
        out = (client or _client()).chat_completion(
            messages=[{"role": "system", "content": req.instructions}, {"role": "user", "content": req.input}],
            max_tokens=256, temperature=0.0,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        text = out.choices[0].message.content or ""
    except Unavailable:
        raise
    except Exception as e:  # HTTP 402/429/5xx, timeouts: the checker result still stands
        raise Unavailable(type(e).__name__) from e
    parsed = parse_response(text)
    if parsed.feedback is None:
        raise Unavailable("unparseable reply")
    return {"feedback": parsed.feedback, "step": parsed.step, "agrees": parsed.step == first_error,
            "model": MODEL, "prompt": PROMPT_VERSION}
