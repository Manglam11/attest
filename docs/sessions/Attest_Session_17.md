# Attest — Session 17

**[17]: Turn 2 Deepening — Reranker Swap Measured And Reverted**

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
1 figure), reconfirmed live this session rather than carried forward. 15-pair
gold set: 12 answerable, 3 unanswerable.

**Turn state.** Five of seven turns alive. This session was a **deepening pass
on Turn 2**, aimed at the one §02 row that fails on quality. It did not move
that row. It replaced a wrong diagnosis with a correct one, built a free ruler,
measured one lever, and reverted it.

**§02 contract vs. measured — unchanged from Turn 5's close:**

| Metric | Target | Measured | Verdict |
|---|---|---|---|
| faithfulness | ≥ 0.90 | 1.000 (n=12) | PASS |
| retrieval precision | ≥ 0.85 | 0.774 (n=12) | FAIL — re-diagnosed, not fixed |
| answer relevance | ≥ 0.85 | 0.979 (n=12) | PASS |
| hallucination flag | < 0.50 | 0/3 — all 3 unanswerable refused | PASS |
| figure-grounded | ≥ 80% (aspirational) | not attempted — one-figure corpus | n/a |
| p95 latency | ≤ 8s | n=7, all > 8s | EXCLUDED |

The precision figure is the same judged run as before this session. No re-judge
happened; none was warranted.

**Head of `main`: `c744d98`.** Tree clean, local == `origin/main`, confirmed by
fresh read at close.

**Stack state.** Application containers stopped and removed. Named volumes
(`01_attest_postgres_data`, `01_attest_qdrant_data`, `01_attest_hf_cache`)
intact. Nothing Attest-related running.

**Quota.** Zero metered calls this session. Every measurement was local.

---

## Supersedes

- **The Turn 5 retrieval diagnosis is wrong and is replaced.** It recorded three
  near-misses at the reranker plus one genuine miss at rank 7 of 20. Re-derived
  live, the shape is 11 of 12 rows clean, two rows where the reranker *demotes*
  the correct chunk below its fusion rank, and one row that was never a
  retrieval miss at all. The old shape did not reproduce.
- **S10's "the retrieval stack is the bottleneck" is dead.** Measured warm and
  per stage, a retrieval call costs 5.736s total and accounts for 4.7–13.2% of
  an observed ask. The 62s figure from S10 was per-call model reloading, already
  removed by Turn 4's singleton fix. Latency belongs to the agent loop.
- **The rank-of-correct-chunk baseline is not the graded metric.** §02 contracts
  to context precision, which is rank-sensitive average precision over the
  returned set. A row can put the correct chunk in the top-5 and still score
  0.333. The two rulers answer different questions and are not pooled.
- **The Turn 2 baseline was run on the wrong input.** It queried retrieval with
  the literal gold questions; the agent rewrites the query on 9 of 11
  single-call rows. Nine rows were measured on text the system never issues.
- **Cutoff is not a productive lever.** A uniform `TOP_K` moves the 12-row mean
  0.725 (K=5) → 0.729 (K=3 or 4) → 0.708 (K=2) → 0.583 (K=1). Best case is
  +0.004; tighter cuts zero out the rows whose only relevant chunk sits at
  rank 2–4.

---

## Goal and buckets

**Goal: the retrieval subsystem — its quality and its cost.** Both failing §02
rows pointed at the same place.

| Bucket | One line | Status |
|---|---|---|
| **T2.0** | Resume gate — read-only state verification. | done |
| **T2.D** | *Unplanned.* Land the S16 log, untracked since close. | done |
| **T2.R** | *Unplanned.* Promote three S16 doing-rules into `CLAUDE.md`. | done |
| **T2.1** | Re-derive the ranking baseline from scratch. | done |
| **T2.1b** | *Unplanned.* Reconcile rank against judged context precision. | done |
| **T2.1c** | *Unplanned.* Test the AP mechanism; rebuild the ruler. | done |
| **T2.2** | Per-stage timing inside retrieval. | done |
| **T2.3a** | Propose ordering levers; one gets picked. | done |
| **T2.3b** | Swap the reranker; generalise the derived-value check. | done |
| **T2.4** | Measure once. Keep or revert. | done — reverted |
| **T2.5** | Metered re-judge. | skipped, correctly |
| **T2.C** | Close — reconcile, journal, push. | done |

Three of twelve buckets were unplanned. Two came from the gate finding work
that had not landed; one came from the baseline disagreeing with the metric it
was supposed to explain.

---

## What happened

### T2.0 / T2.D — the gate, again

The S16 log was untracked, sitting only on the external drive — the exact
failure S16 itself recorded about S15, one session later. The gate is now the
only reason this project has not silently lost a session log twice.

Everything else the gate checked matched, with one honest correction: the quota
counter read 20/20 rather than zero because UTC had not rolled over at the
moment of the check. Right number, wrong minute.

### T2.R — three rules promoted

The three S16 lessons existed in a session log and nowhere the executor reads.
They were folded into three rules already present rather than added as new
entries, net +3 lines. Slotting rather than appending is what keeps a file that
is read on every invocation from growing without bound.

The rule about stale numbers caught a stale count in the same file on its way
through — its first act was to find drift of exactly the kind it describes.

### T2.1 — the diagnosis that did not reproduce

Re-derived live over three runs: 11 of 12 rows clean, zero near-misses, one row
unscoreable. The three-near-miss shape I brought into the session is not what
the system does.

The chunk-identification work is what makes that trustworthy. Exact grouped-number
token matching across the full 285-point corpus, then hand-inspection of every
collision rather than taking the first hit. Eight rows turned out to be the
filing genuinely restating the same GAAP figure across MD&A, the primary
statements, and the notes — all real sources, kept. One row's value (100) was a
true coincidence and was separated by a distinguishing token. A fabricated key
was fed through the same path and returned zero matches, which is what makes the
clean verdicts falsifiable rather than assumed.

### T2.1b — the two rulers

The reconciliation found two things, neither of them the one I asked about.

**The baseline was measured on the wrong input.** Only 2 of 11 single-call rows
used the literal gold question; the agent rewrote the other 9, and one row
issued two queries and merged 9 contexts. A baseline run on gold questions
cannot validate a lever against what the system actually does.

**The mechanism, confirmed on the rows that were comparable.** Total assets:
correct chunk present, ranked 3rd, context precision 0.333. The four companions
were an equity roll-forward, a deferred-tax note, a PP&E note, and the cash-flow
statement — real financial-statement text, topically adjacent, none of them
answering the question. Low precision comes from what rides along, not from
what is missing. Faithfulness at 1.000 on all 12 rows corroborates it: the
answer-bearing chunk is always there.

A rank-sensitive average-precision formula reproduced the judged score exactly
on 5 of 6 low rows, which is what turned a single confirmed row into a general
mechanism.

### T2.1c — my claim, killed

I claimed the AP derivation implied that truncation could only lower a score.
Two rows falsify it: net income rises 0.950 → 1.000 at K≤4, and the stock-graph
base row rises 0.833 → 1.000 at K≤2. Both have all their relevant chunks early,
so cutting the tail removes only noise.

The derivation was right; the implication I drew from it was not, and the two
are different claims. What survives is narrower and still decisive: a *uniform*
cut is the only cut the system can apply, and in aggregate it buys +0.004 while
destroying the rows whose only relevant chunk sits deep. Ordering has headroom
on five rows without endangering the six at 1.000.

**The free ruler.** The offline proxy retrieves on the agent's persisted queries,
replicates the multi-call merge behaviour exactly, and scores with the validated
formula. It reproduced the judged scores bit-for-bit on 11 of 12 rows — not
approximately. That is the session's most reusable artifact: levers can now be
tested at zero quota, with the judge called once at the end to confirm.

Its fidelity cost is stated rather than hidden: the queries are the ones Gemini
issued on 31 Aug, not re-derived live, because re-deriving would spend metered
calls. The agent prompt is unchanged since, but the model is not deterministic.

### T2.2 — where the seconds go

| Stage | mean |
|---|---|
| dense embed | 0.021s |
| sparse embed | 0.000s |
| Qdrant hybrid query | 0.006s |
| unpack | ~0s |
| rerank | 5.709s |
| **total per call** | **5.736s** |

The cross-encoder is essentially all of it. Everything else sums to under 30ms.
Cold model load is 13.715s once per process; the first call after it is
indistinguishable from the warm mean, so there is no hidden first-inference
penalty.

Against the seven observed ask latencies, retrieval is 4.7–13.2% — never the
bulk. The remainder tracks the number of Gemini calls: two calls cluster around
43–91s, four calls produced the 196s maximum. Turn 7's latency work is an
agent-loop problem.

The timing check was built to fail: stage timings must sum within 5% of an
independent outer wall clock, so a skipped or double-counted stage would show
as a gap. Max gap was 0.0%.

### T2.3a — one lever, chosen before measuring

The score-gap table, pulled from the baseline rather than measured fresh:

| Row | fusion → rerank | correct-chunk score | top-1 score |
|---|---|---|---|
| R&D | 8 → 4 | 0.535 | 0.917 |
| total assets | 3 → 3 | 0.929 | 0.985 |
| operating income | 2 → 4 | 0.707 | 0.950 |
| cash/securities | 4 → 5 | 0.946 | 0.993 |

In two of four headroom rows the reranker actively demotes the correct chunk
below where fusion had already placed it. That is a capability failure in the
deployed model, not a hard task — which is what made the capability upgrade the
mechanism-grounded pick.

A heuristic header boost was proposed and rejected by the executor on its own
initiative, on the grounds that a rule authored by looking at twelve known
failures is fitting the gold set and would not survive a differently formatted
filing. Correct, and it declined to even measure it.

**The overfitting constraint held.** Candidates were ranked by argument, not by
pre-testing them on the free proxy and keeping the winner. Twelve rows is small
enough that trying several and keeping the best is fitting the ruler.

### T2.3b / T2.4 — measured once, reverted

The swap was confirmed at weight level inside the running process —
567,755,777 parameters, `XLMRobertaForSequenceClassification` — not by re-reading
the config string that had just been edited.

| Row | before | after | Δ |
|---|---|---|---|
| total net sales | 1.000 | 0.888 | −0.113 |
| net income | 0.950 | 1.000 | +0.050 |
| total assets | 0.333 | 1.000 | +0.667 |
| operating income | 0.500 | 0.333 | −0.167 |
| cash/securities | 0.500 | 0.000 | −0.500 |
| stock-graph base | 0.833 | 1.000 | +0.167 |
| five unchanged rows | — | — | 0 |

Mean over the 11 comparable rows: 0.7909 → 0.8004, **+0.0095**. Warm rerank cost:
5.71s → 23.91s mean, 58.39s max. Retrieval's share of an ask rises to as much as
55%.

Three rows regressed, one to a total miss. The two rows the old model demoted
still demote under the new one, and worse. A four-fold latency cost bought less
than a hundredth of a point on a metric that needs 0.076 to clear its contract.

**Reverted**, confirmed at weight level and from disk at close.

The derived-value fix survived, because it was a separate concern in a separate
commit: any gold row may now declare the operands its answer is computed from,
and relevance is checked against those. Stated as a general convention, not a
special case, with a self-test that fails on a leaked literal answer, on an
unrelated number, and on a non-derived row.

---

## Decisions locked

- The deployed reranker stays `bge-reranker-base`. A larger cross-encoder was
  tried, measured, and rejected on evidence.
- The `operand_keys` convention is permanent — retrieval is held responsible for
  surfacing the operands, not for arithmetic no chunk performs.
- The free proxy is the ruler for retrieval-ordering work. The judge is called
  once at the end of a lever, if at all.
- One lever per measurement, chosen before measuring, with keep-or-revert
  decided on that single result.
- Retrieval precision remains a published failure at 0.774. The target is not
  moving to meet the measurement.

---

## Hard-won lessons

**On rulers.**

- *Measure the input the system actually uses.* A baseline run on canonical
  questions cannot validate a system that rewrites them. Nine of eleven rows
  were measured on text the agent never issues, and nobody would have noticed
  had the two rulers not been forced to explain each other.
- *A derivation and its implication are two claims.* The AP formula was right;
  what I concluded from it was wrong, and only the implication was falsified.
  Test the implication separately from the maths.
- *A free proxy that reproduces the graded metric is worth more than a lever.*
  It cost one bucket and it is why a null result cost zero quota.

**On the null result.**

The honest version of this session is that the metric did not move. What it
bought is a correct diagnosis replacing a wrong one, a ruler that costs nothing
to run, a latency finding that redirects Turn 7, and one lever eliminated with
evidence. Recording that as progress on the metric would have been the easy
lie; the reranker choice is now defensible in a way it never was when it was
merely inherited.

**On the executor.**

- It contradicted the brief's premise three times — the baseline shape, the
  truncation claim, the query-text assumption — and was right each time.
- It refused to propose a heuristic it judged to be gold-set fitting, without
  being asked to apply that standard.
- It reported the query-mismatch problem plainly instead of papering over a
  comparison it had been asked to make.

**Claude's own errors, logged honestly.**

- *I commissioned a baseline on the wrong input.* The brief said re-derive the
  ranking picture and never said which query text to use, so the obvious
  reading — the gold question — is what got measured. The system's real input
  was one question away and I did not ask it.
- *I stated an implication as a settled derivation.* "Cutting `k` cannot help"
  was delivered with the arithmetic that made it sound proven. It was killed by
  two rows in the data I already had.
- *I let an acceptance item go unanswered twice.* The head verification was
  asked for in two consecutive briefs and reported in neither, and I only
  escalated it to a blocking gate on the third. An acceptance criterion that is
  silently dropped is not a criterion.

---

## Next session

**Turn 6 — the product shell.** Django auth, roles, multipage, and the real
test: two users cannot see each other's corpus. Turn 2's precision row has had
its lever tried; the next attempt at it should not be another guess, and Turn 6
is the layer that has never been started.

**Debt carried out of this session:**

1. **The two demotion rows** — operating income and cash/securities, where the
   reranker ranks the correct chunk below its fusion position. Now a known,
   unfixed behaviour rather than an unknown. A bigger CPU cross-encoder does not
   fix them; the next lever must be something else.
2. **p95's root cause is instrumented one layer down but not solved.** We now
   know retrieval is 4.7–13.2% of an ask and the agent loop is the rest. What
   the loop spends its time on is still unmeasured.
3. **`figure-grounded` never attempted** — one-figure corpus, no sample basis.
4. **Standing, unchanged:** Qdrant `:latest` image pin (Turn 7) · GPU passthrough
   (deferred) · `.env.example` trailing newline.

**HR questions locked this session:** Q13/14/15 gain their strongest entry yet —
a hypothesis formed from evidence, a single lever measured once, a null result
accepted and reverted rather than re-run until it looked better. Q11/12 deepen:
the project now owns a free ruler validated against its paid one.
