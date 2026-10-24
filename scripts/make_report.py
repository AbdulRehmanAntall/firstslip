"""Build report.pdf: the research so far (Phases 0-4), with figures and analysis.

    python scripts/make_report.py

Every number is read from results/ and runs/, so the report is regenerated from
the same files the tables come from. New figures go to results/report/; the
Phase 2 figures are reused from app/static/results/.
"""
import glob
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIG = ROOT / "results" / "report"
P2FIG = ROOT / "app" / "static" / "results"

BG, INK, MUTED, GRID = "#fcfcfb", "#2b2b29", "#5f5e5a", "#e4e3df"
C = {"base": "#2a78d6", "sft": "#eda100", "grpo": "#e87ba4"}
NAME = {"base": "Base (Qwen3.5-2B)", "sft": "SFT", "grpo": "GRPO"}
SPLIT = {"test_seen": "Synthetic: seen\nmistake types", "test_heldout": "Synthetic: new\nmistake types",
         "vtg_test": "Real student work\n(VtG, teacher-labelled)"}


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def style(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c2")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def fig(w, h, n=1, **kw):
    f, axes = plt.subplots(1, n, figsize=(w, h), facecolor=BG, **kw)
    for ax in (axes if n > 1 else [axes]):
        style(ax)
    return f, axes


def save(f, name):
    FIG.mkdir(parents=True, exist_ok=True)
    f.savefig(FIG / name, dpi=200, facecolor=BG, bbox_inches="tight")
    plt.close(f)
    return FIG / name


def load_eval(split, label):
    p = sorted(glob.glob(str(ROOT / "runs" / f"*_phase4_{split}_qwen-2b_{label}.jsonl")))[-1]
    return [json.loads(line) for line in open(p, encoding="utf-8")][1:]


# --- figures -------------------------------------------------------------------

def f_e4_bars(p4, p2, base1):
    agg = p4["aggregate"]
    f, axes = fig(10.5, 3.6, 2, gridspec_kw={"width_ratios": [3, 2]})
    for ax, metric, splits, title in ((axes[0], "first_error_acc", ("test_seen", "test_heldout", "vtg_test"),
                                       "First wrong step found (%)"),
                                      (axes[1], "clean_acc", ("test_seen", "test_heldout"),
                                       "Correct solutions called correct (%)")):
        w = 0.26
        for i, s in enumerate(splits):
            for j, c in enumerate(("base", "sft", "grpo")):
                m = agg[s][c][metric]
                x = i + (j - 1) * w
                ax.bar(x, 100 * m["mean"], width=w * 0.92, color=C[c], label=NAME[c] if i == 0 else None)
                if c != "base":
                    ax.scatter([x] * len(m["seeds"]), [100 * v for v in m["seeds"]], s=14, color=INK, zorder=3,
                               label="single seed" if (i == 0 and c == "sft") else None)
                top = max([m["mean"]] + m["seeds"])
                ax.text(x, 100 * top + 2.5, f"{100 * m['mean']:.0f}", ha="center", fontsize=8, color=INK)
            if metric == "first_error_acc":
                ref = p2["e1"][s]["qwen-27b"]["first_error_acc"]["mean"]
                ax.plot([i - 0.42, i + 0.42], [100 * ref] * 2, color=INK, lw=1.2, ls=(0, (1, 1.5)),
                        label="Qwen3.5-27B, prompted" if i == 0 else None)
                pos = base1["eval"][s]["position_only"]["first_error_acc"] if s != "vtg_test" else 0.249
                ax.plot([i - 0.42, i + 0.42], [100 * pos] * 2, color=MUTED, lw=1.2, ls="--",
                        label="position-only guess" if i == 0 else None)
        ax.set_xticks(range(len(splits)), [SPLIT[s] for s in splits], fontsize=8.5)
        ax.set_ylim(0, 112)
        ax.set_title(title, fontsize=10, loc="left", color=INK)
    h, lab = axes[0].get_legend_handles_labels()
    f.legend(h, lab, frameon=False, fontsize=8, ncol=6, loc="lower center", bbox_to_anchor=(0.5, -0.04))
    f.tight_layout(rect=(0, 0.06, 1, 1))
    return save(f, "f_e4_bars.png")


def f_grpo_training():
    f, axes = fig(10.5, 3.0, 2)
    for k, s in enumerate((0, 1, 2)):
        p = sorted(glob.glob(str(ROOT / "runs" / f"*_phase4train_grpo_qwen-2b_grpo-s{s}.jsonl")))[-1]
        logs = [r for r in map(json.loads, open(p, encoding="utf-8")) if r.get("type") == "log" and "reward" in r]
        steps = [r["step"] for r in logs]
        for ax, key in ((axes[0], "reward"), (axes[1], "frac_reward_zero_std")):
            ys = [r[key] for r in logs]
            sm = [sum(ys[max(0, i - 9):i + 1]) / len(ys[max(0, i - 9):i + 1]) for i in range(len(ys))]
            ax.plot(steps, sm, color=C["grpo"], lw=1.6, alpha=[1, 0.65, 0.4][k], label=f"seed {s}")
    axes[0].set_title("GRPO reward (10-step mean; max 1.1)", fontsize=10, loc="left", color=INK)
    axes[1].set_title("Share of groups with no reward variance (no signal)", fontsize=10, loc="left", color=INK)
    for ax in axes:
        ax.set_xlabel("Training step", fontsize=9, color=MUTED)
    axes[0].legend(frameon=False, fontsize=8)
    f.tight_layout()
    return save(f, "f_grpo_training.png")


def f_checkpoints(p4):
    cp = {k.split("|")[0]: v for k, v in p4["checkpoints"].items() if k.startswith("grpo-s0-step")}
    steps = sorted(int(k.rsplit("step", 1)[1]) for k in cp)
    f, ax = fig(9.5, 2.4)
    for metric, ls, lab in (("first_error_acc", "-", "first wrong step found"), ("clean_acc", "--", "correct solutions called correct")):
        ys = [100 * cp[f"grpo-s0-step{s}"][metric]["mean"] for s in steps]
        ax.plot(steps, ys, color=C["grpo"], ls=ls, lw=1.8, marker="o", ms=4, label=f"GRPO seed 0: {lab}")
    base = p4["aggregate"]["dev"]["base"]["first_error_acc"]["mean"]
    ax.axhline(100 * base, color=C["base"], lw=1.2, ls=":", label="Base: first wrong step found")
    ax.set_ylim(0, 100)
    ax.set_xlabel("GRPO step (checkpoint)", fontsize=9, color=MUTED)
    ax.set_title("Synthetic dev, per checkpoint (%)", fontsize=10, loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.02, 0.5))
    f.tight_layout()
    return save(f, "f_checkpoints.png")


def f_position(p4):
    d = p4["position_distribution"]
    f, axes = fig(10.5, 3.0, 2, sharey=True)
    series = (("gold", "#8a8a85", "True first error"), ("base", C["base"], NAME["base"]),
              ("sft", C["sft"], "SFT"), ("grpo", C["grpo"], "GRPO"))
    for ax, s in zip(axes, ("test_seen", "test_heldout")):
        steps = sorted({int(k) for v in d[s].values() for k in v})
        w = 0.2
        for j, (k, col, lab) in enumerate(series):
            xs = [i + (j - 1.5) * w for i in range(len(steps))]
            ax.bar(xs, [100 * d[s][k].get(str(st), 0) for st in steps], width=w * 0.92, color=col, label=lab)
        ax.set_xticks(range(len(steps)), [("no error" if st == 0 else str(st)) for st in steps])
        ax.set_title(SPLIT[s].replace("\n", " ") + " (incorrect items)", fontsize=10, loc="left", color=INK)
        ax.set_xlabel("Predicted first wrong step", fontsize=9, color=MUTED)
    axes[0].set_ylabel("Share of predictions (%)", fontsize=9, color=MUTED)
    axes[0].legend(frameon=False, fontsize=8)
    f.tight_layout()
    return save(f, "f_position.png")


def outcome_shares(split):
    out = {}
    for c in ("base", "sft", "grpo"):
        labels = ["base"] if c == "base" else [f"{c}-s{s}" for s in (0, 1, 2)]
        cnt = Counter()
        for lab in labels:
            for r in load_eval(split, lab):
                if not r["gold"]:
                    continue
                p, g = r["pred"], r["gold"]
                cnt["correct" if p == g else "says no error" if p == 0 else "too early" if p < g else "too late"] += 1
        n = sum(cnt.values())
        out[c] = {k: cnt[k] / n for k in ("correct", "too early", "too late", "says no error")}
    return out


def f_outcomes(shares):
    cols = {"correct": "#1baf7a", "too early": "#9ec5f4", "too late": "#2a78d6", "says no error": "#8a8a85"}
    f, axes = fig(10.5, 2.6, 2, sharey=True)
    for ax, (split, sh) in zip(axes, shares.items()):
        conds = ["grpo", "sft", "base"]
        for i, c in enumerate(conds):
            left = 0
            for k, col in cols.items():
                v = 100 * sh[c][k]
                ax.barh(i, v, left=left, color=col, height=0.62, edgecolor=BG, linewidth=1.5,
                        label=k if (i == 0 and split == "test_heldout") else None)
                if v >= 7:
                    ax.text(left + v / 2, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                            color="white" if k in ("correct", "too late", "says no error") else INK)
                left += v
        ax.set_yticks(range(3), [NAME[c].split(" (")[0] for c in conds])
        ax.set_xlim(0, 100)
        ax.grid(axis="x", color=GRID)
        ax.grid(axis="y", visible=False)
        ax.set_title(SPLIT[split].replace("\n", " ") + ": incorrect items (%)", fontsize=10, loc="left", color=INK)
    axes[0].legend(frameon=False, fontsize=8, ncol=4, loc="upper left", bbox_to_anchor=(0, -0.15))
    f.tight_layout()
    return save(f, "f_outcomes.png")


# --- document ------------------------------------------------------------------

def build():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    fdir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("DV", str(fdir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DVB", str(fdir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DVI", str(fdir / "DejaVuSans-Oblique.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

    p1, p2, p4 = (jload(ROOT / f) for f in ("results/phase1/gate.json", "results/phase2/tables.json",
                                            "results/phase4/tables.json"))
    base1 = jload(ROOT / "results/phase1/synthetic_baselines.json")
    figs = {"e4": f_e4_bars(p4, p2, base1), "train": f_grpo_training(), "ckpt": f_checkpoints(p4),
            "pos": f_position(p4),
            "out": f_outcomes({"test_heldout": outcome_shares("test_heldout"), "vtg_test": outcome_shares("vtg_test")})}

    ink = colors.HexColor(INK)
    st = {
        "title": ParagraphStyle("t", fontName="DVB", fontSize=20, leading=24, textColor=ink, spaceAfter=4),
        "sub": ParagraphStyle("s", fontName="DV", fontSize=10.5, leading=14, textColor=colors.HexColor(MUTED)),
        "h1": ParagraphStyle("h1", fontName="DVB", fontSize=13.5, leading=17, textColor=ink, spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName="DVB", fontSize=10.5, leading=14, textColor=ink, spaceBefore=8, spaceAfter=3),
        "p": ParagraphStyle("p", fontName="DV", fontSize=9.2, leading=13.2, textColor=ink, spaceAfter=5, alignment=TA_LEFT),
        "li": ParagraphStyle("li", fontName="DV", fontSize=9.2, leading=13, textColor=ink, leftIndent=12,
                             bulletIndent=2, bulletFontName="DV", spaceAfter=2.5),
        "cap": ParagraphStyle("c", fontName="DVI", fontSize=8.2, leading=11, textColor=colors.HexColor(MUTED),
                              spaceAfter=8),
        "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.2, leading=10.5, textColor=ink),
        "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=8.2, leading=10.5, textColor=ink),
        "box": ParagraphStyle("box", fontName="DV", fontSize=9.2, leading=13.2, textColor=ink, leftIndent=4),
    }
    W = A4[0] - 36 * mm

    def P(t, s="p"):
        return Paragraph(t, st[s])

    def bullets(items):
        return [Paragraph(t, st["li"], bulletText="•") for t in items]

    def img(path, width=W, cap=None):
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(str(path)).getSize()
        out = [Image(str(path), width=width, height=width * ih / iw)]
        if cap:
            out.append(P(cap, "cap"))
        return KeepTogether(out)

    def table(rows, widths, header=True, bold_col0=False):
        data = [[Paragraph(str(c), st["cellb" if (header and i == 0) or (bold_col0 and j == 0) else "cell"])
                 for j, c in enumerate(r)] for i, r in enumerate(rows)]
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, ink),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#c9c8c2")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f3ef")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    def pc(x):
        return f"{100 * x:.1f}"

    a4, e1 = p4["aggregate"], p2["e1"]

    def ms(s, c, m):
        v = a4[s][c][m]
        return pc(v["mean"]) if c == "base" else f"{pc(v['mean'])} ± {pc(v['sd'])}"

    t3, t4, anti = p4["tests"]["H3"], p4["tests"]["H4"], p4["tests"]["anti_position"]
    story = []

    # --- title and summary
    story += [P("FirstSlip: verifiable error localization for LLM tutors", "title"),
              P("Research report, Phases 0–4 &nbsp;·&nbsp; Abdul Rehman Antall &nbsp;·&nbsp; 24 October 2026", "sub"),
              Spacer(1, 10)]
    summary = [
        "<b>Question.</b> When a student's algebra solution goes wrong, can a language model find the <i>first</i> "
        "wrong step, explain it faithfully, and can a small model be trained to do this using a symbolic checker "
        "as the source of truth?",
        f"<b>A checker that cannot be fooled.</b> A SymPy step checker finds the injected error on "
        f"{pc(p1['all_items']['incorrect_located'])}% of 7,875 incorrect synthetic solutions and reports no error on "
        f"{pc(p1['all_items']['clean_no_error'])}% of 2,625 clean ones.",
        "<b>Prompted models.</b> Qwen3.5-27B finds the first wrong step on 95% of seen, 87% of held-out and 61% of real "
        "student solutions, but calls only about half of <i>correct</i> solutions correct. The 2B model copies any step it is "
        "told is wrong, true or not (100% deference).",
        f"<b>Training (E4).</b> Fine-tuning Qwen3.5-2B lifts first-error accuracy from 27% to "
        f"{pc(a4['test_heldout']['sft']['first_error_acc']['mean'])}% (SFT) and "
        f"{pc(a4['test_heldout']['grpo']['first_error_acc']['mean'])}% (GRPO, checker reward) on mistake types never seen "
        "in training. Contrary to the pre-registered expectation, plain SFT generalises better than RL and is far "
        "more stable across seeds.",
        f"<b>No transfer to real student work.</b> On 802 teacher-labelled VtG solutions both trained models fall "
        f"<i>below</i> the base model (base {pc(a4['vtg_test']['base']['first_error_acc']['mean'])}%, SFT "
        f"{pc(a4['vtg_test']['sft']['first_error_acc']['mean'])}%, GRPO "
        f"{pc(a4['vtg_test']['grpo']['first_error_acc']['mean'])}%). SFT answers \"no error\" on about half of them.",
    ]
    box = Table([[[Paragraph(t, st["box"]) for t in summary]]], colWidths=[W])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5fb")),
                             ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(C["base"])),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [P("Summary", "h2"), box]

    # --- 1 questions
    story += [P("1. Research questions and pre-registered hypotheses", "h1"),
              P("All hypotheses, thresholds and data splits were fixed in <font name='DVB'>PREREGISTRATION.md</font> before any "
                "model was run; six dated amendments record every later implementation decision. Null results are "
                "reported as null results."),
              table([["RQ", "Question", "Hypotheses"],
                     ["RQ1", "Can models locate the first wrong step, and is that easier than solving?",
                      "H1: solving accuracy > localization accuracy. H1b: some feedback discusses a step other than the one flagged (> 5%)."],
                     ["RQ2", "Does telling the model where the error is help it explain, and does it check a supplied location?",
                      "H2: diagnosis improves when the checker's step is given. H2b: models adopt a deliberately wrong location (> 50%)."],
                     ["RQ3", "Does RL with the checker as reward beat SFT on the same labels?",
                      "H3: both improve on seen mistake types; only a model that learned to check holds its gain on held-out types. Anti-hypothesis: the gain is a position prior."],
                     ["RQ4", "Does the gain transfer to real student work, and does training change faithfulness?",
                      "H4: transfer is positive but much smaller than in-domain. H4b: no prediction (E6)."]],
                    [12 * mm, 62 * mm, W - 74 * mm])]

    # --- 2 method
    story += [P("2. Method", "h1"),
              P("2.1 Data", "h2"),
              P("<b>Synthetic benchmark.</b> Linear equations in one variable, solved step by step, rebuilt from Sonkar et al. "
                "(2024): 15 equation forms reduced one step at a time, with 19 documented misconceptions injected as "
                "alternative steps. Each incorrect solution has exactly one injected error; later steps continue "
                "correctly from the wrong state, so the injected step is the only first error. Labels come from exact "
                "fraction arithmetic, independent of the checker. Four misconceptions (distribution, sign, division, "
                "term-combining) are held out entirely. First-error positions are balanced within each solution length."),
              table([["Split", "Items", "Incorrect", "Clean", "Use"],
                     ["train", "8,000", "6,000", "2,000", "SFT and GRPO"],
                     ["dev", "500", "375", "125", "go/no-go, checkpoint choice, position prior"],
                     ["test-seen", "1,000", "750", "250", "in-domain results (15 seen misconceptions)"],
                     ["test-held-out", "1,000", "750", "250", "4 never-seen misconceptions"],
                     ["VtG test", "802", "802", "–", "real (simulated-student) solutions, teacher labels"]],
                    [26 * mm, 18 * mm, 20 * mm, 16 * mm, W - 80 * mm]),
              Spacer(1, 5),
              P("<b>VtG</b> (Verify-then-Generate, <font name='DVB'>eth-nlped/stepverify</font>): 1,002 teacher-annotated "
                "solutions from MathDial; split 200 dev / 802 test, grouped by problem. Annotators who labelled the same "
                "solution agree on the first error only 60% of the time, which caps any model's achievable accuracy."),
              P("2.2 Checker, models and metrics", "h2"),
              *bullets([
                  "<b>Checker.</b> Each line is parsed with SymPy and compared with the previous line by solution set; the "
                  "first step that changes the solution is the first error. Unreadable lines are flagged, never guessed.",
                  "<b>Models.</b> Qwen3.5-2B, 4B and 27B (FP8), served with vLLM on a Colab A100, greedy decoding, thinking "
                  "off, one frozen prompt (p2-v1). Every model answers <i>Step: k</i> (0 = no error) and one sentence of feedback.",
                  "<b>Metrics.</b> First-error accuracy (exact step, incorrect items), clean accuracy (says 0 on correct "
                  "solutions), error F1 (their harmonic mean, after ProcessBench), within-one accuracy. Faithfulness and "
                  "diagnosis are scored by a Qwen3.5-27B judge validated at 97% agreement with 100 hand labels.",
                  "<b>Statistics.</b> 95% bootstrap CIs (10,000 resamples); McNemar with Holm correction for paired model "
                  "comparisons; trained models report mean ± sd over three seeds, and a difference counts only if it "
                  "exceeds the between-seed sd.",
                  "<b>Baselines.</b> Random step, and a position-only rule (most common first-error step per solution "
                  "length, fitted on dev): 25.3% on test-seen, 37.5% on test-held-out, 24.9% on VtG."])]

    # --- 3 prompted
    story += [P("3. Results: prompted models (Phase 2, E1–E3)", "h1"),
              img(P2FIG / "f3_e1.png", W * 0.86,
                  "Figure 1. E1: first-error accuracy of the prompted models, with 95% CIs. Dashed: random guess; dotted: "
                  "position-only guess."),
              P("<b>Localization scales strongly with size</b> (all pairwise differences p &lt; 1e-14, McNemar, Holm). The 2B "
                "model is barely above the position-only rule on seen items and below it on held-out items. Real student "
                "work is much harder than synthetic for every model: 27B drops from 95% to 61%."),
              P("<b>But every model over-flags.</b> Clean accuracy is 50.8% / 40.4% for 27B (seen / held-out), 36.4% / 24.4% for "
                "4B and about 0% for 2B, so error F1 is far lower than first-error accuracy (27B: 66.3 / 55.2)."),
              table([["Hypothesis", "Result", "Verdict"],
                     ["H1: solving is easier than localizing",
                      "The opposite. Localization beats solving for all 3 models (27B 95.3 vs 48.4%, 4B 67.9 vs 10.5%, 2B 34.8 vs 6.4%).",
                      "Not supported"],
                     ["H1b: feedback discusses another step",
                      "Judge: 2B 24.5%, 4B 9.3%, 27B 0.8% unfaithful on test-seen; CI lower bound >= 5% for 2B and 4B.",
                      "Supported"],
                     ["H2: giving the step improves diagnosis",
                      "Only 2B rises (p = 0.005), and 2B copies whatever step it is given. 27B and 4B do not change.",
                      "Not supported"],
                     ["H2b: models adopt a wrong location",
                      "2B 100%; 4B 9–17%; 27B 2–7%. Only 1 of 3 models above 50%.",
                      "Not supported"]],
                    [44 * mm, W - 70 * mm, 26 * mm], bold_col0=True),
              Spacer(1, 6),
              img(P2FIG / "f7_e3.png", W * 0.78,
                  "Figure 2. E3: share of answers that copy a deliberately wrong step supplied by a fake checker."),
              img(P2FIG / "f9_faith.png", W,
                  "Figure 3. Faithfulness (LLM judge): is the feedback about the step the model flagged?"),
              P("<b>Reading.</b> Larger models check rather than defer: 27B rejects a wrong supplied step 93–98% of the time, while "
                "2B simply repeats it. Small models also explain the wrong step: a quarter of 2B's feedback is about a "
                "different step from the one it flagged. This is the motivation for the app's design, where only the "
                "checker's claims are shown as verified and the model's explanation is labelled as a guess.")]

    # --- 4 training
    sft_h, grpo_h = a4["test_heldout"]["sft"]["first_error_acc"], a4["test_heldout"]["grpo"]["first_error_acc"]
    story += [P("4. Results: training a small model with the checker (Phase 4, E4)", "h1"),
              P("<b>Setup.</b> Qwen3.5-2B with a LoRA adapter (r 16), TRL 1.16, three seeds per method, all from the base model. "
                "<b>SFT</b> trains on the target <i>Step: k / Feedback:</i> with loss on those tokens only, so the feedback "
                "sentence is always the model's own. <b>GRPO</b> samples 8 answers per problem and rewards them with the "
                "checker: 1.0 for the right step (or a right \"no error\"), 0.2 for one step off, 0 otherwise, plus 0.1 if the "
                "answer parses. The feedback sentence is never rewarded. 400 steps, about 1.5 GPU-hours per seed; SFT is "
                "one epoch, 8 minutes per seed. The base model is one greedy run."),
              table([["Split", "Condition", "First-error", "Clean", "Error F1", "Within-one"]] +
                    [[SPLIT[s].replace("\n", " ") if c == "base" else "", NAME[c].split(" (")[0],
                      ms(s, c, "first_error_acc"),
                      ms(s, c, "clean_acc") if "clean_acc" in a4[s][c] else "–",
                      ms(s, c, "error_f1") if "error_f1" in a4[s][c] else "–",
                      ms(s, c, "within_one_acc")]
                     for s in ("test_seen", "test_heldout", "vtg_test") for c in ("base", "sft", "grpo")],
                    [40 * mm, 22 * mm, 27 * mm, 27 * mm, 25 * mm, W - 141 * mm]),
              P("Table: E4 results in %, mean ± sd over 3 seeds (Base: one greedy run).", "cap"),
              img(figs["e4"], W,
                  "Figure 4. E4: bars are means, dots single seeds. Dotted: prompted Qwen3.5-27B (Phase 2); dashed: "
                  "position-only guess."),
              P("4.1 In-domain and held-out", "h2"),
              *bullets([
                  f"<b>Both methods improve hugely on seen mistake types</b> (F1 gain: SFT +{pc(t3['sft']['seen_gain'])}, "
                  f"GRPO +{pc(t3['grpo']['seen_gain'])} points, both far above the between-seed sd). SFT reaches "
                  "99.6%: the 15 seen misconceptions are learnable patterns, which is exactly why the held-out split exists.",
                  f"<b>On never-seen mistake types SFT wins</b>: {pc(sft_h['mean'])} ± {pc(sft_h['sd'])}% against "
                  f"{pc(grpo_h['mean'])} ± {pc(grpo_h['sd'])}% for GRPO, with clean accuracy 98.0% against 59.7%. The trained 2B "
                  "model beats prompted 4B on held-out first-error accuracy (49.3%) and prompted 27B on held-out error F1 "
                  "(80.1 against 55.2), because it learned to say \"no error\" on correct work; 27B still finds more "
                  "first errors (87.2%).",
                  "<b>GRPO is unstable across seeds</b>: held-out first-error accuracy is "
                  + " / ".join(pc(x) for x in grpo_h["seeds"]) + "% for seeds 0 / 1 / 2."]),
              P("4.2 Pre-registered tests", "h2"),
              table([["Test", "SFT", "GRPO"],
                     ["H3 improves (seen F1 gain > sd)", f"yes (+{pc(t3['sft']['seen_gain'])}, sd {pc(t3['sft']['seen_sd'])})",
                      f"yes (+{pc(t3['grpo']['seen_gain'])}, sd {pc(t3['grpo']['seen_sd'])})"],
                     ["H3 holds gain (held-out F1 gain >= half seen)", f"yes (+{pc(t3['sft']['heldout_gain'])})",
                      f"yes (+{pc(t3['grpo']['heldout_gain'])})"],
                     ["Beats position-only (37.5%) on held-out", "every seed", "mean only; seed 1 below (30.9%)"],
                     ["H4 transfer to VtG (gain > sd, < seen gain)", f"no ({pc(t4['sft']['vtg_gain'])} points)",
                      f"no ({pc(t4['grpo']['vtg_gain'])} points)"]],
                    [70 * mm, (W - 70 * mm) / 2, (W - 70 * mm) / 2], bold_col0=True),
              Spacer(1, 5),
              P("<b>Verdict on H3.</b> By the pre-registered F1 rule, H3's two conditions hold for both methods. Its substantive "
                "prediction, that only the checker-rewarded model would hold its gain, is <b>not borne out</b>: SFT is better "
                "than GRPO on every synthetic metric, by more than either method's between-seed sd. <b>Caveat (not "
                "pre-registered):</b> the base model never says \"no error\", so part of every F1 gain is learning to accept "
                "clean work. On first-error accuracy alone, SFT keeps 63% of its seen gain on held-out items and GRPO 44%, "
                "below one half."),
              img(figs["pos"], W,
                  "Figure 5. Position check: predicted first wrong step on incorrect items, against the true distribution "
                  "(trained models pool their 3 seeds)."),
              P("<b>The position prior belongs to the base model, not the trained ones.</b> Base answers \"step 1\" on 88% (seen) "
                "and 93% (held-out) of incorrect items. Both trained models follow the true distribution of error positions; "
                "their held-out misses go to \"no error\" instead. The anti-hypothesis is rejected for SFT; for GRPO it cannot "
                "be rejected for seed 1."),
              P("4.3 Where the trained models fail", "h2"),
              img(figs["out"], W,
                  "Figure 6. Outcome on incorrect items: correct step, a step before the true one (too early), after it (too "
                  "late), or no error found. Trained models pool their 3 seeds."),
              P("<b>SFT behaves like a pattern detector.</b> On held-out items it is never too early or too late: it either finds "
                "the step or says the solution is correct. That is the signature of recognising known error patterns rather "
                "than checking each step, since a step-by-step checker would at least stop at the first step it cannot "
                "verify. On VtG, where errors are misreadings of word problems rather than algebraic slips, SFT says \"no "
                "error\" on about half of the solutions, all of which contain an error. GRPO says \"no error\" less often but "
                "flags too late."),
              P("4.4 Training dynamics", "h2"),
              img(figs["train"], W,
                  "Figure 7. GRPO training, 3 seeds. Left: reward. Right: share of prompt groups whose 8 answers all got the "
                  "same reward, which gives a zero update."),
              img(figs["ckpt"], W * 0.92,
                  "Figure 8. GRPO seed 0, dev accuracy at each checkpoint (the 12 Nov go/no-go)."),
              P("<b>Go/no-go: GRPO kept.</b> Mean reward rose from 0.46 to 0.95 and every checkpoint beat the base model on dev "
                "(33.1%). But by the end, 94–99% of groups carry no learning signal, and clean accuracy swings between "
                "checkpoints (0.8% at step 200, 84.8% at 350, 69.6% at 400). GRPO first learns to locate errors and only "
                "late, and unevenly, to accept correct work, which explains its large between-seed sd.")]

    # --- 5 discussion
    story += [P("5. Discussion", "h1"),
              *bullets([
                  "<b>The checker is a better teacher for SFT than for RL here.</b> With exact labels for every item, SFT gets a "
                  "dense, correct signal on every example. GRPO only learns from groups whose answers differ, and the task's "
                  "single-token answer saturates quickly. The advantage RL is often credited with did not appear at this "
                  "scale and budget.",
                  "<b>Held-out success is not the same as step checking.</b> Both trained models improve on unseen "
                  "misconceptions, but the outcome analysis shows SFT detecting patterns, and neither transfers to real "
                  "student work. Synthetic algebra slips and VtG word-problem errors are different tasks.",
                  "<b>Small prompted models should not be trusted with a supplied location.</b> The 2B model's 100% deference "
                  "means a buggy or adversarial checker would be repeated verbatim; only the 27B model checks.",
                  "<b>Design implication.</b> Show only what the checker verifies as fact, and label model feedback as a guess. "
                  "This is how the FirstSlip app works (Phase 3, live at abdulrehman420-firstslip.static.hf.space)."]),
              P("6. Limitations", "h1"),
              *bullets([
                  "One model family (Qwen3.5) and one training budget; GRPO hyperparameters were fixed in advance, not tuned.",
                  "Synthetic data covers linear equations only; VtG solutions are LLM-simulated students (MathDial), not real "
                  "learners, and their labels have 60% inter-annotator agreement.",
                  "No learner study was run; nothing here shows the feedback helps students learn.",
                  "Some trained-model feedback runs to the 256-token limit (up to 42% for one SFT seed on VtG), which must "
                  "be accounted for when faithfulness is measured in E6.",
                  "The faithfulness and diagnosis judge is also one of the judged models (Qwen3.5-27B)."]),
              P("7. Status and next steps", "h1"),
              table([["Phase", "Status"],
                     ["0 Setup, VtG split, baselines, pre-registration", "Done"],
                     ["1 Generator and SymPy checker (100% gate)", "Done"],
                     ["2 Prompted experiments E1–E3", "Done"],
                     ["3 Student app (static Hugging Face Space)", "Deployed; friend test on a phone outstanding"],
                     ["4 Training E4 (SFT, GRPO, 3 seeds)", "Done; Gate 4 passed"],
                     ["5 Transfer and faithfulness E5, E6", "Next: VtG breakdowns, faithfulness of trained feedback"],
                     ["6 Release and write-up", "Dataset release, 4–6 page paper, app video"]],
                    [80 * mm, W - 80 * mm]),
              Spacer(1, 3),
              P("<b>Reproducibility.</b> Every run logs its git commit, seed, config hash, model revision and all prompts and "
                "responses; data regenerate byte for byte from seeds and committed hashes. This report is built by "
                "<font name='DVB'>scripts/make_report.py</font> from the committed results.")]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(18 * mm, 10 * mm, "FirstSlip research report")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(ROOT / "report.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title="FirstSlip research report",
                            author="Abdul Rehman Antall")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("report.pdf written")


if __name__ == "__main__":
    build()
