# Attest

Multimodal, self-grading RAG over SEC filings. Attest ingests a 10-K, answers
plain-English questions with page citations, reads the figures inside the
filing with a vision model rather than skipping them, and grades its own
answers against the same rubric a human reviewer would use — retrieval
precision, faithfulness to the source, and answer relevance — so that when it
cannot ground an answer in the document, it says so instead of inventing one.
The self-grading layer is the product here, not a bolted-on eval script: the
trust dashboard described below renders those numbers live, including the
one that currently fails.

## Architecture

Four services under Docker Compose, plus a profile-gated eval image:

- **`attest_shell`** (Django, published on `:8001`) — the product a user
  touches: signup/login, an ask page, per-user history, a library of owned
  documents, and a trust dashboard. Mints a signed HMAC token on login; every
  downstream call carries it.
- **`attest_engine`** (FastAPI) — retrieval, reranking, the agent loop, and
  the vision call for figures. Publishes no host port; it's reached only
  from inside the Docker network (by `attest_shell`, or with
  `docker compose exec`). Verifies the shell's signed token on every request
  and derives `owner_id` from it — never from the request body — which is
  what makes tenant isolation enforceable rather than advisory.
- **`attest_qdrant`** (`:6333`) — the vector store. One collection,
  `attest_chunks`, holding both dense text embeddings and figure-description
  embeddings for every ingested page.
- **`attest_postgres`** (`:5432`) — two application tables, not just
  Django's own. `AskRecord` is one row per ask attempt — success, refusal,
  or error alike, with `sources`, `tool_calls`, `refused`, and `latency_s` —
  so history and the trust dashboard never have to infer honesty from
  answer text. `Document` is one row per document a user owns; the library
  page reads this table, not Qdrant, so it never depends on a live vector
  query to render.

**Retrieval pipeline:** a query is embedded twice — dense
(`bge-small-en-v1.5`) and sparse (BM25) — fused against Qdrant with
reciprocal rank fusion into a candidate pool, then re-scored by a
cross-encoder (`bge-reranker-base`) before the top chunks reach the agent.

**Where model calls happen:** the agent (`gemini-3.6-flash`) runs inside a
LangGraph tool loop that can call retrieval more than once per question
before answering — this is the dominant cost of every ask, both in latency
and in quota (see Latency below). The offline judge (`gemini-3.5-flash-lite`)
only runs during eval batches, never on a live ask — the trust dashboard
never invents a score for something it hasn't actually judged. A vision call
reads each qualifying figure at ingest time; today's corpus has exactly one
such figure.

**Current corpus:** 304 points across three tenants — `alice`/`aapl_10k`
(285 points: 65 pages, 284 text chunks, 1 figure — the real filing),
`bruno`/`bruno_10k_excerpt` (10 points, synthetic), and
`carla`/`carla_10k_excerpt` (9 points, synthetic).
*(source: `docs/sessions/Attest_Session_20.md`)*

## Success criteria (§02)

Frozen targets, measured against a 12-question gold set (3 of the 12 are
deliberately unanswerable, to test refusal). Every number below is read
directly from the judged eval artifact or the raw latency log — none
carried forward from a prior write-up.

| Metric | Target | Measured | Verdict |
| --- | --- | --- | --- |
| Faithfulness | ≥ 0.90 | **1.000** (n=12) | PASS |
| Retrieval precision | ≥ 0.85 | **0.774** (n=12) | **FAIL** |
| Answer relevance | ≥ 0.85 | **0.979** (n=12) | PASS |
| Hallucination flag | < 0.50 | **0.0** — 0/3 unanswerable questions hallucinated (all 3 correctly refused) | PASS |
| Figure-grounded | ≥ 80% (aspirational) | not attempted — corpus has one qualifying figure | n/a |
| p95 latency | ≤ 8s | **EXCLUDED** — n=7 live asks, every one exceeded 8s (43.5s–196.0s) | **FAIL (excluded)** |

*Sources: faithfulness, retrieval precision, answer relevance, and
hallucination flag from `data/eval/judged_20260831T101752Z.json`
(`summary.faithfulness`, `summary.context_precision`,
`summary.answer_relevancy`, `summary.refusal_rate`). Latency from
`data/eval/latency_samples.json` (7 recorded live-ask samples,
43.464s–195.979s).*

Retrieval precision's known cause: the reranker demotes the correct chunk
below its fusion-pool rank on 2 of the 12 gold rows (both still inside the
top-5 cutoff). A larger reranker recovered +0.0095 on those two rows at
roughly 4x the per-call rerank cost and was reverted as not worth it against
an already-excluded latency budget.

## Latency

None of the 7 recorded live asks came in under the 8s p95 target — the
fastest was 43.464s, the slowest 195.979s
(`data/eval/latency_samples.json`). Splitting where that time actually
goes: retrieval + rerank, measured directly against the same 7 questions
with the deployed reranker, accounts for **4.7%–13.2%** of each ask's total
observed latency (`data/eval/retrieval_timing_20260902T012156Z.json`,
`end_to_end_reconciliation`). The remaining **87–95%** of every ask sits in
the agent's own round-trips to the model provider — not in our retrieval,
reranking, or application code, all three of which have been individually
checked and ruled out as the lever.

That variance is real and current: a single-hop ask observed 2026-09-02 ran
251.648s end to end, against the same question shape that previously
completed in 14.1s — and ran long enough that the shell's own 210s client
timeout abandoned it before the engine finished, discarding a correct answer
that was never shown or persisted. The full phase split — two model
round-trips (96.93s, 146.91s; 243.84s/251.648s = 96.9% of the total) against
7.81s of retrieval and rerank, the latter consistent with the isolated
seven-run baseline above — is recorded in
`docs/sessions/Attest_Session_21.md`, derived from container log timestamps
and the `AskRecord` row the shell wrote on timeout, not carried forward from
memory. It confirms the pattern already measured here (provider round-trips
dominating a small, stable stack-side cost) and is the reason live asks are
switched off for tomorrow's demo (see `DEMO_RUNBOOK.md`). Root cause for the
provider-side variance itself is still not isolated — host contention and a
provider-side penalty remain equally plausible and both require metered
spend to test, which this write-up did not make.

## What is not done, and why

- **Upload.** No upload button exists. `data/corpus` is mounted read-only
  into the engine, ingest's ML dependencies live only in the engine image
  (not the shell's), and — found while timing a real ingest — the vision
  call ingest makes per figure spends `GEMINI_API_KEY` without going
  through the same quota counter the agent uses
  (`engine/app/ingest.py`, `engine/app/quota.py`). A user-facing upload that
  makes an uncounted, uncapped number of paid calls per file isn't
  shippable; a quota ceiling for vision has to land first.
- **Retrieval precision fails its target (0.774 vs 0.85).** Diagnosed, not
  fixed: two gold rows get demoted by the reranker; the fix tried (a bigger
  reranker) cost ~4x the latency for a ~0.01 gain and was reverted.
- **p95 latency is excluded, not narrowly missed.** Every one of 7 timed
  live asks ran past 8 seconds, and the dominant cost is provider round-trip
  time, not our stack. That root cause is still open.
- **The shell can silently lose a slow answer.** The shell's own client
  timeout on the engine call is 210s (`shell/accounts/engine_client.py:8`),
  tighter than gunicorn's 220s worker timeout — so an engine call that runs
  past 210s is abandoned by the shell while the engine keeps computing, and
  that answer is never written to Postgres. Known, not fixed.
- **No OCR path, no failure detection.** `ingest.py` does a bare text
  extraction; a scanned PDF would silently produce ~0 chunks instead of
  erroring. `Document.status` can express `failed`, but nothing produces
  that state yet.
- **The judge key has no spend ceiling.** Unlike the agent key's persisted
  counter, `JUDGE_API_KEY` is protected only by fail-fast-and-resume on 429.
- **Markdown renders raw in the shell.** The engine returns `**bold**`; the
  browser shows the asterisks literally. Cosmetic, known, not fixed.

## Running it

See `DEMO_RUNBOOK.md` for the full cold-start, verification, and
troubleshooting procedure — every command and expected output in it was
copied from a real run, not written from memory.

---
*Author: Manglam Dubey*
