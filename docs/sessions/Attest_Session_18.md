# Attest — Session 18

**[18]: Turn 6 Half — Tenancy Proven, Product Shell Not Yet**

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

**Corpus.** Now genuinely multi-tenant and multi-document — **304 points**:

| owner | doc_id | points | provenance |
|---|---|---|---|
| alice | aapl_10k | 285 | real Apple FY2025 filing, re-fetchable |
| bruno | bruno_10k_excerpt | 10 | synthetic, regenerated from committed generator |
| carla | carla_10k_excerpt | 9 | synthetic, regenerated from committed generator |

15-pair gold set unchanged: 12 answerable, 3 unanswerable, all against `alice`.

**Turn state.** Turn 6 is **half built and honestly labelled half built.** The
tenancy and isolation layer — the load-bearing part — is done and proven. The
product shell it exists to serve is not. Django has auth and no other pages, no
HTTP client, and has never called the engine.

**§02 contract — untouched this session.** No judging ran, no metered call
succeeded. The table stands exactly as S17 left it, precision still failing at
0.774.

**Head of `main`: `5b34065`.** Tree clean, local == `origin/main`, read live at
close.

**Quota.** Local counter reads 2/20 for 2026-09-02 UTC. Both of those were
failed calls — Google returned 429 while the local counter believed the day was
fresh. No successful metered call this session.

---

## Supersedes

- **The engine was never network-isolated.** From Turn 1 through Turn 5, compose
  published the engine on `8000:8000` with `/ask` behind zero authentication.
  Anything that could reach the host could read the whole corpus without
  touching Django. This was not a future risk being designed against — it was
  the live state, discovered by the T6.1a survey.
- **`shell/` was never a running container.** `shell/Dockerfile` had no `CMD`
  and a duplicated `COPY`; the container is declared in compose and depended on
  by nothing that ran. It would have failed the first time it was needed.
  Django was also pointed at sqlite, not the Postgres it `depends_on`.
- **Postgres was empty.** No tables from any service. The database has been
  provisioned since Turn 1 and used by nothing.
- **Ingest was single-document, not merely single-tenant.** `store_vectors()`
  did `delete_collection` → `create_collection` → `upsert` on every run, with a
  hardcoded PDF path, sequential int IDs, and no document identifier of any
  kind. Two documents could not coexist.
- **`CLAUDE.md` claimed two quota ceilings; one existed.** The agent key has a
  persisted counter and ceiling. The judge key has neither — only
  fail-fast-and-resume on 429. Corrected in the file rather than papered over.
- **The synthetic corpus counts changed mid-session.** bruno 86 → 10, carla
  57 → 9. The original test PDFs were deleted after ingest and their content is
  unrecoverable; the committed generator produces different documents. The new
  counts are a fresh baseline, not a reconstruction.

---

## Goal and buckets

**Goal: start Turn 6 with the half that carries the weight** — identity in
Postgres, an owner stamped on every vector, and a filter the engine enforces so
the UI is not the thing keeping users apart.

| Bucket | One line | Status |
|---|---|---|
| **T6.0** | Resume gate — read-only state verification. | done |
| **T6.D** | *Unplanned.* Land the S17 log; correct the false quota claim. | done |
| **T6.1a** | Tenancy survey — facts before design. | done |
| **T6.1b** | Lock the design; unpublish the engine port. | done |
| **T6.2** | Django on Postgres; signup, login, logout alive. | done |
| **T6.3** | `owner_id` + `doc_id` at ingest; incremental; tenant index. | done |
| **T6.4** | Signed token; engine derives owner and filters retrieval. | done, one item open |
| **T6.5** | Two-user isolation test, including forged-token rejection. | done |
| **T6.C** | Close — reproducibility, journal, reconcile, push. | done |

One bucket unplanned, and it came from the gate again — the S17 log was
untracked, exactly as the S16 log had been. Two sessions running, the gate is
the only thing that has caught it.

---

## What happened

### T6.0 / T6.D — the gate found a lie in the constitution

The resume gate did its job twice over. The S17 log was untracked on the
external drive. And item 5 — "report the judge-key quota counter" — turned out
to be unanswerable, because no such counter exists. `CLAUDE.md` asserted two
keys with two ceilings; the code has one.

The executor named this plainly rather than answering the question it was asked.
That is the correct behaviour: an instruction built on a false premise should be
challenged, not satisfied.

The file was corrected to describe what the code does, at the same line count,
and the missing judge ceiling was recorded as tracked debt rather than built —
Turn 6 spends nothing metered, and a ceiling built now would be untested.

### T6.1a — the survey that rewrote the brief

I went in assuming there was a Django-to-engine seam to secure. There was no
seam. There was no Django app. There was no document model, no Postgres tables,
and no per-document identifier anywhere in the vector store.

And there was a hole: the engine's port published to the host, `/ask` open to
anything on the machine.

The executor's recommendation — payload-field tenancy in a single collection,
with a keyword index at `is_tenant: true`, checked against Qdrant's current
multitenancy guidance rather than recalled — was taken as given. So was its
sharper point on enforcement: a Django-layer filter is decorative while the
engine's port is open, and `owner_id` cannot be read from a request body because
anyone can write anything there.

### T6.1b — design locked, port closed

Five points recorded in a new `docs/decisions/` store, with an explicit threat
model naming what is *not* defended.

The port was unpublished and both directions proved: `Connection refused` from
the host, a clean 200 from inside the compose network. Showing the refusal is
what makes it a test.

A wrinkle surfaced honestly — the in-network check also failed for ~40s after
recreate, because the reloader's worker was still cold-loading the embedder and
reranker before the socket opened. Not a bug; a `start_period` too short for
reality. Carried forward and fixed in the next bucket rather than left as a note
nobody reads. A healthcheck that reports unhealthy during every normal cold
start is a status line that will eventually be believed.

### T6.2 — Django alive, and a container that never ran

Django moved to Postgres, and `shell/Dockerfile` turned out to be broken in a
way that proves nobody had ever started it. Fixed, `psycopg[binary]` pinned
after verifying it current on PyPI.

Auth is Django's own — no third-party package, no DRF. The checks that matter
are the ones that could have failed: a wrong password rejected with Django's own
error and no session, and a logout that killed the session **server-side**,
confirmed by reusing the cookie and being bounced to login. A 302 alone proves
nothing.

The stored password read `pbkdf2_sha256$870000$...`, not the plaintext
submitted.

One commit-hygiene slip, self-flagged: the `db.sqlite3` deletion rode along in
the healthcheck commit instead of its own. Harmless and correct, but not atomic.

### T6.3 — ownership, and the backfill that cost nothing

Every point now carries `owner_id` and `doc_id`. Point IDs became
`uuid5(namespace, f"{doc_id}:{index}")` — deterministic, collision-free across
documents, and idempotent on re-ingest. Delete-and-rebuild is gone; a document
is now delete-this-`doc_id`-then-insert, and removable standalone.

The 285 existing points were **backfilled in place**, not re-ingested — because
re-ingesting would have re-run the vision model on the one figure to reproduce a
description already sitting in the payload. Zero calls, zero cost.

Incrementality was proven so it could fail: ingest a second document (285 → 286
with the first unchanged at 285), then remove it (back to 285, first still
intact). A test that only ever adds proves nothing about disturbance.

### T6.4 — the gate that stopped a convincing false pass

The blocking gate mattered. The corpus carried `owner_id="alice"`, a username
string; Django's identity is an integer pk. If the token had carried the pk, the
filter would have matched zero points on every query — and **that looks exactly
like working isolation**. The canonical owner was settled as the username and
recorded.

Auth landed as a Django-minted, HMAC-signed, short-TTL token; the engine
verifies the signature and derives `owner_id` from the token. `owner_id` is not
a field on `AskRequest` at all — pydantic drops it, so nothing downstream can
ever see a client-supplied owner.

Rejections all shown failing: no token, tampered token, expired token. `/health`
stays open.

**The check that could have failed silently** — a valid owner returning three
real chunks with page numbers, against an owner who owns nothing returning zero.
Running it surfaced a genuine bug: `rerank()` crashed on an empty candidate
list, unreachable while every query scanned the whole corpus, and reachable the
moment tenancy existed. Fixed.

### The blocked item, and what was substituted for it

An end-to-end `/ask` under a valid token hit a live 429. The metered call was
never the point of that check — the claim was that the filter matches real
points, and that is a retrieval fact costing nothing. It was proved directly
instead, and only the end-to-end `/ask` was marked unproven-by-exhaustion.

What the 429 did prove, for free: it arrived from *inside* the Gemini call, past
every auth check — so token verification and dispatch into `run_agent` both
worked, with `owner_id` threaded all the way to the model node.

### T6.5 — the isolation test

Two users created through the real signup page, two image-free documents
verified at zero images before ingest, ingested through the real path.

Retrieval, via the same function the agent's tool calls: bruno's token returns
10/10 chunks all his; carla's returns 10/10 all hers; bruno's token carrying
carla's `doc_id` returns nothing — with a **control** showing carla's own
`doc_id` returns her chunks normally, so the zero is the owner filter working
rather than a broken filter returning zero for everyone. The executor added the
optional `doc_id` parameter and ANDed it with the token-derived `owner_id`, so
it can narrow within an owner and never across.

Forged-token rejection was run over real HTTP from a *different container*,
across the compose network, with the engine's port unpublished: forged secret,
no token, garbage, and a self-minted token claiming `owner_id=carla` — all four
401'd at the dependency before the route body ran. A positive control on
`verify_token()` proved the 401s were forgery, not broken auth.

### T6.C — the reproducibility gap

143 of 428 points came from PDFs that had been deleted after ingest. The corpus
is gitignored on the grounds that it is rebuildable from the filing — which had
quietly stopped being true.

Fixed rather than deleted: a generator committed to the repo, holding both
excerpts as literal constants and rendering them with PyMuPDF, no new
dependency. Determinism verified where it matters — two runs produce
byte-identical *extracted text*, the exact call `ingest.py` makes — with the
honest caveat that raw PDF container bytes are not stable and nothing downstream
reads them.

The original synthetic content is gone and unrecoverable, so the new counts are
a fresh baseline. Said plainly rather than presented as a restoration.

---

## Decisions locked

- Tenancy is payload-field in a single collection, `owner_id` indexed with
  `is_tenant: true`, per Qdrant's current guidance rather than recalled memory.
- The canonical `owner_id` is the **username string**, not Django's pk.
- The engine authenticates its own caller. `owner_id` is derived from a signed
  token and never read from a request body.
- The owner filter lives inside the Qdrant query, not in post-filtering of
  results.
- The engine's port is not published to the host. This narrows exposure and is
  explicitly *not* claimed to authenticate container-to-container traffic.
- Django owns the Postgres database. The engine neither reads nor writes it.
- Ingest is incremental and per-document. Delete-and-rebuild is dead.
- Anything in the vector store must be rebuildable from the repo, or it does not
  stay.
- Turn 6 is **not** complete and will not be logged as complete.

---

## Hard-won lessons

**On what a survey is for.** Three of my brief's assumptions were wrong — a seam
that did not exist, a document model that did not exist, and a threat I framed
as future which was already live. The survey bucket cost one round and saved a
design built on fiction. Ask the executor what the repo contains before
designing against what I imagine it contains.

**A filter that matches nothing is indistinguishable from a filter that works.**
This is the session's most transferable lesson. Every isolation check in T6.4
and T6.5 needed a positive control beside it, or the whole layer could have
passed while being completely broken. The username-vs-pk gate existed only
because that failure mode is invisible from the passing side.

**Tenancy makes previously unreachable code reachable.** `rerank()` had a crash
on empty input that could not fire while every query returned the whole corpus.
Narrowing the search surface is a behaviour change, not just a security change.

**A container declared in compose is not a container that runs.** `shell/` had
been in the stack since Turn 1 with a Dockerfile that could not have started.
Five turns of "the stack is up" meant four containers, not five, and nobody
counted.

**Our own guardrail disagreed with the provider.** The local quota counter read
"fresh day, zero used" while Google returned 429. It compares a stored date
string to UTC today and knows nothing about Google's actual reset window. On
free tier that mismatch is harmless. It stops being harmless the moment a card
is attached.

**Claude's own errors, logged honestly.**

- *I wrote a brief whose premise was false.* T6.1a asked how Django reaches the
  engine. There was no Django. The survey caught it because I made it a survey,
  but I had already written two prior briefs assuming a shell that worked.
- *I nearly let the metered blocker stall a free check.* When the 429 hit, the
  offered options were all framed around whether to spend. The actual claim
  under test — does the filter match real points — never needed a model call at
  all. I caught it, but the framing came within one keystroke of accepting a
  documented gap in place of a test that was free.
- *I did not ask whether the shell's port was published before promising
  Manglam a URL.* Same class as S17's wrong-input baseline: an assumption about
  the repo, stated to him as fact, that I could have resolved with one question.
  It happened to be true.

---

## Next session

**Turn 6's other half — the product shell.** Dashboard, upload and library,
chat, answer viewer, trust dashboard. This is the session where the last few
weeks of work becomes something openable in a browser. The `frontend-design`
plugin becomes worth installing here and not before.

**Before any of that, the paid-tier decision.** Manglam has offered to move off
free tier. The call: yes, but the judge-key ceiling gets built *first*, because
free tier's 429 has been the safety net for every unbounded loop in this
project, and paid tier removes it. Order of protection: per-project API quota
caps in the console (the only real hard stop), a separate GCP project, a small
billing budget with alerts, the ceiling in code, the counter-divergence fix, a
cap on internal retry multipliers, and a low-limit card.

**Debt carried out of this session:**

1. **A live authenticated `/ask` has never run** — the one call that proves
   auth, tenancy, and the agent together. Turn 6 cannot be called complete
   without it.
2. **The judge key has no counter and no ceiling.** Tracked, deliberately
   unbuilt, and now blocking the paid migration.
3. **The quota counter's day-rollover disagrees with the provider's.**
4. **`/admin/` is anonymously reachable** — harmless today with no data behind
   it, not harmless later.
5. **Password reset is a live URL with no `EMAIL_BACKEND`** — it exists and
   would break if used.
6. **Retrieval precision still fails at 0.774**, unchanged. One lever tried and
   reverted in S17; the next one must not be a guess.
7. **`figure-grounded` never attempted** — one-figure corpus.
8. **Standing:** Qdrant `:latest` image pin (Turn 7) · GPU passthrough
   (deferred) · `.env.example` trailing newline.

**HR questions locked this session:** Q16 (architecture) gains its strongest
material yet — a real tenancy design with a written threat model, chosen against
current vendor guidance, enforced below the UI. Q17 (what would you do
differently) gets the unpublished-port finding: a security hole that lived
through five turns because nobody asked who could reach the engine. Q13/14/15
gain the username-vs-pk gate — a bug caught before it could pass as a success.
