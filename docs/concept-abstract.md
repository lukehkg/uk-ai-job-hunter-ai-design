# Conceptual Design — Trust‑Scoring Job Listing System (Abstract)

## What this design describes

An AI system that collects job listings, verifies their authenticity, and provides users with a **trust score** (0‑100) along with risk flags. The core concept is **RAG‑augmented verification** — the system retrieves similar real jobs from its own archive and asks an AI whether this listing is legitimate, before showing it to the user.

This document is intentionally abstract. No specific services, infrastructure, or proprietary implementation details are exposed.

---

## High‑level system flow (conceptual)

```
User (job seeker) → Web app UI → Backend service → AI Trust System → Private storage → Web app UI → User
```

### Step‑by‑step (high level)

1. **Collection** — A daily job feed arrives from several commercial job boards and public ATS feeds. Roughly 2,000–3,000 new listings are processed each day.
- **Tier‑1 (cheap)**: A small, local model labels every job for free. Only the low‑confidence slice (~10‑20%) moves on.
- **Tier‑2 (verifier)**: A larger, more capable model reviews only those uncertain listings and provides structured verdicts. This step costs money because the model has to reason from retrieved evidence.
- **Tier‑3 (student)**: A smaller model is retrained on the Tier‑2‑verified labels. It promotes itself only when it can match or beat Tier‑2’s accuracy on test data.

---

## RAG concept (how verification works, in plain language)

Think of RAG as “use past evidence, don’t guess from memory.”

| Step | What happens |
|------|--------------|
| **Embed** | The job text is converted to a vector that captures its meaning. |
| **Retrieve** | The system looks at its own archive of already‑verified jobs and finds the top‑10 that are most similar. |
| **Context** | These similar real jobs are assembled into a “context block” along with basic facts. |
| **Ask** | The system asks the AI verifier: *"Using ONLY this context, assess this listing."* The verifier cannot access any other information. |
| **Verdict** | The AI returns a structured answer with risk flags, a confidence score, and explicit citations to the retrieved evidence. |
| **Badge** | The user sees a trust badge on the job card, with a brief explanation of why the score is what it is. |

---

## AI learning concept (conceptual economics)
---

## Privacy and data protection (high level)

| What we do | Why it matters |
|------------|----------------|
| Scrub personal contact info before storing | No emails or phone numbers ever exist in the raw system. |
| Private storage only | Data is stored in systems that explicitly require privacy settings. |
| Fail‑closed design | Upload operations refuse to run unless privacy constraints are met. |
| Rate limiting and budget guards | Large‑model calls are monitored to prevent runaway costs. |

---

## Why this design matters

A job seeker shouldn’t have to guess whether a listing is real. This design gives them a concrete signal: **a trust badge with an auditable explanation**. The RAG pattern ensures that every verdict is grounded in evidence, not guesswork. The three‑tier learning pattern makes the system smarter over time at a low ongoing cost.

At a high level, this is a **verification system that uses its own history as evidence, learns continuously, and protects user data** — all without exposing proprietary implementation details.

---

*This document is intentionally generic and abstract. It describes the concept of a job‑listing trust‑scoring RAG system, not a specific implementation or proprietary design.*

The system starts with zero AI knowledge and gradually becomes smarter by labeling real jobs and learning from verified verdicts.

| Tier | What it does | Cost |
|------|--------------|------|
| **Tier‑1** | A cheap local model labels every single job. This costs almost nothing ($0). |
| **Tier‑2** | A more powerful model reviews only the low‑confidence slice that the cheap model was unsure about. This costs money because the model has to read structured evidence and produce structured outputs. |
| **Tier‑3** | After Tier‑2 has done the hard work, a smaller model retrains on those verified labels. It promotes itself only when it can match or beat Tier‑2’s accuracy on test data. |

By the time Tier‑3 is ready to replace Tier‑2, the system has already done the expensive heavy lifting, and future iterations are nearly free.

2. **Deduplication** — The system identifies and removes exact duplicates, then checks for similar listings using a cheap AI model.

3. **Risk screening** — Each listing passes a risk filter that flags potential scams (ghost jobs, spam, CV‑harvesting patterns).

4. **Privacy scrubbing** — Personal contact information (emails, phone numbers) is replaced with generic placeholders before anything is stored.

5. **Indexing** — Clean listings are stored in a searchable index so the front page can respond instantly.

6. **Trust scoring (RAG)** — For every listing:
   - The system creates a “meaning fingerprint” of the job text.
   - It retrieves the top‑10 most similar real jobs from its own archive (using full‑text and vector search).
   - It sends one structured question to an “AI verifier” model.
   - The verifier returns a JSON verdict with flags and scores.
   - A simple fallback rule‑based scorer is used if the AI verifier is unavailable.
   - The verdict becomes a trust badge shown on the job card.

7. **AI learning (teacher → student)** — The system learns in three tiers:
﻿