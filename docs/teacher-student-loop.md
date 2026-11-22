# Teacher → Student Learning Loop (the core AI design)

The platform is built around one idea: **real job-search traffic should make
the system smarter, without paying large-model prices on every request.**

## The tiered teacher cascade

Every job entering the training corpus is labelled by a cascade, cheapest
first:

```
Tier 1   Local DistilBERT batch inference        $0   labels ~100% of jobs
              │ only the LOW-CONFIDENCE slice (~10–20%) continues
              ▼
Tier 2   Frontier-class LLM teacher            ~$2 per full low-conf pass
         (served via an OpenAI-compatible
          gateway API; vendor unnamed)
         one structured-output call per job:
           { tags[≤5], is_scam, is_agency, confidence }
              │ quota guard: abort if >80% of gateway credits used
              ▼
Tier 3   The STUDENT (DistilBERT 67M)
         retrained on Tier-2-verified labels; promotes itself only if it
         beats the teacher's agreement rate on held-out data
```

Design rules that make this work:

1. **Duplicates never touch an LLM.** Dedup runs on content hashes and
   embedding cosine similarity first — only genuinely new jobs are labelled.
2. **The token-savings contract is test-enforced.** The cascade asserts the
   large model is called *only* for rows the cheap model left untagged
   (`call_count == untagged_row_count` in the test suite).
3. **Failures degrade, never break.** If the teacher is unavailable (quota,
   network, malformed JSON), the pipeline continues with the cheap labels —
   the hot path is byte-identical whether the flag is on or off.
4. **The teacher's share shrinks every cycle.** Each retrained student
   absorbs more of the labelling; large-model spend trends toward zero.

## Quality gates before anything becomes training data

- **Content-hash dedup** — one row per logical job (normalized title +
  company + description fingerprint).
- **Label-conflict detection** — the same job labelled differently across
  batches is surfaced, not silently averaged.
- **Risk screening** — ghost-job heuristics, spam scoring, short-description
  and no-skills flags drop the row entirely.
- **PII scrub at the gate** — emails and phone numbers are replaced with
  `[email]` / `[phone]` placeholders in description, title, and company
  fields *before* any row can be published.
- **Privacy-enforced uploads** — the upload path refuses to run unless the
  storage API confirms the destination repo is `private=True` (fail-closed:
  missing token, network error, or an explicit `private=false` all block
  the upload).

## Leakage-safe evaluation

Grouped splits are keyed on the normalized **title + company** pair, with a
secondary fingerprint over the normalized description. One logical job can
never appear in both train and test — the metric you see is the metric a
fresh job would get.

## The economics

| Step | Cost | Time |
|---|---|---|
| Tier-1 labelling (local CPU batch) | $0 | runs inside the nightly compaction |
| 100-job pilot (teacher vs cheap-model agreement) | ~$0.01 | 1 day |
| Full low-confidence re-label (~470k-row corpus, 10–20% slice) | ~$2 | 1–2 days |
| Student retrain + automatic promotion evaluation | $0 (Pro credits) | nightly check |
| **Total to a self-improving system** | **~$2.50** | **~5–6 working days** |

For comparison: labelling the full corpus with a large model was quoted at
~282M tokens (~$13) and would blow the token budget for ~90% of the same
benefit. Tiering is the whole point.

## Current status (2026-11-22)

- Tier 1: live and verified inside nightly compaction (weights load, tags produced, $0).
- Tier 2: implemented behind a feature flag, quota-guarded, with an offline
  test suite covering the cascade contract.
- Tier 3: student trained once (F1 0.888 vs 0.575 baseline); retrain on
  Tier-2-verified labels is the next milestone, with promotion gated on
  beating teacher agreement on held-out data.
