# Roadmap — what's built, what's next

## Shipped

| Milestone | Evidence |
|---|---|
| Daily multi-source collection → dedup → UK filter → risk screen | nightly GitHub Actions run, green 8 consecutive days (verified 2026-11-22) |
| Corpus-first warm search (SQLite FTS5 + persisted embeddings) | 0.7 ms warm / 3.3 ms cold vs 5–15 s network path |
| Append-only training shards → nightly compaction → grouped splits → Parquet | 69 daily shards; 128,627-row train split; 12.9× the 10k viability gate |
| C1 tag classifier trained + promoted | F1 0.888 vs 0.575 baseline (see model card) |
| RAG trust scorer live | 5 flags + 0–100 score, strict-JSON teacher |
| Privacy enforced in code | fail-closed private-repo check on every upload; PII scrub across description/title/company |
| Frontend tag rendering | teacher labels surface directly in the results UI |

## Next (in order)

1. **Merge the Tier-2 cascade** (currently on a feature branch, feature-flag
   off — the hot path is byte-identical until flipped).
2. **100-job pilot** (~$0.01): measure Tier-1 vs Tier-2 agreement rate and
   cost per job — the number that decides everything downstream.
3. **First low-confidence re-label** (~$2): the Tier-2 LLM teacher verifies
   the ~10–20% slice the cheap model was unsure about.
4. **Student retrain on verified labels** → the nightly monitor evaluates
   `student_promotable` → the student takes over the serving slot.
5. **Phase B serving**: scale-to-zero inference endpoint for the student
   (on-demand only, $0 when idle).

## Later

- **E1 embedder scale-up** — the fine-tuned all-mpnet embedder is paused at
  smoke (recall@5 0.100 vs 0.175 baseline); anchor audit + 20k-pair scale-up
  queued before retry.
- **Trust-score student distillation** — once ~1,000 scored labels
  accumulate, distill the RAG teacher into a local model (Step C).
- **F9 assistant** — hosted-LLM job-search assistant with corpus RAG.
- **Per-sector collection rebalance** — tune daily category budgets by what
  the catalog strip actually shows.

## Design principles this roadmap follows

1. Small local models first; large models only for verification slices.
2. Every label is append-only and schema-versioned — history is never
   rewritten, so training data is reproducible.
3. Every model must *beat its teacher* on held-out agreement before it
   serves — promotion is earned, not scheduled.
4. Privacy is a code gate, not a policy paragraph.
