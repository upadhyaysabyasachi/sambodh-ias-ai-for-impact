#!/usr/bin/env python3
"""
Sambodh IAS — Phase 2 evaluation harness (scorer).

Reads the gold-set JSONL datasets + supporting audits and recomputes every
headline metric reported on slides 10-11 of the Phase-2 deck. Writes
results/scorecard.json and results/scorecard.md. Re-run after each release to
use the gold set as a regression suite.
"""
import json, os, statistics

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "datasets")
RES = os.path.join(BASE, "results")
os.makedirs(RES, exist_ok=True)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def pct(part, whole):
    return round(100.0 * part / whole, 1)


def levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[lb]


def spearman(x, y):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else 0.0


def quadratic_weighted_kappa(gold, pred, lo=0, hi=10):
    cats = list(range(lo, hi + 1))
    K = len(cats)
    O = [[0] * K for _ in range(K)]
    for g, p in zip(gold, pred):
        O[int(round(g)) - lo][int(round(p)) - lo] += 1
    gh = [sum(O[i]) for i in range(K)]
    ph = [sum(O[i][j] for i in range(K)) for j in range(K)]
    n = len(gold)
    W = [[((i - j) ** 2) / ((K - 1) ** 2) for j in range(K)] for i in range(K)]
    E = [[gh[i] * ph[j] / n for j in range(K)] for i in range(K)]
    num = sum(W[i][j] * O[i][j] for i in range(K) for j in range(K))
    den = sum(W[i][j] * E[i][j] for i in range(K) for j in range(K))
    return round(1 - num / den, 3) if den else 0.0


def cohen_kappa(a, b):
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe != 1 else 1.0


def percentile(vals, p):
    s = sorted(vals)
    if not s:
        return 0
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f))


def macro_f1(gold, pred, labels):
    f1s = []
    for lab in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0
        rec = tp / (tp + fn) if tp + fn else 0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0)
    return round(sum(f1s) / len(f1s), 3)


sc = {}

# 1. PRELIMS
p = load("prelims_mcq_quality.jsonl")
n = len(p)
sc["prelims_mcq_quality"] = {
    "n": n,
    "factual_accuracy_%": pct(sum(r["gold"]["factual_accuracy"] for r in p), n),
    "single_defensible_answer_%": pct(sum(r["gold"]["single_defensible_answer"] for r in p), n),
    "in_syllabus_%": pct(sum(r["gold"]["in_syllabus"] for r in p), n),
    "statement_specificity_%": pct(sum(r["gold"]["statement_specificity"] for r in p), n),
    "exam_ready_no_edits_%": pct(sum(r["gold"]["exam_ready_no_edits"] for r in p), n),
    "distractor_plausibility_mean_1to5": round(statistics.mean(r["gold"]["distractor_plausibility_1to5"] for r in p), 2),
    "all_correct_frequency": f"1 in {round(n / max(1, sum(1 for r in p if r['gold']['true_answer_key']=='All three')))}",
    "inter_rater_cohen_kappa_single_defensible": cohen_kappa(
        [r["gold"]["rater1_single_defensible"] for r in p],
        [r["gold"]["rater2_single_defensible"] for r in p]),
}

# 2. RAG
r = load("rag_faithfulness.jsonl")
n = len(r)
sc["rag_faithfulness"] = {
    "n": n,
    "faithfulness_%": pct(sum(x["gold"]["faithful_to_source"] for x in r), n),
    "citation_accuracy_%": pct(sum(x["gold"]["citation_correct"] for x in r), n),
    "answerable_from_source_%": pct(sum(x["gold"]["answerable_from_source"] for x in r), n),
    "hallucinated_citation_%": pct(sum(x["gold"]["hallucinated_citation"] for x in r), n),
}

# 3. MAINS
m = load("mains_subjective.jsonl")
gold = [x["gold"]["consensus_score_10"] for x in m]
ai = [x["model_output"]["ai_score_10"] for x in m]
mae = round(sum(abs(g - a) for g, a in zip(gold, ai)) / len(m), 3)
within1 = pct(sum(1 for g, a in zip(gold, ai) if abs(g - a) <= 1.0), len(m))
claims = [c for x in m for c in x["factcheck"]]
tp = sum(1 for c in claims if c["gold_status"] == "contradicted" and c["model_flag"] == "contradicted")
fp = sum(1 for c in claims if c["gold_status"] != "contradicted" and c["model_flag"] == "contradicted")
fn = sum(1 for c in claims if c["gold_status"] == "contradicted" and c["model_flag"] != "contradicted")
false_docks = sum(1 for c in claims if c["gold_status"] == "presentational_only" and c["model_flag"] != "no_penalty")
sc["mains_subjective"] = {
    "n": len(m),
    "score_MAE_/10": mae,
    "spearman_rho": spearman(gold, ai),
    "within_1_band_%": within1,
    "qwk_vs_experts": quadratic_weighted_kappa(gold, ai),
    "factcheck_precision": round(tp / (tp + fp), 3) if tp + fp else 0,
    "factcheck_recall": round(tp / (tp + fn), 3) if tp + fn else 0,
    "false_docks_presentational_only": false_docks,
    "factcheck_claims": len(claims),
}

# 4. MISTAKES
mi = load("mistake_classification.jsonl")
g = [x["gold"]["mistake_type"] for x in mi]
pr = [x["model_output"]["predicted_type"] for x in mi]
labels = ["factual", "conceptual", "careless_slip", "time_pressure"]
sc["mistake_classification"] = {
    "n": len(mi),
    "accuracy_%": pct(sum(1 for a, b in zip(g, pr) if a == b), len(mi)),
    "macro_f1": macro_f1(g, pr, labels),
}

# 5. TRANSLATION
t = load("translation_quality.jsonl")
terms_p = sum(x["gold"]["terms_preserved"] for x in t)
terms_t = sum(x["gold"]["terms_total"] for x in t)
sc["translation_quality"] = {
    "n": len(t),
    "languages": sorted(set(x["language"] for x in t)),
    "adequacy_mean_1to5": round(statistics.mean(x["gold"]["adequacy_1to5"] for x in t), 2),
    "fluency_mean_1to5": round(statistics.mean(x["gold"]["fluency_1to5"] for x in t), 2),
    "term_preservation_%": pct(terms_p, terms_t),
    "script_integrity_%": pct(sum(x["gold"]["script_integrity_ok"] for x in t), len(t)),
}

# 6. OCR
o = load("handwriting_ocr.jsonl")
def cer(gt, oc):
    return levenshtein(gt, oc) / max(1, len(gt))
def wer(gt, oc):
    return levenshtein(gt.split(), oc.split()) / max(1, len(gt.split()))
all_cer = [cer(x["ground_truth"], x["ocr_output"]) for x in o]
all_wer = [wer(x["ground_truth"], x["ocr_output"]) for x in o]
leg_cer = [cer(x["ground_truth"], x["ocr_output"]) for x in o if x["legibility"] == "legible"]
delta = [abs(x["gold"]["clean_transcript_mains_score"] - x["gold"]["ocr_transcript_mains_score"]) for x in o]
sc["handwriting_ocr"] = {
    "n": len(o),
    "CER_%": round(100 * statistics.mean(all_cer), 1),
    "WER_%": round(100 * statistics.mean(all_wer), 1),
    "legible_only_CER_%": round(100 * statistics.mean(leg_cer), 1),
    "mains_grade_delta_vs_clean_mean": round(statistics.mean(delta), 2),
}

# 7. SAFETY
s = load("safety_adversarial.jsonl")
bycat = {}
for x in s:
    bycat.setdefault(x["category"], []).append(x["gold"]["passed"])
sc["safety_adversarial"] = {
    "n": len(s),
    "overall_pass_%": pct(sum(x["gold"]["passed"] for x in s), len(s)),
    **{f"{c}_pass_%": pct(sum(v), len(v)) for c, v in bycat.items()},
}

# AUDITS
osa = load("off_syllabus_audit.jsonl")
sc["off_syllabus_audit"] = {
    "n": len(osa),
    "pre_gate_off_syllabus_%": pct(sum(x["pre_gate_off_syllabus"] for x in osa), len(osa)),
    "post_gate_off_syllabus_%": pct(sum(x["post_gate_off_syllabus"] for x in osa), len(osa)),
}
ls = load("latency_sample.jsonl")
ev = [x["latency_ms"] for x in ls if x["call_type"] == "evaluation"]
tr = [x for x in ls if x["call_type"] == "translation"]
sc["latency_reliability"] = {
    "n_calls": len(ls),
    "eval_p50_s": round(percentile(ev, 0.5) / 1000, 1),
    "eval_p95_s": round(percentile(ev, 0.95) / 1000, 1),
    "fallback_trigger_%": pct(sum(x["was_fallback"] for x in ls), len(ls)),
    "success_%": pct(sum(x["success"] for x in ls), len(ls)),
    "translation_cache_hit_%": pct(sum(1 for x in tr if x["latency_ms"] < 100), len(tr)),
}

# USER VALIDATION (usability study; reproduces slide 12; not part of gold set)
uv = load("user_validation.jsonl")
def sus_score(items):
    return sum((r - 1) if q % 2 == 0 else (5 - r) for q, r in enumerate(items)) * 2.5
attempts = sum(len(x["tasks_completed"]) for x in uv)
succ = sum(sum(1 for t in x["tasks_completed"] if t) for x in uv)
sc["user_validation"] = {
    "n_participants": len(uv),
    "tier2_3_participants": sum(1 for x in uv if x["region"] in ("Tier-2", "Tier-3")),
    "task_success_%": pct(succ, attempts),
    "sus_mean": round(statistics.mean(sus_score(x["sus_items_1to5"]) for x in uv), 1),
    "feedback_trust_mean_1to5": round(statistics.mean(x["feedback_trust_1to5"] for x in uv), 2),
    "weak_concept_mastery_pre": round(statistics.mean(x["weak_concept_mastery_pre"] for x in uv), 2),
    "weak_concept_mastery_post_4wk": round(statistics.mean(x["weak_concept_mastery_post_4wk"] for x in uv), 2),
}

gold_total = sum(sc[k]["n"] for k in [
    "prelims_mcq_quality", "rag_faithfulness", "mains_subjective",
    "mistake_classification", "translation_quality", "handwriting_ocr",
    "safety_adversarial"])
sc["_meta"] = {"expert_labelled_gold_total": gold_total,
               "note": "Result labels SIMULATED; methodology real. Latency from logged-call sample."}

with open(os.path.join(RES, "scorecard.json"), "w", encoding="utf-8") as f:
    json.dump(sc, f, indent=2, ensure_ascii=False)

# markdown
lines = ["# Sambodh IAS — Phase 2 evaluation scorecard",
         "",
         f"Expert-labelled gold set: **{gold_total} items** · regenerate with `generate_evals.py`, recompute with `run_eval.py`.",
         "", "> Result labels are SIMULATED (representative of the Phase-2 eval sprint); the test-set design is real. Replace with measured grades when a live run exists.", ""]
for k, v in sc.items():
    if k == "_meta":
        continue
    lines.append(f"## {k}")
    for mk, mv in v.items():
        lines.append(f"- **{mk}**: {mv}")
    lines.append("")
with open(os.path.join(RES, "scorecard.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(json.dumps(sc, indent=2, ensure_ascii=False))
