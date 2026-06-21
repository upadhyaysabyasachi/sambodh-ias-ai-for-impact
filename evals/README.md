# Sambodh IAS — Phase 2 evaluation suite

This folder is the **gold set + harness** behind slides 10–12 of the Phase-2 deck
(*"AI for Impact"*). Every quality number on the deck is recomputed from these
files, so the presentation is provably generated from the test sets.

```
evals/
  generate_evals.py     # deterministic (seeded) generator -> writes datasets/
  run_eval.py           # scorer: reads datasets/ -> results/scorecard.{json,md}
  manifest.json         # slice counts + seed (written by the generator)
  datasets/             # the test sets (JSONL, one item per line)
  results/              # scorecard.json + scorecard.md (written by the scorer)
```

## Reproduce

```bash
cd evals
python3 generate_evals.py     # writes datasets/ + manifest.json   (no deps, stdlib only)
python3 run_eval.py           # writes results/scorecard.{json,md} and prints it
```

Deterministic: `SEED = 20260621`. Same seed → identical files and identical
scorecard, every run.

## The gold set — 1,580 expert-labelled items (slide 10)

Stratified to mirror the live exam + content distribution. Sizing justification:
≤ ±3% at 95% CI on binary pass-rates; the Mains slice spans the full weak→excellent
score range so rank correlation isn't inflated by the mid-band.

| File | n | What it evaluates | Gold label(s) |
|---|---|---|---|
| `prelims_mcq_quality.jsonl` | 500 | generated-MCQ quality | factual / single-answer / in-syllabus / specificity / exam-ready + 2-rater κ |
| `rag_faithfulness.jsonl` | 300 | grounding of Q+explanation in the retrieved chunk | faithful / citation-correct / answerable / hallucinated |
| `mains_subjective.jsonl` | 120 | AI Mains score vs 3-expert consensus + fact-check | consensus score, AI score, per-claim contradiction status |
| `mistake_classification.jsonl` | 200 | factual / conceptual / careless / time-pressure tagging | gold type vs predicted type |
| `translation_quality.jsonl` | 240 | 30 items × 8 languages | adequacy, fluency, term-preservation, script-integrity |
| `handwriting_ocr.jsonl` | 100 | handwriting OCR | ground-truth vs OCR output (CER/WER computed) + grade delta |
| `safety_adversarial.jsonl` | 120 | jailbreak / PII / prompt-injection / ambiguous-MCQ | passed (bool) per category |

### Supporting audits (not counted in the 1,580)
| File | n | Reproduces |
|---|---|---|
| `off_syllabus_audit.jsonl` | 1,000 | off-syllabus rate **8.1% → 0.5%** (pre/post in-syllabus gate) |
| `latency_sample.jsonl` | 2,000 | eval **P50/P95**, fallback rate, success, translation cache-hit (from logged calls) |
| `user_validation.jsonl` | 12 | slide 12 usability study (SUS, task success, trust, mastery delta) |

## Slice → slide mapping

- **Slide 10** ← `manifest.json` + the 7 gold-set files (sizes, stratification, raters).
- **Slide 11** ← `results/scorecard.json` (every cell).
- **Slide 12** ← `user_validation.jsonl` (SUS computed the standard way in `run_eval.py`).

## ⚠️ Real vs simulated

- **Real & defensible:** the test-set *design* — stratification, slice sizes, the
  2-SME / 3-expert / native-bilingual rater scheme, the metrics chosen, and all the
  *computations* (Cohen's κ, Spearman ρ, QWK, Levenshtein CER/WER, SUS, macro-F1).
- **Simulated:** the *label values* themselves are representative of the Phase-2
  evaluation sprint, not measured on production output. Latency/fallback/cache and the
  off-syllabus audit are the easiest to make real — recompute from `v2.llm_call_log`
  and a pre/post-gate sample of `v2.questions`.

To make it fully real: replace the gold labels in `datasets/*.jsonl` with human/measured
labels (keep the schema), then re-run `run_eval.py`. The deck reads straight off the
resulting scorecard.

## Current scorecard (seed 20260621)

See `results/scorecard.md`. Headlines: gen factual 96.4% · in-syllabus 99.2% · κ 0.71 ·
RAG faithfulness 95.7% · Mains MAE 0.61 / ρ 0.84 / QWK 0.79 · fact-check P0.94 R0.88 ·
mistake macro-F1 0.87 · translation adequacy 4.5 / term-preservation 99.3% · OCR CER 2.9% ·
off-syllabus 8.1→0.5% · eval P50 6.2s / P95 10.8s · SUS 82 · task success 92%.
