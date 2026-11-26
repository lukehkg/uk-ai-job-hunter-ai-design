# 5 — High-Level Concept (non-technical story)

## What we want to do

Help UK job seekers find real, safe job listings — without being flooded by scams, fake postings, or “ghost” jobs that exist only to collect CVs.

## What the system does (high-level story)

1. **Collect** — Every day (about 06:00 UTC) the system pulls fresh job postings from a few commercial APIs, a web scraper, and public ATS feeds (Greenhouse, Lever, Ashby, Workable, SmartRecruiters). Roughly 2 000–3 000 raw rows land each day.

2. **Dedupe & screen** — Exact duplicates are dropped. Then a cheap AI model checks if two postings are essentially the same (cosine similarity ≥ 0.88). A UK‑location filter removes about 16 % that aren’t UK‑focused. Each row is run through a risk screen that flags ghost jobs, spam, and resume‑harvest patterns. Personal emails and phone numbers are scrubbed and replaced with placeholders (`[email]`, `[phone]`) **before** anything is stored.

3. **Index** — The clean rows are turned into a fast searchable index (SQLite full‑text + vector embeddings). This lets the front page answer a query in a sub‑second — no re‑scraping needed.

4. **Serve** — The React front‑end reads the exported JSONL files directly. The user sees a landing strip with sector categories, a CV‑match area, and results with **trust badges** that tell them how reliable each listing is.

5. **Trust score (RAG)** — For every listing the system:
   - Embeds the job text (cheap local model).
   - Retrieves the top‑10 most similar real jobs from its own archive (FTS5 + vector dupes).
   - Sends one structured call to a “teacher” LLM (via an OpenAI‑compatible gateway) with a prompt that **must** cite the retrieved evidence.
   - The teacher returns a strict JSON verdict: 5 risk flags, a 0‑100 confidence score, and the evidence citations.
   - If the teacher is unavailable, a cheap fallback scorer kicks in.
   - The verdict becomes a trust badge on the job card and is also saved to `trust_labels.jsonl` for later AI learning.

6. **AI learns in tiers (teacher → student)** — This is where the system gets smarter without costing a fortune:
   - **Tier‑1** (cheapest): a local DistilBERT model labels every job for free. Only the low‑confidence slice (~10‑20 %) moves on.
   - **Tier‑2** (teacher, ~$2 per full pass): a larger LLM (frontier model via gateway) reviews only those uncertain slices and produces the structured verdicts described above.
   - **Tier‑3** (student, $0): a second DistilBERT is retrained on the Tier‑2‑verified labels. It promotes itself **only if** it beats the teacher’s agreement rate on held‑out data.
   - Total cost to go from “no AI” to a self‑improving system: **≈ $2.50**.

7. **Privacy & data protection (high‑level)**:
   - **PII scrubbing** happens at the gate — emails/phones are replaced before any row is stored.
   - **Fail‑closed uploads**: every upload to the Hugging Face repos refuses to run unless the destination repo is confirmed `private=True`. Missing token, network error, or an explicit `private=false` all block the upload.
   - The three HF repos (`pro-data`, `dev-autotrain`, `autotrain-models`) are all **private**; no public exposure.
   - The live Space uses a passcode; only the owner can trigger deploys or training.
   - Rate limits and token‑budget guards prevent runaway LLM calls.

## How the AI (RAG) runs — step‑by‑step (concept)

```
Job text → embed (local model) → retrieve top‑10 similar real jobs from archive
⬇
Assemble a “RAG context block” (max 10 chunks + facts about duplicates)
⬇
Send ONE structured call to the teacher LLM:
   “Using ONLY this context, give me 5 risk flags, a 0‑100 score, and cite each fact.”
⬇
Teacher returns strict JSON → trust badge on job card → save label for later learning
⬇
If teacher is down → cheap keyword fallback → still shows a badge (lower confidence)
```

The key point: **the LLM never guesses from memory**; it always reasons from retrieved real‑job evidence. That’s what makes the trust score auditable and hard to fake.

## How the AI learns (economics)

| Tier | Model | Cost per full run | What it does |
|------|-------|-------------------|--------------|
| 1 | Local DistilBERT (CPU batch) | $0 | Labels ~100 % of jobs; only unsure slices continue |
| 2 | Teacher LLM (frontier, gateway) | ~$2 | Verifies the uncertain slice; returns 5 flags + score + evidence |
| 3 | Student DistilBERT (67 M) | $0 (Pro credits) | Retrains on verified labels; promotes if it beats teacher agreement |

**Total to a self‑improving system: about $2.50** — compared with ~$13 if the full corpus were labelled with a large model from the start.

## Privacy & data‑protection checklist (what you don’t see)

- ✅ Emails/phones scrubbed to `[email]` / `[phone]` before anything is persisted
- ✅ Every upload to HF repos checks `private=True`; blocks if missing/false
- ✅ Three private repos only — jobs, training shards, model artifacts
- ✅ Live Space behind passcode; only the owner can deploy or trigger training
- ✅ LLM calls guarded by quota; abort if >80 % of credits used
- ✅ No raw user data leaves the private environment

## Bottom line for a non‑technical user

- You land on a clean page with job listings, sector tags, and a **trust badge** on each card.
- The badge tells you “this job has been checked — here’s why it’s safe (or not)”.
- Behind the scenes the system learns from real job data, gets a little smarter each day, and keeps your personal data private by design.
- The whole AI pipeline costs roughly the price of a cup of coffee (~$2.50) to make the system noticeably better over time.

---
*Related docs: `docs/01-system-diagram.md` (high‑level architecture diagram) · `docs/02-data-flow.md` (byte‑by‑byte flow) · `docs/03-solution-architecture.md` (layered architecture) · `docs/teacher-student-loop.md` (AI‑learning economics).*