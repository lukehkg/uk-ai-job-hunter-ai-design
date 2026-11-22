# UK AI Job Hunter — AI System Design (Public Showcase)

> The open design companion to **UK AI Job Hunter** — a self-improving,
> privacy-first job-search platform for the UK market. This repo shares
> **how the AI is designed**: architecture, data flows, the teacher→student
> learning loop, and measured results. The production code and data stay
> private; what's documented here is the design thinking.

**Live product:** [jobs.ai-daily.uk](https://jobs.ai-daily.uk)

## Why this exists

Most job boards rank by keyword echo. This platform treats job search as a
**continuous learning problem**: every daily crawl, every dedup decision,
and every user match produces training signal — quality-gated, PII-scrubbed,
and privacy-enforced — that feeds a family of small, cheap models instead of
putting a large-model call on every search.

## The design in one paragraph

A GitHub-Actions pipeline collects ~2,000–3,000 UK job postings daily from
multiple sources (commercial job-board APIs, public ATS feeds, and open web
scraping of major employment platforms — deliberately unnamed here),
deduplicates them (exact keys + 768-dim embedding cosine ≥ 0.88), filters
to the UK, and screens for ghost/spam listings. Every finalized job
is auto-labelled into schema-2.0 training shards by a **tiered teacher
cascade** — a locally-served DistilBERT tagger first (free), with a larger
frontier-class teacher model (served through an OpenAI-compatible gateway
API, vendor unnamed) verifying only the low-confidence
slice (~$2 for the whole backlog). Nightly compaction dedupes, quality-gates,
and publishes leakage-safe grouped splits as Parquet. From that corpus a
276-label job-tag classifier (**F1 0.888 vs 0.575 frequency baseline**) and a
RAG trust scorer (5 risk flags + 0–100 score) were already trained; a student
model distills the teacher next, and promotes itself only by beating the
teacher on held-out agreement.

## What's in this repo

| Path | What you'll find |
|---|---|
| [`docs/01-system-diagram.md`](docs/01-system-diagram.md) | Component diagram — every live service as it runs today |
| [`docs/02-data-flow.md`](docs/02-data-flow.md) | The five data flows, with measured volumes |
| [`docs/03-solution-architecture.md`](docs/03-solution-architecture.md) | Six-layer architecture + the three model tracks |
| [`docs/teacher-student-loop.md`](docs/teacher-student-loop.md) | ⭐ The tiered teacher→student design: cascade, economics, quality gates, promotion criteria |
| [`models/model-card-c1-jobtag.md`](models/model-card-c1-jobtag.md) | Model card — 276-label job-tag classifier (F1 0.888) |
| [`models/model-card-trust-scorer.md`](models/model-card-trust-scorer.md) | Model card — RAG trust scorer (scam/ghost/harvest flags) |
| [`docs/roadmap.md`](docs/roadmap.md) | What's built, what's next, and why |

## Highlights worth reading

- **Token thrift by design** — the whole system avoids per-search LLM calls:
  dedup is embedding-cosine, tagging is a 67M-param local model, and the large
  teacher only sees the ~10–20% of jobs the cheap model was unsure about.
- **Privacy enforced in code, not policy** — uploads refuse to proceed unless
  the storage API confirms the destination repo is private; PII (emails,
  phones) is scrubbed from every field that enters the training corpus.
- **Leakage-safe splits** — grouped splits keyed on normalized
  title+company, so the same job can never appear in both train and test.
- **Self-promotion gate** — the student only replaces the teacher if it beats
  the teacher's agreement rate on held-out data; otherwise the teacher stays.

## Status snapshot (2026-11-22)

| Metric | Value |
|---|---|
| Nightly pipeline | green 8 consecutive days (GitHub Actions verified) |
| Training corpus | 128,627 gated rows (12.9× the 10k minimum), 69 daily shards |
| C1 tag classifier | F1 **0.888** vs 0.575 baseline (500-row held-out eval) |
| Trust scorer | live, RAG + strict-JSON teacher, labels accumulating for distillation |
| Privacy | all storage repos private, enforced at upload time |

## Related

- Production app: [jobs.ai-daily.uk](https://jobs.ai-daily.uk)
- Implementation repo: `uklukie/uk-ai-job-hunter-dev` (private)

## License

Documentation and diagrams: [CC BY 4.0](LICENSE) — share and adapt with
attribution. No source code, data, or credentials are included in this repo.
