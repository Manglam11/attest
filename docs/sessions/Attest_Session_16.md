# Attest — Session 16

**[16]: Turn 5 Closes — p95 Excluded, §02 Table Complete**

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
1 figure). 15-pair gold set: 12 answerable, 3 unanswerable.

**Turn state. Turn 5 (trust/evaluation layer) is CLOSED.** Five of seven spiral
turns alive. The §02 table is complete and honest: four metrics measured, one
declared not-applicable with a reason, one bounded rather than point-estimated.
Two of the six do not pass, and both are recorded as failures with their status
stated plainly.

**§02 contract vs. measured — final:**

| Metric | Target | Measured | Verdict |
|---|---|---|---|
| faithfulness | ≥ 0.90 | 1.000 (n=12, one embedder) | PASS |
| retrieval precision | ≥ 0.85 | 0.774 (n=12) | FAIL — diagnosed |
| answer relevance | ≥ 0.85 | 0.979 (n=12, one embedder) | PASS |
| hallucination flag | < 0.50 | 0/3 — all 3 unanswerable refused | PASS |
| figure-grounded | ≥ 80% (aspirational) | not attempted — one-figure corpus | n/a |
| p95 latency | ≤ 8s | n=7, all > 8s (43.5–196.0s) | **EXCLUDED** — not narrowly missed |

**Head of `main`: `b91ca10`.** Tree clean, local == `origin/main`.

**Stack state at close.** All three containers stopped and removed cleanly.
Named volumes (`postgres_data`, `qdrant_data`, `hf_cache`) untouched — a
container teardown, not a data teardown. Docker and WSL left running; shutting
those down and unmounting E: is a host action outside the executor's reach.

**Quota at close.** 20/20 used for 2026-09-01. Zero remaining. Every metered
call this session was approved individually and produced a recorded observation.

---

## Supersedes

- **S15's closing claim was wrong.** Its Status Board said "tree clean, local ==
  `origin/main`, all work in two places." It was not. A promoted `CLAUDE.md`
  lesson and the S15 log itself were never committed — they existed only on the
  external drive. Corrected here rather than by rewriting the old log; the
  historical record keeps its own inaccuracy.
- **`CLAUDE.md`'s build-state prose was two sessions stale.** It described a
  half-finished judge and an unfixed write-merge bug, both of which git history
  showed as merged before the then-current head. Caught by the executor reading
  the repo against the prose. Rewritten twice this session — once to current
  state, once again at close to carry the final §02 table.
- **p95 is not a point estimate and never will be under this contract.** §02
  asks a one-sided question (≤ 8s), so the answer is a bound, not a percentile.
  The old plan — accumulate n=20 over several days — was abandoned as
  unnecessary.
- **The p95 ruler collapsed the usable sample to n=1 before this session.** S15
  locked engine-side timing as the §02 source; the twelve pre-existing latencies
  were client-stopwatch numbers and are not poolable with it. Rulers are not
  mixed, so the project effectively held one observation, not thirteen.
- **`figure-grounded` moves from "not yet measured" to "not applicable, with a
  reason."** The corpus contains exactly one real figure. There is no
  80%-of-what basis to compute. It stays aspirational until the corpus grows —
  but it is now declared, not silently pending.
- **`AGENT_DAILY_CEILING = 20` is measured, not assumed.** Google's free-tier
  RPD wall fired at exactly the value our own counter held. The constant is now
  confirmed against the provider.
- **The per-ask planning constant is dead as an average.** 2.08 was replaced by
  worst-observed cost, read live off the tracked evidence file.
- **`generate.py` is deleted.** Turn 4 superseded it; nothing imported it.

---

## Goal and buckets

**Goal: close Turn 5.**

| Bucket | One line | Status |
|---|---|---|
| **T5.0** | Resume gate — environment, git, quota, vector store, judged artifact. | done |
| **T5.D** | *Unplanned.* Land two dangling docs; bring `CLAUDE.md` state current. | done |
| **T5.9a** | Make the harness incapable of replaying a cached latency. | done |
| **T5.9b** | p95 — the bounded verdict. The session's only metered spend. | done |
| **T5.12** | Quota gate hardened; `generate.py`'s fate decided. | done |
| **T5.J** | Seed `JOURNAL.md` — the interview record, five turns. | done |
| **T5.C** | Close Turn 5 — final table, reconcile, push, teardown. | done |

`T5.D` was not planned. The resume gate found unpushed work and stale prose, and
both had to land before anything else was built on top of them.

---

## What happened

### T5.0 — the gate earns its keep

Read-only, nothing started, nothing written. It returned three things worth the
bucket:

The stack was **absent**, not stopped — zero Attest containers existed, not
merely halted ones. The executor flagged it rather than starting them, since
starting is a state change and this bucket was read-only.

Two artifacts were sitting uncommitted: a `CLAUDE.md` promotion and the S15 log
itself, 349 lines, untracked. S15 had claimed both were in two places. They were
in one, on an external drive.

And the executor contradicted the brief's own context, as instructed to. It read
`CLAUDE.md`'s "where the build stands" section describing a half-finished judge
and an unfixed write-merge bug, checked git history, and found both completed
and merged before the current head. Its conclusion — the prose is stale, not the
repo — was correct, and the call was taken.

**One correction to its net list.** It carried row 3's context-precision score
forward as open investigation. It was not: S15 had already replayed the
retrieval locally and diagnosed it as a 0.048 near-miss at the reranker. Row 3
belongs to the Turn 2 deepening pass.

### T5.D — the two-places rule, restored

Three atomic commits: the S15 log committed verbatim (its inaccurate closing
claim untouched — a historical record keeps its errors), the promoted rule on
its own, and the build-state rewrite.

The rewrite came out **net four lines shorter** despite gaining the
context-precision diagnosis, because the resolved quota-wall and write-merge
narrative came out with it. `CLAUDE.md` is read on every invocation; length has
a per-call cost.

The executor also answered the quota-provenance question properly: the counter
is a host bind mount written only by `on_chat_model_start` on a real LangChain
invocation, mounted read-write into the engine and read-only into eval, and
date-keyed so it cannot carry stale counts. Teardown does not touch it. Nothing
in the code path can inflate it without a real model call. That is what made the
number safe to size a metered run against.

### T5.9a — a test that could fail

The harness cached run records by question text and replayed them verbatim on
resume. Fine for correctness fields; fatal for latency, where a multi-day
accumulation would replay day one's numbers wearing twenty hats. Same
cached-data-outliving-its-fix pattern as the judge write-merge, the embed
provenance, and the gold keys.

Three proofs demanded, each required to be capable of failing. The freshness
proof is the one that matters: the executor seeded an artifact with
`latency_s: 999.0` on every question, ran a fresh sample, and asserted no 999
survived. Then — unprompted — **it reintroduced the old merge bug in a throwaway
script and reran the same assertion against it**, watched it fail with the
cached values replayed, and only then trusted the pass. That is the difference
between a test and a decoration.

Health gate and quota gate both proved to block, not silently skip.

### T5.9b — the p95 verdict, and my own arithmetic error

**The design decision.** §02 asks whether p95 ≤ 8s. One-sided. If every
observation in a sample exceeds 8s, a one-sided 95% bound answers the contract
without estimating the percentile at all. n=8 was sufficient. The multi-day
accumulation was never needed.

**What I got wrong, twice.** I stated the bound as "the 95% lower bound on the
share above 8s." That is the wrong direction. `1 − 0.05^(1/n)` is the **upper
bound on the share below 8s**. I corrected it in one brief and it propagated
into the executor's report anyway, because it had already been said once with
confidence. The executor then re-derived it from scratch before writing
`JOURNAL.md` — explicitly because that was the mistake under discussion — and
stated it correctly for the first persisted time.

Read correctly the result is **stronger**, not weaker.

**The run.** Health gate confirmed the engine genuinely answering (~45s of model
load, resetting connections until the embedder and reranker finished, then clean
200). Qdrant confirmed at 285 points. Eight draws requested, ordered
round-robin across question categories so an early abort would still leave a
representative sample.

| # | Question | latency_s | calls |
|---|---|---|---|
| 1 | total net sales | 53.62 | 2 |
| 2 | total assets | 84.29 | 2 |
| 3 | stock performance graph, ending value | 91.25 | 2 |
| 4 | net sales − R&D difference | 122.29 | 2 |
| 5 | cost of sales | 67.08 | 3 |
| 6 | cash + equivalents + securities | 195.98 | 4 |
| 7 | stock performance graph, base amount | 43.46 | 2 |
| 8 | net income | **aborted — 429 RESOURCE_EXHAUSTED** | — |

n=7. Min 43.46s, median 84.29s, max 195.98s. **All seven exceeded 8s** — the
minimum is over five times the target. The seven collected observations were
saved intact; nothing was lost to the abort.

**The verdict, stated correctly:** with seven of seven fresh engine-timed
observations above 8s, the 95%-confidence upper bound on the share of the
response-time distribution *below* 8s is approximately 35%. A passing p95
requires at least 95% below 8s. The contract is **excluded** by a factor of
nearly three — not narrowly missed. This holds without any multi-day
accumulation.

**Why it aborted at 7.** The gate checked once, upfront, against a 2.08 average.
Actual costs were 2, 2, 2, 2, 3, 4, 2 — mean 2.43, worst 4. The upfront
arithmetic (8 × 2.08 = 16.6 ≤ 18) looked safe; the real cumulative spend left
one call where the eighth ask needed at least two. The executor flagged this as
a calibrated risk and explicitly declined to change the gate unilaterally after
the fact.

The silver lining: the 429 landed at exactly our own counter's value. The
ceiling is now confirmed against the provider.

### T5.12 — the gate, and the deletion

**Gate hardening, my call:** re-check before every draw, and size against worst
observed cost rather than the mean. An average cannot gate a run whose worst
single draw is double it.

**The executor went further than the brief, correctly.** I specified a measured
constant. It made the constant read itself off the tracked evidence file and
self-tighten as history accumulates, demoting the hardcoded `4` to a bootstrap
default that dies the moment real data exists — verified by running
`worst_case_calls()` against the committed artifact and watching it return 4.0
from disk rather than from a literal. That inverts the pattern that has bitten
this project three times: the live source of truth outliving the cached
constant, instead of the reverse. Provenance is the tracked file, not a comment.

**`generate.py`: dead code, deleted.** Grep across every symbol returned zero
references outside the file's own definitions and `__main__`. `/ask` calls
`run_agent` exclusively; Turn 4 fully superseded it. Verified at zero quota by
watching hot-reload restart cleanly with no import error and `/health` return
200 — named honestly as the strongest check available for free, not dressed up
as a regression suite. The grep is what carries the verdict.

### T5.J — the interview record

`JOURNAL.md` seeded at repo root, one entry per completed turn, first person.
Distinct from the session logs by audience: a session log says what happened, a
journal entry says what I would carry to another project.

Per-turn HR capture: every entry lands Q13/14/15 by design. Beyond that floor —
Turn 1 brushes Q16 (how secrets flow through the compose stack), Turn 2 is the
gold-set-wrong/model-right entry the blueprint names for it, Turn 3 adds Q20 via
the vision estimate matching the filed table within ~1%, Turn 4 touches Q17
through its named unresolved compound-case caveat, and Turn 5 carries Q3 (the
§02 contract) plus the richest Q13/14/15 material of the five.

**The restraint that mattered.** The executor deliberately did not let context
precision's diagnosed cause bleed into p95's entry as if it explained the
latency failure too. That root cause is not isolated. The journal says so rather
than implying a diagnosis nobody has done.

---

## Decisions locked

- Turn 5 is closed. The §02 table is complete and honest; two of six rows do not
  pass and both say so.
- p95 is answered as a bound, not a percentile. The contract asks a one-sided
  question and gets a one-sided answer.
- Rulers are never pooled. Client-stopwatch latencies are not evidence under an
  engine-timed contract, no matter how many of them exist.
- The quota gate re-checks before every draw and sizes on worst observed cost,
  read live off the tracked evidence file.
- `figure-grounded` is declared not-applicable with a stated reason, not left
  quietly pending.
- Metered work is scheduled first in any session where a daily ceiling applies.
- `generate.py` is gone. Unused code in a portfolio repo is a question I would
  have to answer with "I forgot it was there."

---

## Hard-won lessons

**On evidence.**

- *A one-sided contract deserves a one-sided answer.* Three days of quota were
  budgeted to estimate a number the contract never asked for. §02 asks whether
  p95 clears 8s, and seven observations settle that with 95% confidence. Read
  what the contract actually asks before funding the measurement.
- *A session's own closing claim is a status line.* S15 wrote "all work in two
  places" and two artifacts were in one. Our own success messages have now
  failed this test twice — once as a `print()` with no write behind it, once as
  a log asserting a clean tree. Verify the effect, not the assertion.
- *Falsify the test before trusting the pass.* Reintroducing the bug to watch
  the assertion fail is what turns a green check into evidence. This was done
  unprompted and it is the standard now.
- *Don't let one diagnosis cover two failures.* Context precision has a root
  cause; latency does not. Letting the first imply the second would have been
  the easiest and most dishonest line in the journal.

**On the pattern, again.**

Cached data outliving the fix meant to override it has now appeared in five
places: the judge write-merge, the embed provenance, the harness gold keys, the
harness latency replay, and — inverted at last — the per-ask planning constant,
which now reads from the live artifact instead of being read from a literal.
The fix shape is settled: **name which fields are safe to replay and which must
be re-derived, or make the constant read the source of truth itself.**

**On working with the executor.**

- *It can see the repo and I cannot.* It caught stale `CLAUDE.md` prose against
  git history, and it built a better constant than I specified. Both calls were
  taken.
- *It refuses to decide what is mine to decide.* It flagged the gate's
  average-versus-worst-case flaw and explicitly declined to change it
  unilaterally after the run. That boundary is working.

**Claude's own errors, logged honestly.**

- *I stated a statistical bound backwards, twice.* I gave the direction wrong,
  corrected it in a later brief, and it still propagated into the executor's
  report — because a confident wrong statement outlives its correction inside
  the same session. Any quantitative claim heading for a persisted document gets
  derived from scratch, not copied from an earlier message. The executor caught
  this by re-deriving; I should not have needed it to.
- *I sized a metered run on an average when its tail was unmeasured.* 2.08 came
  from one calibration point. I approved eight draws against it and the run
  aborted at seven. The evidence for worst-case gating existed only after the
  loss it would have prevented.

---

## Next session

**Turn 2 deepening pass — retrieval ranking.** The diagnosis is already written
and does not need repeating: three near-misses at the reranker (gaps
0.037–0.056) and one genuine retrieval miss (row 8, gap 0.711, rank 7 of 20 in
the fusion pool). Likely levers are a stronger reranker, tightening `k`, and
chunk-boundary work on the financial tables. The evidence justifying whichever
is chosen is already in the repo.

This is the first turn where a §02 number moves because of work aimed at it —
which means the honest thing is to record the before-number, change one lever,
and re-measure, rather than changing three and claiming the delta.

**Conscious debt carried out of Turn 5:**

1. **Retrieval ranking** — diagnosed, scheduled, not started.
2. **p95's root cause is not isolated.** We know the contract is excluded and
   that real end-to-end latency runs 43–196s. We do not know where the time
   goes. Per-stage instrumentation is owed before any further latency sampling —
   more samples of an undiagnosed number teach nothing.
3. **`figure-grounded` never attempted** — one-figure corpus, no meaningful
   sample basis. Stays aspirational until the corpus grows.
4. **Standing, unchanged:** Qdrant `:latest` image pin (tagged for Turn 7) · GPU
   passthrough (deferred until heavier models demand it) · `.env.example`
   trailing newline.

**Then Turn 6 — product shell.** Django auth, roles, multipage, and the real
test: two users cannot see each other's corpus.

**HR questions locked this session:** Q3 (success criteria — a contract set
before building and reported against honestly, including its failures) and
Q11/12 (how you know it works, how you measure — a §02 table that publishes two
failures rather than moving the targets). Q13/14/15 now have `JOURNAL.md` behind
them across all five completed turns.
