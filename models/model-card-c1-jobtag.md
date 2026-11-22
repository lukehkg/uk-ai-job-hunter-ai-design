# Model Card — C1 Job-Tag Classifier (`c1-jobtag-distilbert-v1`)

## Model details

| | |
|---|---|
| **Architecture** | DistilBERT-base-uncased (66M params) with a multi-label classification head |
| **Labels** | 276 canonical UK tech/job skills (multi-label, up to ~5 predicted per job) |
| **Training data** | 128,627 quality-gated job rows (grouped train/val/test splits — see below) |
| **Held-out eval** | 500 rows, stratified |
| **Metrics** | **F1 0.888** (precision 0.964, recall 0.822) vs frequency baseline F1 0.575 |
| ** avg tags predicted** | 4 per job |
| **Storage** | private model repo (`c1-jobtag-distilbert-v1/`) |

## Training data provenance

- Source: daily UK job collection aggregating commercial job-board APIs, an
  open web scraper covering major employment platforms, and public ATS
  feeds — deduplicated by content hash,
  UK-location filtered, ghost/spam screened.
- Labels: weak supervision from a ~120-skill resume-side vocabulary matched
  against job text (rule: `matched = score ≥ 5 AND ≥1 skill overlap`), with
  negative pairs mined per search batch (same-search low-score rows).
- Splits: grouped by normalized title+company (with a description
  fingerprint) so a listing can never straddle train and test.

## Intended use

- **Primary:** pre-tagging job listings (`predicted_tags`) so users can
  filter and match by skill without waiting on a live model. Runs as a local
  batch inference step inside nightly compaction (~free) or behind an
  inference endpoint.
- **Secondary:** as the Tier-1 model in a teacher→student cascade, flagging
  the low-confidence slice for review by a larger teacher.

## Limitations

- UK-market vocabulary; multi-label F1 measured on the corpus's own label
  distribution — recall on rare labels is weaker than the headline (overall
  recall 0.822).
- Weak-supervision labels inherit the vocabulary's blind spots; the Tier-2
  teacher verification pass exists precisely to correct these.
- English-language UK postings only.

## Ethical considerations

- Trained only on public job-ad text; no resume or personal data enters the
  training corpus (PII scrubbed at the gate; resume identifiers are salted
  HMACs, never reversible).
- Spam/ghost screening is advisory — a flagged listing is demoted, never
  silently deleted, so borderline postings stay auditable.
