# Attest — Session 21

**[21]: Demo Prep — the Latency Split, Recorded**

---

## Status Board

**Project.** Attest — a multimodal, self-grading RAG system over SEC filings.
Flagship portfolio/interview build. Solo.

**Session type.** Presentation prep. Demo is 2026-09-03. No feature work — one
bucket, closing what the runbook and README had left as untraceable.

**Turn state.** Unchanged from Session 20: Turn 6 complete except upload, one
bucket short, not logged as done.

**§02 contract.** Untouched this session. No judging ran.

**What this session added.** A runbook (`DEMO_RUNBOOK.md`) verified against a
live cold start, a README latency section, and — the reason this log exists —
a real number for the split between our stack and the model provider inside
one specific slow ask, plus proof of a second, previously-undiscovered defect:
the shell can abandon a call the engine goes on to finish, and lose the
answer.

**Quota.** Opened at 14 (Session 20's closing value). One single-hop ask this
session — `data/quota/agent_calls.json`, last written 2026-09-02T12:52:30Z —
closed the day at **16**. Net movement: **+2**, matching the single-hop-ask
cost already established in T6.16. This closing bucket (T6.C) spent nothing
further: no model API calls, confirmed by re-reading the same file at close
with the same value.

---

## Supersedes

- **The engine has never published a host port — and Session 20's own text
  says otherwise in spirit.** Verifying the runbook's own health-check
  section against `docker-compose.yml` found the `engine:` service block
  (line 25) carries no `ports:` key at all, unlike `shell` (line 6) and
  `postgres`/`qdrant` (line 19 area), which do. `docker compose ps` today
  shows an empty `PORTS` column for `attest_engine`. This isn't new — the
  Turn 6 journal entry already recorded the port being *unpublished* as a
  tenancy fix — but no session had verified it by reading the compose file
  itself against a runbook written to `curl localhost:8000`, which is why the
  runbook was corrected to check from inside the Docker network instead.
- **The 210s shell-side timeout is not a safety margin against the known
  worst case anymore — it's the second-most-common failure mode.** The
  constant's own comment (`shell/accounts/engine_client.py:7-8`) reads "Worst
  end-to-end /ask latency measured so far is ~196s ... This must clear that
  with margin." Today's ask cleared 210s and kept running to 251.648s inside
  the engine. The margin the comment describes no longer holds.

---

## Goal and buckets

**Goal: make today's latency observations traceable, then close.**

| Bucket | One line | Status |
|---|---|---|
| **T6.C** | Record the incident's phase split and the cold-start/health evidence; update README, JOURNAL.md; commit and push. | done |

---

## What happened

### The incident

A single-hop ask (`"What were Apple's total net sales for fiscal 2025?"`,
alice, `aapl_10k`) was submitted through the shell. The engine completed it
and logged the result itself:

```
2026-09-02T12:54:56.924670795Z INFO:attest.engine:ask latency_s=251.648 question="What were Apple's total net sales for fiscal 2025?"
```

The shell never showed that answer. Its own `httpx` client carries a 210.0s
timeout (`shell/accounts/engine_client.py:8`) and fired first, writing its own
row to `AskRecord` rather than waiting:

```
id=22  created_at=2026-09-02 12:54:15.320274+00
error=unreachable  error_detail="timed out"
answer=""  latency_s=NULL  sources=[]
```

`12:54:15.320` minus the engine's derived request start (`12:54:56.925` −
`251.648s` = `12:50:45.277`) is **210.04s** — the client timeout firing almost
exactly on its configured value. The engine kept computing for another
41.6 seconds after the shell had already given up and recorded failure, then
produced a correct, gold-matching answer that had nowhere to go. It exists
only in the engine's stdout log, never in Postgres, never in a browser.

### The phase split

The engine log carries no per-phase timer, but three timestamped events
inside the same request let the total be split without any additional
instrumentation:

| Phase | Span (from container logs, UTC) | Duration |
|---|---|---|
| Model call 1 (agent decides to retrieve) | request start `12:50:45.277` → `12:52:22.205` | **96.93s** |
| Retrieval + rerank (1 round-trip) | `12:52:22.205` → `12:52:30.018` | **7.81s** |
| Model call 2 (agent composes the final answer) | `12:52:30.018` → `12:54:56.923` | **146.91s** |
| **Sum** | | **251.65s** (engine logged 251.648s) |

Two provider round-trips account for **243.84s of 251.648s (96.9%)**. The
9-point pool of dense+sparse fusion, the Qdrant query, and the deployed
cross-encoder rerank together account for the remaining 7.81s.

That 7.81s is not an outlier by itself. `data/eval/retrieval_timing_20260902T012156Z.json`
— a zero-quota, isolated timing of the same reranker across seven of the
gold-set questions, produced during Session 20's reranker A/B test — recorded
individual retrieval+rerank calls between 4.726s and 9.029s (mean 5.736s),
and estimated retrieval's share of seven live-ask totals at 4.69%–13.2%.
Today's 7.81s sits inside that range. This is the evidence for ruling
retrieval and reranking out as a contributor to the outlier: the stage that
today's incident shares with an already-measured baseline behaved exactly
as that baseline predicts.

**Ruled out:** retrieval, reranking, and our own application code — the
pipeline produced a correct answer, on schedule for its own stage, and the
7.81s stage timing is unremarkable against seven prior isolated
measurements. The 210s/220s timeout values are correctly set for the purpose
stated when they were written (Session 19/20); they are not miscalibrated,
they are exceeded.

**Genuinely open, not tested today:** why the two model round-trips took
243.84s instead of the ~180–190s implied by the previous 196s worst case.
Two candidate causes remain indistinguishable from the available logs — host
contention on this machine at the incident's timestamp (no per-hop network
timing was captured, so a slow local network path or CPU contention under
WSL2/Docker Desktop cannot be ruled in or out) and a provider-side cold-start
or throttling penalty on Google's end. Confirming either would require
deliberately reproducing slow calls, which spends metered quota — out of
scope for this no-spend closing bucket, and not attempted.

### Cold start and the four health checks

`DEMO_RUNBOOK.md` (new this session, untracked before this close) documents
"~50 seconds" from `docker compose up -d` to all four services healthy,
stated as a measured figure. That specific stopwatch reading exists only in
this session's earlier terminal output — no separate timestamped artifact
records it, so it is not independently re-derivable from what's on disk right
now, and is recorded here as exactly that: a number this session observed
but did not persist as raw data.

The runbook's four verification commands were re-run live during this
closing bucket (2026-09-02, ~15:5x UTC) and all four passed, matching the
runbook's stated expectations exactly:

1. Engine health (from inside the Docker network — the engine has no host
   port): `{"status":"alive","service":"engine"}`
2. Postgres: `/var/run/postgresql:5432 - accepting connections`
3. Qdrant: `{"result":{"collections":[{"name":"attest_chunks"}]},"status":"ok",...}`,
   collection point count `304`
4. Shell: `302` (redirect to login)

None of these four spend quota; none touch a model provider.

---

## Decisions locked

- **Live asks are off for tomorrow's demo.** Recorded in `DEMO_RUNBOOK.md`
  section e/f. The reason is not just "it's slow" — it's that a slow-enough
  answer is provably lost today, not merely delayed, and the loss produces no
  visible error to a user watching the page (the shell's own error card would
  show, but a demo audience has no way to know an engine-side answer existed
  and never arrived).
- **The timeout mismatch is filed as a defect, not fixed this session.**
  Raising the shell's client timeout past the engine's own worst case would
  require knowing that worst case first, which today's open causes (host
  contention vs. provider variance) block from being established with
  confidence. Recorded, not patched, per the no-feature-work constraint on
  this bucket.

---

## Hard-won lessons

**A margin sized against the worst *previously observed* case is not a
margin against the worst case.** `engine_client.py`'s 210s constant was set
with an explicit, correct rationale — clear the known 196s worst case with
room — and it was cleared by more than 14s just five sessions later. The
comment describing the intent is still accurate; the number it protects has
moved. Any timeout set from an observed maximum needs a note that says so
explicitly, so the next person reads it as "true as of the last measurement,"
not "true."

**A completed answer and a recorded answer are different claims, and a slow
system will eventually prove the gap.** Nothing about today's ask was a bug
in the RAG pipeline — the retrieval, rerank, and both model calls each did
their job and the final answer was almost certainly correct (the question
shape and gold key are known from T6.16). The defect is entirely in what sits
between "the engine finished" and "the user sees it": a shorter timeout on
the calling side that discards the callee's eventual success silently. This
is the same family of bug as Session 19's 30-second gunicorn default — a
config value nobody had reason to revisit outliving the assumption it was
set against — surfacing again at a different seam in the same request path.

**Splitting a duration into named phases without adding new instrumentation
is possible when every phase already logs a start or end event.** No new
timer was added to the engine to produce the 96.93s/7.81s/146.91s split —
it came entirely from three existing log lines' UTC timestamps, arithmetic,
and one derived value (request start, from the logged total). Useful when
the constraint is "diagnose, don't ship a change."

---

## Next session

Unchanged priority list from Session 20 — upload, vision quota ceiling first
— plus one new, higher-priority item surfaced today:

1. **Decide what "the shell's timeout" should actually be**, once host
   contention vs. provider variance can be told apart (needs metered
   reproduction, budgeted explicitly before spending). Until then, treat
   any `/ask` that runs past ~180s as one that may silently lose its answer.
2. Consider whether the shell should persist a partial/pending `AskRecord`
   at request start rather than only at completion or timeout, so a lost
   answer at least leaves a row that can be reconciled against the engine's
   own log after the fact. Not designed here — a real option, not a decision.
3. Everything carried forward from Session 20 (see `CLAUDE.md`, Carried
   Forward) stands untouched: vision quota ceiling, read-only corpus mount,
   ingest model-reload tax, no OCR/failure detection, judge key ceiling,
   markdown rendering, `alice` fixture churn, cross-tenant response-level
   proof, `/admin/` reachability, retrieval precision at 0.774, Qdrant
   `:latest` pin.

**Carried debt, added this session:**

13. **The shell can silently lose a completed engine answer.** Its 210s
    client timeout is shorter than realistic worst-case `/ask` latency has
    now proven to be (251.648s observed). Confirmed today with a concrete
    before/after: `AskRecord` id 22 recorded as `error=unreachable` while the
    engine's own log shows the same request finishing with a correct answer
    41.6s later. Not fixed — root cause of the underlying slowness (below) is
    a prerequisite to picking a new number responsibly.
14. **Provider round-trip variance is unexplained above the stack level.**
    243.84s of a 251.648s ask was two model calls; 7.81s was retrieval and
    rerank, in line with a seven-run isolated baseline. Host contention and
    provider-side variance remain equally plausible and both untested —
    testing either costs quota.
