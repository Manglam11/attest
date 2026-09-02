# Attest — Session 19

**[19]: The Browser Moment — First Authenticated /ask**

---

## Status Board

**Project.** Attest — a multimodal, self-grading RAG system over SEC filings.
Ingests a 10-K, answers plain-English questions with citations, reads figures
via a vision model, and grades its own faithfulness so it can refuse an answer
it cannot ground. Flagship portfolio/interview build. Solo.

**Stack.** Django shell + FastAPI engine + Qdrant + PostgreSQL ·
`bge-small-en-v1.5` dense + BM25 sparse (hybrid RRF) · `bge-reranker-base`
cross-encoder · `gemini-3.6-flash` (agent), `gemini-3.5-flash-lite` (judge) ·
`httpx` 0.28.1 as the shell→engine client · Docker Compose on WSL2/Ubuntu,
external SSD (E:), Agastya111.

**Corpus.** 304 points, verified live this session, unchanged:

| owner | doc_id | points |
|---|---|---|
| alice | aapl_10k | 285 |
| bruno | bruno_10k_excerpt | 10 |
| carla | carla_10k_excerpt | 9 |

15-pair gold set unchanged: 12 answerable, 3 unanswerable, all against `alice`.

**Turn state.** Turn 6 is roughly **two-thirds built.** Tenancy was done in S18.
This session added the seam and the first page: a logged-in user can now open a
browser, ask a question, and read a cited answer from their own corpus. Still
missing before Turn 6 can be called complete: upload/library, history, and the
trust dashboard.

**§02 contract — untouched.** No judging ran. Precision still fails at 0.774.

**Latency observations — recorded, not concluded.** Two live end-to-end calls
through the product:

| question shape | retrieval round-trips | latency |
|---|---|---|
| single-hop lookup (net income FY2025) | 1 | 11.348s |
| refusal / prediction (revenue > $500B?) | 3 | 47.355s |

These sit far below the 43–196s previously on record, and they separate cleanly
by how many times the agent called `retrieve`. Two points are not a
distribution and §02's p95 remains EXCLUDED — but the recorded picture of "the
system is uniformly slow" is now contradicted by data and should not be
repeated without re-measuring.

**Head of `main`: `35a27fe`.** Verified by reading the remote directly
(`ls-remote`), not by trusting the push command's own output. Local == origin.

**Quota.** Counter reads 8/~20 RPD for 2026-09-02. Engine access log is the
truth: 2 successful `POST /ask` → 200, 3 × 401 (all forged/tampered token tests,
none reached `run_agent`). Counter delta +6, because it counts Gemini
invocations inside the ReAct loop, not HTTP requests — the refusal cost 4
internal turns, the lookup 2.

---

## Supersedes

- **The shell is now a running product, not a declared container.** S18 found
  `shell/` had never started. It now serves a base layout, four pages, and a
  working chat view on a published host port (8001).
- **Turn 6 debt #1 is closed.** A live authenticated `/ask` — Django-minted
  token, accepted by the engine, real grounded answer — has now run. This was
  the item blocking any claim that the tenancy layer works end to end.
- **gunicorn's worker timeout was 30 seconds** against a worst observed engine
  latency of ~196s. Every slow answer would have been SIGKILL'd. This defect
  has existed since the shell was written and could never fire, because the
  shell had never run. Fixed to 220s and verified in the live process.
- **`alice` is a test fixture being used as a human account.** Her password was
  unrecoverable (Django hashes one-way; S18 recorded only the hash prefix) and
  was reset to a known demo value. Her corpus was ingested by a script, not
  uploaded through a UI — which becomes a real inconsistency the moment upload
  lands.
- **The engine's `contexts` field carries no `doc_id` or page metadata** — bare
  strings only. This blocks two things at once: the blueprint's source-card UI,
  and any response-level verification that the owner filter fired.

---

## Goal and buckets

**Goal: make the build openable.** Turn the proven tenancy layer into something
a human uses in a browser, and close the one debt that blocked calling that
layer proven.

| Bucket | One line | Status |
|---|---|---|
| **T6.6** | Resume gate — read-only state verification. | done, **G3 failed** |
| **T6.7** | Clear the gate; bring the stack up; survey the shell. | done |
| **T6.8** | Django→engine seam, proven without spending. | done |
| **T6.9** | One metered authenticated `/ask`. | done, attempt 1 of 3 |
| **T6.10** | Chat page, base template, answer viewer, error states. | done |
| **T6.10b** | *Unplanned.* Reset alice's password. | done |
| **T6.C** | Close — journal, reconcile, push. | done |

---

## What happened

### T6.6 — the gate caught the same failure a third time

The Session 18 log was untracked, exactly as S16's and S17's had been. Three
sessions, same file, same miss. This is not bad luck; it is the close ritual in
the wrong order — the log is written *after* the final push, so it can never be
in that push. The gate is the only thing that has ever caught it.

The gate also found zero containers existing at all — not stopped, never
created. Named volumes survived, and the 304 points were verified rather than
assumed.

### T6.7 — the survey rewrote the plan again

Second session running, the survey earned its round. Three things it changed:

- The shell had **no `ENGINE_URL`**. The seam had no address to call. The engine
  service carried a stray self-referential copy of that variable, apparently
  copy-pasted from the eval service — flagged, left alone.
- **No base template existed.** All three auth templates were bare fragments
  with no `{% extends %}`, no `<html>`, no CSS anywhere in the repo.
- **No HTTP client of any kind** in the shell, and nothing in it had ever made
  an outbound request.

And the finding that shaped the next two buckets: the engine exposes exactly
two routes, `/health` and `/ask`. There is **no way to prove a valid token
round-trips without triggering a model call.** The reject path is free; the
happy path costs money. That constraint was designed around rather than wished
away.

### T6.8 — the seam, and an honestly incomplete proof

`httpx` 0.28.1, verified live on PyPI and matched to the version already pinned
in the eval requirements so the repo does not carry two. Timeout 210s, clearing
the worst observed latency. Retries explicitly disabled — `httpx` defaults to
zero, but a silent transport change would otherwise spend a second metered call
invisibly.

Three distinguishable errors, three free proofs: health reachable through the
shell's own code, forged and malformed tokens both rejected as clean
`EngineAuthError`, and a missing address failing at Django import in 0.22s
rather than hanging for 210s.

The executor stated plainly that the forged-token test **has no positive
control in this bucket** — a 401 is indistinguishable from a broken client, and
the only witness costs a model call. It did not fabricate a substitute. That
honesty is what made T6.9 worth running.

### T6.9 — the call that closed the debt

First attempt of a three-attempt budget. `mint_token('alice')` → 200, not 401 —
the positive control T6.8 structurally could not produce.

`$112,010 million (Pages 33, 34)`, matching the gold key exactly, with both
cited pages independently corroborated in the returned contexts.

On isolation, the report drew the line precisely: all five contexts were Apple
text, consistent with correct filtering — but with no `doc_id` on any context,
this call **cannot** distinguish a working owner filter from vector similarity
favouring the only Apple content in the pool. The isolation proof remains
S18's forged-token control. Said rather than glossed.

### T6.10 — the first real page, and a server bug only a running app could reveal

Base template with two blocks and navigation as fixed chrome, so no child page
can silently replace it.

The wait was argued, not defaulted into: HTMX decorates a synchronous wait but
does not shorten it; a real fix needs an async job and polling, which is new
machinery this bucket excluded. Plain POST plus a disabled button and an honest
"up to 3 minutes" message.

And along the way, **the find of the session**: gunicorn's default worker
timeout is 30s. Any answer approaching the observed 196s worst case would have
been killed by the server, and it would have presented as a frontend bug. It
was invisible until something actually waited.

### T6.10b — the unrecoverable password

`alice` predates the real signup flow. Django hashes one-way, S18 recorded only
`pbkdf2_sha256$870000$...`, and nothing in the repo, database, or config could
return the plaintext. Reset through Django's own tooling, verified over real
HTTP with both a correct login and a wrong-password rejection — the second
because a successful login alone cannot distinguish a working reset from an
auth layer accepting anything.

### The browser moment — and the bug that a mock had hidden

The live question asked was the blueprint's red row: *"Will Apple's revenue beat
500 billion dollars next year?"*

The system refused correctly, rewrote its query three separate ways looking for
grounding, found none, and gave the three historical net-sales figures it
*could* ground with page citations. Exactly the differentiator, rendered in a
browser for the first time.

**But it rendered in the ordinary answer card, not the blue refusal card.**
The view compares `result['answer'].strip() == REFUSAL_TEXT` — exact equality —
while the live answer *leads* with the refusal sentence and continues. The
mocked refusal in T6.10 was a bare sentence, so it passed. Reality is chattier
than the mock.

Diagnosed by reading the comparison, not by theorising. Left unfixed
deliberately: a debug thread does not get opened at the tail of a long session.

---

## Decisions locked

- The shell owns the token minting. It calls the engine as the logged-in user;
  the engine still derives `owner_id` from the signature and never from a body.
- `httpx`, pinned to the version already in the repo, with retries explicitly
  disabled on any path that can spend money.
- Client timeout and server worker timeout must both exceed the worst observed
  end-to-end latency. Either one alone is a false guarantee.
- Plain form POST for now. Async job + polling is Turn 7 ops work, not a
  smuggled-in bucket.
- The tool-call trace is product UI, not debug output. It is the visible
  evidence the agent chose its own path.
- A correct refusal is a **success state** in the UI and gets its own card.
- Turn 6 is still not complete.

---

## Hard-won lessons

**A mock proves the code path, never the behaviour.** The refusal card passed a
mocked refusal and failed a real one, because the mock was written to the shape
the code expected. Every branch verified only against a mock is unverified —
and by the executor's own report, `EngineResponseError` is now the remaining
one in that category.

**A defect in code that never runs is not a fixed defect, it is a delayed one.**
gunicorn's 30s timeout was wrong from the day it was written and could not fire
until the shell actually served a slow request. Same family as S18's
unpublished-port finding: five turns of "the stack is up" that nobody counted.

**Latency is a property of question shape, not of the system.** 11s for one
retrieval round-trip, 47s for three. The old "43–196s" figure was measuring
multi-step questions and got generalised into a verdict on the whole system.

**A one-way hash means the credential is gone, not hidden.** There is no file to
grep. Recognising unrecoverability immediately is faster than searching for
something that structurally cannot exist.

**Claude's own errors, logged honestly.**

- *I sent Manglam hunting for a password I already knew was unrecoverable.* I
  correctly said the only possible locations were outside the system, then
  still spent a round on the search before offering the reset. When something
  is structurally unrecoverable, the remedy belongs in the same message as the
  diagnosis.
- *I let the ritual's ordering defect survive three sessions.* I have caught the
  untracked log three times with the gate and never once fixed the cause. A
  recurring catch is a design smell, not a win.

---

## Next session

**Open with the refusal-card fix.** Cause is confirmed and written down. The
executor's warning stands: a naive substring swap removes tonight's false
negative and opens a narrow false-positive risk if a grounded answer ever quotes
that sentence. Fix both directions, and this time verify against a real
refusal, not a mock.

**Then finish Turn 6:** upload and library, history, and the trust dashboard.
Upload is the one that forces the `alice`-as-fixture inconsistency into the
open, and it needs `doc_id` and page metadata on `contexts` to render source
cards properly.

**Quota planning:** the day closed at 8 of ~20. Schedule metered work first.

**Debt carried out:**

1. **Refusal-card equality bug** — cause confirmed, fix deferred one session.
2. **`contexts` has no `doc_id` or page metadata** — blocks source cards and
   blocks response-level isolation verification.
3. **`EngineResponseError`'s UI branch is mock-verified only.**
4. **`alice` is a fixture used as an account**, with a script-ingested corpus.
5. **The engine's stray self-referential `ENGINE_URL`** in compose.
6. **The judge key has no counter and no ceiling** — still blocking any paid
   migration.
7. **The quota counter's day-rollover disagrees with the provider's.**
8. **`/admin/` anonymously reachable**; **password reset has no `EMAIL_BACKEND`.**
9. **Retrieval precision still fails at 0.774**; **`figure-grounded` never
   attempted.**
10. **Standing:** Qdrant `:latest` pin (Turn 7) · GPU passthrough (deferred).

**HR questions locked this session:** Q13/14 gain their strongest item yet — a
30-second server timeout sitting under a three-minute operation, invisible until
something waited. Q15 (when it failed) gains the refusal card that passed on a
mock and failed on reality. Q7/Q25 (effort saved) and Q19 (target user) open
properly now that there is a product a person can actually open.
