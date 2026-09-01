# Attest — Session 15

**[15]: Quota Wall Killed — §02 Table Complete, Context Precision Fails**

---

## Status Board

**Project.** Attest — a multimodal, self-grading RAG system over SEC filings.
Ingests a 10-K, answers plain-English questions with citations, reads figures
via a vision model, and grades its own faithfulness so it can refuse an answer
it cannot ground. Flagship portfolio/interview build. Solo.

**Stack.** Django shell + FastAPI engine + Qdrant + PostgreSQL ·
`bge-small-en-v1.5` dense + BM25 sparse (hybrid RRF) · `bge-reranker-base`
cross-encoder · `gemini-3.6-flash` (agent), `gemini-3.5-flash-lite` (judge) ·
Docker Compose on WSL2/Ubuntu, external SSD (E:), Agastya111.

**Corpus.** Apple FY2025 10-K — 285 points in Qdrant (284 text chunks +
1 figure). 15-pair gold set in `gold_set.py`: 12 answerable, 3 unanswerable.

**Turn state.** Turn 5 (trust/evaluation layer) is substantially complete but
**does not close this session**. Three of four §02 metrics are measured under a
single consistent ruler. The fourth — p95 latency — is blocked on the agent
key's daily ceiling, not on engineering.

**§02 contract vs. measured, n=12 answerable rows, one ruler:**

| Metric | Target | Measured | Verdict |
|---|---|---|---|
| faithfulness | ≥ 0.90 | **1.000** | PASS |
| answer relevancy | ≥ 0.85 | **0.979** | PASS |
| context precision | ≥ 0.85 | **0.774** | **FAIL** |
| hallucination flag | < 0.50 | refusal 3/3 on unanswerable | PASS |
| p95 latency | ≤ 8s | **not measured** — quota-blocked | unknown, likely FAIL by a wide margin |
| figure-grounded | ≥ 80% | not yet measured | aspirational |

**Head of `main`: `54fae60`.** Tree clean, local == `origin/main`, all work in
two places.

**Execution moved to Claude Code this session** — first live use of the
three-tier model from S14. Chat writes briefs with intent and acceptance
criteria; Claude Code reads the repo and decides the how; Manglam gates
anything metered or destructive. It worked. Every metered spend this session
was approved individually and none was wasted.

---

## Supersedes

- **Judge embedder: remote → local.** `gemini-embedding-001` is gone. Answer
  relevancy now embeds with `BAAI/bge-small-en-v1.5` locally, inside the eval
  container, off the mounted HF cache. The judge no longer has any metered
  embedding dependency.
- **§02 latency source: client stopwatch → engine timing.** The blueprint says
  p95 is measured from *engine timing logs*. Those had never been built —
  `main.py` had no instrumentation and the only latency number in the project
  was `harness.py`'s client-side `perf_counter`. `/ask` now times its own
  handler and returns `latency_s`; the harness prefers it.
- **Context precision is no longer "unknown at partial n".** It is measured at
  0.774 across the full answerable set and it **fails the frozen contract**.
  The target does not move. The gap is documented and scheduled.
- **Turn 5's closing condition is now explicit.** Turn 5 closes when the §02
  table is *complete and honest*, not when it is *passing*. A measured failure
  with a diagnosed cause is a closed turn; an unmeasured number is not.

---

## Goal and buckets

**Goal: close Turn 5.** Planned buckets: T5.Q quota wall · T5.W write-merge
fix · T5.R finish rows 4–11 · T5.3 investigate row 3 · T5.J seed JOURNAL.md ·
T5.9 p95 · T5.12 `generate.py`'s fate · T5.C close.

Two buckets emerged that were not planned — **T5.E** (local embedder swap plus
a ruler-refusal guard) and **T5.3b** (stale gold keys in a committed artifact).
Both were consequences of what the earlier buckets found. Two planned buckets
did not start.

---

## What happened

### T5.Q — the quota wall, named

S13 and S14 both died on a 429 that nobody had ever read in full. Free work
first: Claude Code read `judge.py`, pulled the `ragas==0.4.3` wheel from PyPI
and read its provider and metric sources directly, and produced the exact
per-row call inventory — faithfulness 2 calls, answer relevancy 3 calls plus
2 embedding calls, context precision 5 calls (one per retrieved context). Only
answer relevancy touched an embedder.

That reframed the whole problem. The 15 RPM pacing had been designed around the
judge LLM, which was never the constraint. One approved metered row captured
the untruncated error:

```
429 RESOURCE_EXHAUSTED — Quota exceeded for
aiplatform.googleapis.com/global_embed_content_requests_per_minute_per_base_model
with base model: gemini-embedding
```

`judge.py` never configures Vertex anywhere. Embedding calls made with a plain
AI-Studio key were being metered under a Vertex-side quota regardless. The row
died on its *first* embedding call of the session, after only eight embedding
calls had ever been made from this project — so the ceiling is genuinely tiny,
not something we burned through.

### T5.W — the write-merge fix, verified

Carried debt from S14: each judge run rewrote the judged file with only the
rows that run touched, so a partial run could delete rows already paid for.
Fixed before spending anything — the in-memory judged map is now seeded from
the prior file, `flush()` writes after every row, and the 429 tail-fill skips
rows already present instead of stamping `"not attempted"` over them.

Verified against a pre-run backup: rows 0–3 byte-identical after the metered
row ran. The fix and the diagnosis came out of the same single row of spend.

### T5.E — kill the dependency, don't negotiate with it

The obvious fix was not backoff or a quota-increase request. It was to stop
asking Google to do embeddings the machine can do locally for free. The engine
already runs `bge-small-en-v1.5`; the eval container simply had no reason not
to.

- `sentence-transformers==3.3.1` added to `requirements-eval.txt`, matching the
  engine's existing pin exactly.
- `hf_cache` volume mounted to the eval service — it had never been mounted.
  Weights already present (128.4 MB), so no download on rebuild.
- Switched to **RAGAS's own** `HuggingFaceEmbeddings` (capital F — a direct
  `BaseRagasEmbedding` subclass that satisfies `AnswerRelevancy`'s interface
  check natively), not the LangChain one. It imports `sentence_transformers`
  directly and never touches `langchain_community`, so there is no interaction
  with the `0.3.31` pin in either direction. RAGAS also ships a legacy
  lowercase-f `HuggingfaceEmbeddings` that would fail the modern check; the
  distinction was caught in the source, not discovered at runtime.
- Every judged row now records `embed_model`. **A number whose ruler is not
  recorded is not evidence.**

Three proofs demanded before the run, each able to fail: the image builds and
starts; the embedder produces a 384-dim vector with `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` set, which would hard-fail if it needed the network;
and `summarise()` **refuses** to print a mixed-ruler mean. That third check was
run against the genuinely mixed file on disk and correctly printed
`UNCLAIMABLE — mixed/unrecorded embed_model across scored rows: {None: 4}`
instead of the old 0.988.

### T5.R — the complete table

92 calls, 31m54s, no 429. Rows 0–3 got answer relevancy recomputed only
(59–66s each); rows 4–11 ran fresh (195–226s each); rows 12–14 are unanswerable
and cost nothing. All 12 answerable rows carry the same `embed_model`, checked
against the file rather than assumed.

```
faithfulness      1.000   PASS
answer_relevancy  0.979   PASS
context_precision 0.774   FAIL  (target ≥ 0.85)
refusal_rate      3/3
```

Per-row context precision: rows 6 (0.33), 7 (0.50), 8 (0.50) and 3 (0.58) carry
the entire failure. Every one of those four has faithfulness 1.00 and answer
relevancy ≥ 0.98.

### T5.3 — ruler or product?

Verdict: **product.** `ContextPrecisionWithoutReference` is average precision —
it wants the answer-bearing chunk ranked first and penalises every non-relevant
chunk in the returned set regardless of whether it caused harm downstream.

The confirming test cost nothing. Retrieval is entirely local — dense embedder,
BM25, cross-encoder, Qdrant — so the rerank scores that `retrieve.py` computes
and discards were recoverable by replaying the exact queries from the run
artifact:

| Row | Answer-bearing chunk | Its score | Top score in pool | Gap |
|---|---|---|---|---|
| 3 | p33 income statement | 0.949 | 0.997 (p28 SG&A tail, no number) | 0.048 |
| 6 | p35 balance sheet | 0.929 | 0.985 (p36 equity roll-forward) | 0.056 |
| 7 | p33 income statement | 0.624 | 0.664 (p53 segment table) | 0.040 |
| 8 | p29 narrative "$132.4B" | 0.961 | 0.997 (p41 Note-4 intro) | 0.037 |
| 8 | p41 exact-total table | 0.225 | 0.936 (same subquery) | **0.711** |

Three near-misses and one genuine miss. `bge-reranker-base` is consistently
fooled by *other* Apple financial tables and figure-dense prose that resemble
the query lexically without carrying the line item asked for — the equity
roll-forward, deferred-tax and segment tables all outrank the statement that
actually holds the number. Row 8's exact-total chunk is the outlier: buried at
rank 7 of 20 in the RRF pool and never pulled up.

There is one honest ruler characteristic worth stating alongside this, though
it is not an excuse: a *retrieve broadly, let the model choose* architecture
will structurally sit below AP's ceiling even when every answer is correct and
grounded. That is a property of the metric, not a reason to move the target.

**Retrieval was deliberately not fixed this session.** Turn 5's job was to
build a layer that catches defects. It caught one. Fixing it is a Turn 2
deepening pass on the spiral, and starting it at the tail of a session is how
you get a half-built layer.

### T5.3b — a lie in the repo

Two rows in the committed evidence artifact carried gold keys that commit
`91c0336` had corrected weeks earlier. The agent's answers were right against
current gold; the artifact just disagreed with `gold_set.py`.

Root cause, not just symptom: `harness.py::load_previous()` replays a cached
run record verbatim on resume, `answer_key` included, and never re-reads
`GOLD_SET`. The fix in `gold_set.py` was overridden by a cache that outlived
it. Patched the artifact surgically (only that field) rather than regenerating,
since regeneration would have meant re-running the agent and re-judging for no
benefit; confirmed the scores blocks are byte-identical, since none of the
three RAGAS metrics take `answer_key` as an argument. `harness.py` now
re-derives it on every read.

### T5.9 — the honest stop

The blueprint names *engine timing logs* as the measurement source and they had
never existed. Built them. Also built a local quota counter — hooked to
`on_chat_model_start` on the LLM invocation, **not** the `/ask` endpoint,
because a ReAct loop makes those different numbers.

That counter immediately earned itself. One `/ask` is not one API call: it
averages ~2.08 across the 12 gold rows, confirmed exactly by a live calibration
call that registered 2 against the engine's own logs. So the agent key's ~20
calls/day buys roughly **nine or ten `/ask` calls in an entire day** — meaning
n=20 was never achievable in a single day, independent of what had already been
spent.

n≈9 gives no separation between a 95th percentile and "second-worst of nine".
Stopped, as instructed. **A missing number beats a number I cannot defend.**

What is on record anyway: the 12 existing rows range 13.7s–117.7s and the fresh
engine-timed sample came in at 21.3s. Every observation is far above the 8s
target. p95 is very likely to fail by a wide margin — worth knowing before
funding a multi-day run.

Also flagged for later: the harness resume path caches by question text and
would silently replay an old `latency_s` instead of taking a fresh draw, so
multi-day latency accumulation needs either varied questions or a
resume-bypass for latency sampling specifically.

---

## Decisions locked

- Judge embeddings run locally. No metered embedding dependency in the eval
  path, ever again.
- Every judged row records the embedder that produced its answer relevancy, and
  `summarise()` refuses to print a mean across mixed or unrecorded rulers.
- The §02 targets do not move. Context precision fails at 0.774 and the
  response is to fix retrieval, not the contract.
- Latency for §02 is measured engine-side, by the handler itself.
- Agent API spend is counted at the LLM invocation, in a local file the harness
  reads before sizing any run.
- Retrieval ranking is a Turn 2 deepening pass, scheduled, not started.
- Turn 5 closes on a complete and honest table, not a passing one.

---

## Hard-won lessons

**On measurement.**

- *A number whose ruler is not recorded is not evidence.* Provenance is part of
  the measurement, not metadata about it.
- *Make the pipeline refuse.* "The per-row field lets you check it yourself" is
  a footnote, and footnotes lose to pressure. The mixed-mean guard is the whole
  Attest thesis in fifteen lines of code — and the proof that mattered was
  running it against a genuinely broken file and watching it trip.
- *Count API calls, not units of work* — again. It cost us the judge in S13
  (~10 calls per metric) and it reappeared here in a completely different place
  (~2.08 calls per `/ask`). Any ceiling reasoned about in the wrong unit is a
  ceiling you will hit by surprise.
- *A missing number beats a number you cannot defend.* n≈9 dressed up as a p95
  would have been the most dishonest thing in the repo.

**On diagnosis.**

- *Read the source, not the docs.* The exact call counts, the Vertex-side
  metering path, and the capital-F/lowercase-f embedder distinction all came
  out of reading `ragas`'s own code. None of it was in the documentation.
- *Kill the dependency instead of negotiating with it.* Backoff, a different
  remote model, and a quota-increase request were all bets on a table we cannot
  see. Moving the work onto hardware we own removed the failure class.
- *The cheapest confirming test is often free.* The discarded rerank scores
  looked unrecoverable; because retrieval is fully local, replaying the queries
  cost nothing and turned a hypothesis into a table of gaps.

**The pattern, named at last — cached data outliving the fix meant to override
it.** Three instances in this build: the judge write-merge (a partial run
dropped rows scored earlier), the judge embed provenance (a cached score
outlived the embedder that produced it), and the harness gold keys (a cached
run record outlived a gold-set correction). Every resume-from-disk feature in
this codebase needs an explicit statement of which fields are safe to replay
verbatim and which must be re-derived from current source of truth. **Reuse by
default is the bug, not the exception.** Promoted to `CLAUDE.md`.

**Claude's own errors, logged honestly.**

- *I ordered a more expensive run than the evidence justified.* I called for a
  full 12-row re-judge on ruler-consistency grounds. Claude Code correctly
  pushed back: faithfulness and context precision never touched the embedder,
  so their cached values were already produced by an identical ruler. Only
  answer relevancy needed recomputing. 92 calls instead of 120, with ruler
  consistency fully intact. I was wrong; the executor was right; I took its
  call.
- *I designed around a problem that did not exist.* I held the p95 run over a
  cold-start-versus-warm concern. Models load at import time, before Uvicorn
  opens the port — no `/ask` has ever paid that cost. I should have asked it to
  check before building an instruction around my assumption. The hold turned
  out productive for other reasons, but that was luck, not judgement.
- *I delivered a brief in two parts and then patched it with an addendum.*
  Manglam flagged it. Into a window that gets `/clear`ed between buckets, a
  split brief is a real hazard — order is not guaranteed and half a brief is
  worse than none. Promoted to a standing rule.

---

## Next session

**Open, in order:**

1. **Turn 5 close-out** — `JOURNAL.md` seeded from `docs/sessions/` (T5.J), and
   `generate.py`'s fate decided (T5.12). Both free, both small, neither started.
2. **p95, funded properly.** Decide whether to spend a full day's agent ceiling
   on a multi-day accumulation, and handle the harness resume path first — it
   would replay cached latencies and silently defeat the sampling.
3. **Then Turn 5 closes** on a complete table, with context precision recorded
   as a measured, diagnosed failure.

**Then, Turn 2 deepening pass — retrieval ranking.** The diagnosis is already
written: three near-misses at the reranker (gaps 0.037–0.056) and one genuine
retrieval miss (row 8, gap 0.711, rank 7 of 20 in the fusion pool). Likely
levers are a stronger reranker, tightening `k`, and chunk-boundary work on the
financial tables. The evidence to justify whichever is chosen is in the repo.

**Standing debt, unchanged:** Qdrant `:latest` image pin (conscious, tagged for
Turn 7) · GPU passthrough (deferred until heavier models demand it) ·
`.env.example` trailing newline.

**HR questions locked this session:** Q13/14/15 (hardest technical problem, how
you debugged it, what you would do differently) now have three separate
defensible answers — the Vertex-metered embedding quota, the mixed-ruler
refusal guard, and the cached-field pattern across three subsystems. Q11/12
(how you know it works, how you measure) are answered by a §02 table that
reports its own failure rather than hiding it.
