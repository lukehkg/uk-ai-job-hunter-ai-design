# How I built an AI that detects scam & fake jobs — the full design

> A public build log + design doc for **UK AI Job Hunter**: a self-improving
> job-search platform whose AI learns to spot scam, fake, and ghost job
> postings from real traffic. This repo shares **how it was designed, what
> it cost, how long it took, and how you can copy the recipe** — no source
> code, data, or credentials included.

**Live product:** [jobs.ai-daily.uk](https://jobs.ai-daily.uk)

## The story in 60 seconds

I wanted a job board that didn't just *list* jobs but **judged** them —
because the biggest time-killer for job seekers isn't finding listings,
it's wading into scam, fake, and ghost postings. So I built a platform
that collects ~2,000–3,000 UK postings daily from multiple sources
(commercial job-board APIs, public ATS feeds, and web scraping — vendors
deliberately unnamed), and runs every listing through a **layered
scam-detection system** ending in a retrieval-augmented (RAG) trust scorer
that outputs 5 risk flags and a 0–100 score with cited evidence.

Building the detector was the easy-sounding part. The hard lessons were
operational: an inference endpoint that 400'd on every request, a training
set that silently stopped growing, token budgets that die if you call a
large model on every row. The fixes — local batch inference, a tiered
teacher cascade, append-only shards — are documented here in full.

## What it cost & how long it took (the honest ledger)

| Item | Cost | Time |
|---|---|---|
| Platform subscription (model hosting + Spaces) | ~$9/month | ongoing |
| Tag-classifier training (local CPU, 67M-param model) | **$0** | ~1 day |
| Scam/ghost/spam rule screening | **$0** | built into the pipeline |
| RAG trust scorer (retrieval + teacher prompts) | **$0** to run the retrieval | ~3–5 days to build |
| Teacher verification pilot (100 jobs) | **~$0.01** | 1 day |
| Full low-confidence re-label (10–20% of ~470k rows) | **~$2** | 1–2 days |
| Inference endpoint (avoided — replaced by local batch) | $0 (saved ~$0.10–0.30/h) | — |
| **Total build: ~3 months solo, part-time, ~1,600 commits** | **≈ $30 all-in** | see the [build recipe](docs/build-it-yourself.md) |

The trick that made this cheap: **never put a large-model call on the hot
path.** A small local model labels everything; a frontier-class teacher
(served through an OpenAI-compatible gateway, vendor unnamed) verifies only
the ~10–20% the small model was unsure about. Same quality signal, ~90%
less spend.

## Start here

| Read | If you want to know… |
|---|---|
| [`docs/scam-detection.md`](docs/scam-detection.md) | ⭐ **How the scam/fake-job detection actually works** — 4 layers, RAG retrieval design, strict-JSON verdicts |
| [`docs/teacher-student-loop.md`](docs/teacher-student-loop.md) | How the AI keeps getting better for ~$2.50 — the tiered teacher→student cascade |
| [`docs/build-it-yourself.md`](docs/build-it-yourself.md) | 🛠 **Copy the recipe** — 10 build steps with time + cost per step, and the 7 lessons I learned the hard way |
| [`models/model-card-c1-jobtag.md`](models/model-card-c1-jobtag.md) | The tag classifier: F1 0.888 vs 0.575 baseline, 276 labels |
| [`models/model-card-trust-scorer.md`](models/model-card-trust-scorer.md) | The trust scorer: 5 flags, 0–100 score, evidence citations |
| [`docs/01-system-diagram.md`](docs/01-system-diagram.md) · [`02-data-flow.md`](docs/02-data-flow.md) · [`03-solution-architecture.md`](docs/03-solution-architecture.md) | The full system, layer by layer |
| [`docs/roadmap.md`](docs/roadmap.md) | What's shipped, what's next |

## Status snapshot (2026-11-22)

| Metric | Value |
|---|---|
| Nightly pipeline | green 8 consecutive days (GitHub Actions verified) |
| Training corpus | 128,627 gated rows (12.9× the 10k minimum), 69 daily shards |
| Tag classifier | F1 **0.888** vs 0.575 baseline (500-row held-out eval) |
| Trust scorer | live — RAG + strict-JSON teacher; labels accumulating for a student distillation |
| Privacy | all storage private, enforced in code at upload time; PII scrubbed from every training field |

## Can I copy this?

**Yes — that's the point of this repo.** [`docs/build-it-yourself.md`](docs/build-it-yourself.md)
is written as a recipe: the ten build steps in order, what each costs, how
long each takes, and the mistakes to skip. The production implementation
stays private, but every design decision in it is documented here.

## Related

- Implementation repo: `uklukie/uk-ai-job-hunter-dev` (private)

## License

Documentation and diagrams: [CC BY 4.0](LICENSE) — share and adapt with
attribution. No source code, data, or credentials are included in this repo.

