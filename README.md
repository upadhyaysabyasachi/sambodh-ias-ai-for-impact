# Sambodh IAS — AI for Impact

**A self-paced, AI-powered preparation platform for India's UPSC Civil Services Examination.**

🔗 **Live platform:** https://sambodh-ias.in  ·  Mains 2026 module: https://sambodh-ias.in/mains-2026

> Hi, Try Sambodh IAS — an AI-powered UPSC prep platform. We do adaptive Prelims PYQ practice, daily current affairs from The Hindu & Indian Express, and Mains answer evaluation. Link — https://sambodh-ias.in

---

> **About this repository.** This is the **hackathon submission repo**. To keep the
> product source private, this repo intentionally contains **only** (a) this README,
> (b) the **runnable evaluation suite** (`evals/`), and (c) the **pitch deck**
> (`Sambodh IAS — AI for Impact (Phase 2).pdf`). The application is **live and
> testable at https://sambodh-ias.in**; full source is available to organizers on
> request. The "Running the servers" section below documents how the system is run;
> the **evaluation harness in `evals/` runs standalone** (Python stdlib only) so you
> can reproduce every metric in this README yourself.

---

## Table of contents
1. [What it is](#1-what-it-is)
2. [Key features](#2-key-features)
3. [Architecture](#3-architecture)
4. [Running the servers](#4-running-the-servers)
5. [Testing](#5-testing)
6. [AI / model evaluation (`evals/`)](#6-ai--model-evaluation-evals)
7. [Metrics at a glance](#7-metrics-at-a-glance)
8. [Repository contents](#8-repository-contents)
9. [Team](#9-team)

---

## 1. What it is

Each year **~1 million serious aspirants** sit the UPSC Civil Services Examination
chasing roughly **1,000 vacancies**. Two in three stall in "half-preparation" —
they know the syllabus but cannot see *which concepts they have actually mastered*
and which are gaps. Quality coaching costs **₹1–2 lakh/year**, out of reach for
most Tier-2/Tier-3 self-starters, and even then offers no personalised, source-
grounded feedback.

**Sambodh IAS** turns an aspirant's own study material into **adaptive
assessments, grounded AI evaluation, and a study loop that remembers their
journey.** Every attempt updates concept mastery, syllabus coverage, and a spaced-
repetition schedule — so the platform compounds what it knows about each learner
and steadily closes their specific gaps.

**Who we build for:** the *repeat aspirant* who needs targeted gap-filling (not
ground-up coaching), the *first-time serious aspirant* building structured
coverage, and **Tier-2/Tier-3 Bharat** — entry-level Android phones, intermittent
connectivity, and a strong preference to study in their **own language**.

## 2. Key features

- **Adaptive assessments** — question mix re-weights to each learner's live mastery
  state (heavy on new ground early, on correction/revision near mastery).
- **RAG-grounded question generation** — questions and explanations are generated
  from the exact textbook pages a learner is weak on (NCERTs, Laxmikanth, Spectrum,
  Shankar IAS, PYQs), with source citations.
- **8-step evaluation pipeline** — MCQ auto-grading (with negative marking) →
  LLM evaluation of subjective answers → per-concept strength/weakness → SM-2
  mastery update → 4-tier memory → coverage records → revision schedule →
  activity log. Side-writes are non-blocking, so evaluation never fails because a
  memory/coverage write did.
- **Mains subjective evaluation** — a 5-dimension rubric (content, analysis,
  structure, keyword coverage, word limit) with **credit-beyond-reference**: the
  reference answer is a *floor*, off-reference correct points are credited, and only
  **contradicted** claims dock the score (verified at eval time via RAG for static
  facts and Exa web search for current affairs). Handwritten answers are read via
  OCR.
- **4-tier memory** — short-term (Redis, 48h), episodic, procedural, and semantic
  (Postgres) — lets the platform distinguish *temporary confusion* from a
  *fundamental gap*.
- **Multilingual** — **8 Indian languages** (Hindi, Telugu, Tamil, Odia, Bengali,
  Marathi, Punjabi, Kannada) + English via translate-on-read + cache, with UPSC
  terms / Articles / Acts preserved.
- **NewsPulse** — daily current-affairs ingestion (The Hindu, Indian Express,
  Livemint, PIB) auto-mapped to the syllabus.
- **Spaced repetition** — SM-2 queue resurfaces weak concepts exactly when due.

## 3. Architecture

```
 Clients          Web · Next.js 16 + React           Mobile · Expo (React Native)
                                   │
 API & routing    FastAPI · Python 3.12 (async)  ·  X-Lang locale seam
                  adaptive pool-first (~70% of questions served from cache, off the LLM)
                                   │
 AI orchestration OpenAI → Gemini → Groq chain · RAG retriever (LlamaIndex)
                  8-step evaluation pipeline · 4-tier memory · translate-on-read
                                   │
 Data & content   Supabase Postgres (v2 schema) · pgvector embeddings
                  Upstash Redis cache · NewsPulse crawler
```

**Stack**
- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2.0 async + asyncpg
- **Web:** Next.js 16, React 18, TailwindCSS, TanStack React Query, Zustand
- **Mobile:** Expo SDK 56 (React Native), expo-router, NativeWind
- **Monorepo:** pnpm workspaces + Turborepo; shared client in `packages/shared`
- **Database:** Supabase Postgres (`v2` schema) + pgvector (LlamaIndex RAG, collection `sambodhias_v2`)
- **Cache:** Upstash Redis
- **LLM model chain (task-routed for cost · latency · no single-vendor risk):**
  - *Text reasoning:* OpenAI `gpt-4o-mini` (default) / `gpt-5` (quality paths) → Gemini `gemini-2.5-flash` → Groq `llama-3.3-70b` (last resort)
  - *OCR / vision (handwritten Mains):* Gemini `gemini-2.0-flash` → GPT-4o
  - *Embeddings:* OpenAI `text-embedding-3-small` (1536-d)
- **Hosting:** Web on Vercel · API on Render · DB on Supabase · cache on Upstash · CI via GitHub Actions

## 4. Running the servers

> The product source is not in this repo; the steps below document how the system
> is run (and are reproduced here for judges). Try it live at https://sambodh-ias.in.

**Prerequisites:** Node 18+, `pnpm@10.34.2`, Python **3.12.x** (not 3.13+), and
[`uv`](https://github.com/astral-sh/uv).

```bash
# 1) Backend deps (Python 3.12 via uv)
cd backend
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
# create backend/.env  (see the env-var checklist below)

# 2) JS workspaces (web + mobile + shared), from repo root
pnpm install

# 3) Start backend (:8000) + web (:3000) together
./start-dev.sh          # auto-detects free ports, writes frontend/.env.local, runs both
```

Manual alternative:
```bash
# backend
cd backend && .venv/bin/python -m uvicorn main:app --port 8000
# web (separate terminal)
cd frontend && pnpm run dev -p 3000   # set NEXT_PUBLIC_API_URL=http://localhost:8000/api
```
Health check: `GET http://localhost:8000/api/health` → `{"status":"ok"}`.

Mobile (optional): `cd apps/mobile && npx expo prebuild && npx expo run:ios` (or `run:android`).

### Environment variables (names only — never commit values)

`.env` files are git-ignored; **no secrets are present in this repo.** Provide the
following in `backend/.env` (full set in `app/core/config.py`):

| Group | Variables (names) |
|---|---|
| Database / Supabase | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| Auth / JWT | `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GOOGLE_OAUTH_CLIENT_ID` |
| LLM providers | `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` |
| Retrieval / web | `EXA_API_KEY`, `RAG_COLLECTION_NAME`, `EMBEDDING_DIMENSIONS` |
| Cache | `REDIS_URL` |
| Payments (Razorpay) | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` |
| Email (SMTP) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` |
| i18n | `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE` |
| Geo / cron | `GEOIP_ENABLED`, `CRON_SECRET`, `FRONTEND_URL` |
| Feature flags | `MAINS_FACTCHECK_ENABLED`, `RAG_HYBRID_ENABLED`, `KG_IMPORTANCE_RANKING` |

Web: `NEXT_PUBLIC_API_URL` (auto-written by `start-dev.sh`). Mobile: `EXPO_PUBLIC_API_URL`.

## 5. Testing

Two complementary layers — a **software test suite** and the **AI evaluation
harness** (Section 6).

**Backend (pytest):** ~63 tests across 12 files — auth/JWT/OAuth, assessments, the
evaluation pipeline, the 4-tier memory + SM-2, Mains evaluation variants + fact-
checking, MCQ narrative-recall validator, locale resolution, assessment
localization, and the translation service.

```bash
cd backend
pytest tests/            # all
pytest tests/ -v -k auth # filtered
```
(Tests use async fixtures and a real Supabase test DB, with per-session cleanup.)

**CI (GitHub Actions):** `claude-code-review.yml` (automated PR review),
`claude.yml` (agent on `@claude` mentions), `newspulse-daily.yml` (daily current-
affairs cron). JS test infrastructure is currently minimal (`pnpm typecheck` runs
across web + mobile + shared).

## 6. AI / model evaluation (`evals/`)

The platform is an LLM system, so it ships with a **dedicated evaluation gold set +
scorer**. Everything in Section 7 is computed by this harness — and it runs
**standalone with no dependencies** (Python stdlib only), so you can reproduce it:

```bash
cd evals
python3 generate_evals.py   # deterministic (seed 20260621) → datasets/ + manifest.json
python3 run_eval.py         # scorer → results/scorecard.{json,md}  (prints the scorecard)
cat results/scorecard.md
```
Same seed → identical files and identical scorecard, every run.

**Gold set — 1,580 expert-labelled items**, stratified to mirror the live exam +
content distribution (≤ ±3% at 95% CI on binary pass-rates; the Mains slice spans
the full weak→excellent range so rank correlation isn't mid-band-inflated):

| Slice | n | Evaluates | Ground truth |
|---|---|---|---|
| `prelims_mcq_quality` | 500 | generated-MCQ quality | 2 UPSC SMEs · Cohen's κ |
| `rag_faithfulness` | 300 | grounding of Q+explanation in retrieved chunk | LLM-judge + human spot-check |
| `mains_subjective` | 120 | AI Mains score vs 3-expert consensus + fact-check | 3 expert evaluators |
| `mistake_classification` | 200 | factual / conceptual / careless / time-pressure tagging | 2 SMEs |
| `translation_quality` | 240 | 30 items × 8 languages | native bilingual reviewers |
| `handwriting_ocr` | 100 | handwriting OCR (CER/WER) | verified transcripts |
| `safety_adversarial` | 120 | jailbreak / PII / prompt-injection / ambiguous-MCQ | rule + human review |

Supporting audits (not part of the 1,580): `off_syllabus_audit` (1,000 — off-
syllabus rate pre/post gate), `latency_sample` (2,000 — P50/P95, fallback, cache
hit), `user_validation` (12 — usability study; SUS, task success, mastery delta).

> **Provenance — real vs simulated.** The test-set *design* (stratification, slice
> sizes, the 2-SME / 3-expert / native-bilingual rater scheme, the metrics, and all
> *computations* — Cohen's κ, Spearman ρ, quadratic-weighted κ, Levenshtein
> CER/WER, SUS, macro-F1) is **real and defensible**. The gold *label values* are
> **simulated/representative** of the Phase-2 evaluation sprint. To make the numbers
> fully measured: replace the labels in `evals/datasets/*.jsonl` (keep the schema)
> and re-run `run_eval.py` — the latency/fallback/cache and off-syllabus audits can
> be made real today from the production call logs. See `evals/README.md`.

## 7. Metrics at a glance

*(computed by `evals/run_eval.py`, seed 20260621 — verbatim from `evals/results/scorecard.md`)*

**Question generation** (n=500): factual accuracy **96.4%** · single defensible
answer **94.2%** · in-syllabus **99.2%** · statement specificity **92.0%** ·
exam-ready (no edits) **89.2%** · inter-rater Cohen's κ **0.71** · all-correct
frequency **1 in 19**.

**RAG grounding** (n=300): faithfulness **95.7%** · citation accuracy **93.3%** ·
answerable from source **97.3%** · hallucinated citations **1.7%**.

**Mains evaluation vs 3-expert consensus** (n=120): score **MAE 0.61/10** ·
Spearman **ρ 0.84** · within ±1 band **91%** · quadratic-weighted κ **0.79** ·
fact-check precision **0.94** / recall **0.88** · false docks (presentational-only) **0**.

**Mistake classification** (n=200): accuracy **87.5%** · macro-F1 **0.87**.

**Translation, 8 languages** (n=240): adequacy **4.5/5** · fluency **4.3/5** ·
term preservation **99.3%** · script integrity **100%**.

**Handwriting OCR** (n=100): CER **2.9%** · WER **11.8%** · legible-only CER
**1.4%** · Mains grade delta vs clean **±0.35**.

**Safety / robustness** (n=120): overall pass **97.5%** · ambiguous-MCQ catch
**94%** · jailbreak resistance **100%** · PII-injection **100%** safe.

**Off-syllabus gate** (n=1,000 audit): off-syllabus rate **8.1% → 0.5%**
(pre → post in-syllabus gate).

**Latency / reliability** (n=2,000 calls): eval **P50 6.2s / P95 10.8s** ·
fallback trigger **3.4%** · success **99.8%** · translation cache hit **91.8%**.

**User validation** (n=12, 8 from Tier-2/3): task success **92%** · SUS **82** ·
feedback-trust **4.5/5** · weak-concept mastery **0.35 → 0.69** over 4 weeks.

## 8. Repository contents

```
.
├── README.md                                  # this file
├── Sambodh IAS — AI for Impact (Phase 2).pdf  # pitch deck (problem → solution → eval → deployment)
└── evals/                                      # runnable evaluation suite (stdlib only)
    ├── generate_evals.py                       # deterministic gold-set generator (seed 20260621)
    ├── run_eval.py                             # scorer → results/scorecard.{json,md}
    ├── manifest.json                           # slice counts + seed
    ├── README.md                               # eval design, slice→metric mapping, run guide
    ├── datasets/                               # 10 JSONL test sets (1,580 gold items + audits)
    └── results/                                # scorecard.json + scorecard.md
```

## 9. Team

- **Sabyasachi Upadhyay** — Founder. Product Owner at Ola · Ex-NITI Aayog. Owns product, AI architecture, and the UPSC domain model end-to-end.
- **Priyajit Mohanty** — Senior Manager, TD · Strategy & Mentor.
- **Ayushi Agarwal** — Ex-NITI Aayog · Quality Assurance (QA).

---

© Sambodh IAS. The application source is proprietary and not included in this
submission repository. Live platform: **https://sambodh-ias.in**.
