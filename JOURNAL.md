# Attest — Build Journal

Session logs record what happened, for whoever picks the project back up.
This is different. This is for the interview: one real problem per turn, what
it cost, what actually fixed it, and what I'd carry into the next project. If
you could write an entry from the commit messages alone, it isn't in here.

## Turn 1 — Walking Skeleton

`/ask` kept saying the Gemini key was missing, even sitting right in `.env`
next to `docker-compose.yml`. The mistake was assuming one `.env` file does
one job. It does two, unrelated: filling `${VAR}` placeholders inside the
compose file itself, and injecting a variable into a container's own process
environment so `os.getenv` can see it. Postgres had the second wired through
`env_file`; the engine service had neither. Fix was one explicit
`environment:` line on the engine service, then a container *recreate*, not a
rebuild — it was a config change, not a dependency change. I'll carry this
into every docker-compose project from here: two separate mechanisms, and the
file's placement makes them look like one.

## Turn 2 — Retrieval Quality

Measured retrieval precision looked stuck lower than a reranker should have
allowed. The reranker wasn't the problem — my own gold set was. The model
answered `34,550` for R&D spend, which is correct; my gold key said `31,370`,
which is last year's number, one column to the left on the same income
statement line. A second key, cost of sales, was pointing at income-before-
taxes (`132,729`) instead of the real line (`220,960`). Both survived a review
I'd already done specifically to catch this exact trap — the ten-K prints
three years of numbers side by side, and I still keyed the wrong column twice.
It only surfaced because an unrelated fix, page provenance, put the full raw
source page in front of me for the first time, and the mismatch between what
the model said and what the page actually showed was impossible to miss. I
didn't patch just the one caught key — re-verified all six against the filing
by grep and corrected both. A wrong ground truth doesn't fail loudly; it
silently mis-scores a system that's actually right, forever, until something
forces you to look at the source next to the number instead of the number
alone.

## Turn 3 — Multimodal

Extracted figures kept vanishing. First cause: I wrote them to `/code` inside
the container — its writable layer, gone on every rebuild — instead of giving
them a mounted, persistent home from the start, the same mistake I'd already
made once with a scratch file in Turn 2. Fixed with a real volume mount. Then
it happened again in a different shape: after adding the new mount line to
`docker-compose.yml`, `docker compose up -d` printed `Running 0.0s` and the
figure still wasn't there. Docker only applies a volume change when a
container is *created*, never when an existing one is reused —
`--force-recreate` is required, and "`Running 0.0s`" versus "`Started`" in the
log is the tell that something didn't actually take. Once the pipeline held
together, the payoff: the vision model's read of the five-year stock
performance chart (~$235 Apple, ~$215 S&P) landed within about 1% of the
filed data table underneath it ($234 / $217) — validated against real, filed
numbers, not eyeballed. Lesson, in two parts: give a reused file its permanent
home the moment you know it'll be reused, and read a Docker status line as a
real signal, not noise to scroll past.

## Turn 4 — Agentic

A single `/ask` call took 62 seconds against an 8-second target, and my first
diagnosis of it was wrong. I'd already fixed per-call model reloading with
module-level singletons and proven it fast in a bare Python harness. Wired
into the real FastAPI process it was still 62s, so I guessed the uvicorn
`--reload` watcher was defeating the singletons — logged the hypothesis, moved
on. It was wrong. Timing prints the next session showed the singletons loading
exactly once; the entire 62 seconds was a single function — reranking 20
candidate chunks with a 568M-parameter cross-encoder, on CPU, on every
`retrieve` call. The agent's ReAct loop calls `retrieve` more than once per
question, so a cost that was invisible in the old one-shot pipeline stacked
openly the moment the architecture went agentic. Fix was a one-line model
swap to a lighter reranker (278M params) — no GPU, no redesign — cutting a
single retrieve call from 62s to about 5.6s. I named the honest caveat at the
time instead of hiding it: fixing the single-call case doesn't guarantee the
compound, multi-step case stays under budget — that got flagged for eval to
answer, not swept under. The lesson that mattered most: a hypothesis is still
a guess until it's timed, even when — especially when — it's my own.

## Turn 5 — Trust + Eval

The judge died on `429 aiplatform.googleapis.com` at row five, and the wall
wasn't the one I'd budgeted for. I'd paced the run around the judge LLM's
15-RPM ceiling. Reading `ragas`'s own source — not its docs — produced the
exact per-metric call inventory, and one deliberately spent metered row
caught the untruncated error:
`aiplatform.googleapis.com/global_embed_content_requests_per_minute_per_base_model`,
base model `gemini-embedding`. A plain AI-Studio key, with Vertex never
configured anywhere in the code, was being metered against a Vertex-side
quota invisibly — on the first embedding call this project had ever made,
after only eight had ever fired. I didn't negotiate with a dependency I
couldn't see the terms of. I killed it: swapped the remote embedder for a
local `sentence-transformers` model running off the mounted HF cache, so eval
now carries zero metered embedding dependency, permanently.

That migration opened its own trap. A score computed under the old remote
embedder and one computed under the new local one aren't the same ruler, even
though they share a metric name — a resumed run could silently average across
both and print a number that means nothing. That's when I recognized the
shape: I'd hit this exact failure twice before under different names — a
partial judge run dropping rows scored in an earlier pass, and, this session,
a harness that kept replaying a gold answer key I had already corrected at
the source. Three subsystems, one root cause: a resume path re-serving
whatever was on disk without asking whether it was still true. I named the
pattern, promoted it into the project's standing rules, and built a guard
into the judge that refuses to average a score across mixed embedders instead
of printing a number that merely looks like one.

That same discipline is why this session's p95 number is trustworthy rather
than convenient. I rebuilt the latency sampler so a resumed run can never
replay a stored latency as a fresh draw. Under that guarantee, seven fresh,
engine-timed observations came back before the real Gemini daily ceiling
stopped the run — all seven above 8 seconds, from 43s to 196s. With zero of
seven below the target, the 95%-confidence upper bound on the true share of
the response-time distribution that falls below 8 seconds is about 35%, and a
passing p95 needs at least 95% below it. The contract isn't narrowly missed —
it's excluded; the evidence caps the passing share at roughly a third of what
the target requires. Unlike context precision, which is already root-caused
(a reranker fooled by lexically similar wrong financial tables) and scheduled
as a Turn 2 deepening pass, latency's cause isn't isolated yet — that's
honest future work, not this session's claim to make. The instinct that ties
the whole turn together: don't trust a number until you know exactly what
produced it, cached or otherwise — it's what let this project report its own
contract failure instead of finding a way to round it into a pass.

## Turn 2 Revisited — Retrieval Deepening (Session 17)

The diagnosis I closed Turn 5 with was wrong, and I found that out by trying
to reproduce it before touching anything. "The reranker ranks lexically
similar wrong tables above the answer, plus one genuine miss at rank 7 of
20" turned out to describe a baseline run that had queried the corpus with
the wrong text — not the agent's actual queries. Rerun cleanly, the shape
was different: 11 of 12 gold rows clean, and exactly two rows where the
reranker demotes the correct chunk below where fusion already had it
(operating income, rank 2 to rank 4; cash and securities, rank 4 to rank 5).
The twelfth row isn't a retrieval miss at all — its gold answer is arithmetic
that never appears verbatim anywhere in the filing, so it can never surface
by construction. My own scoring check had been holding retrieval responsible
for a number retrieval could never find; I fixed the check, not the
retrieval, once I saw that the "miss" was a ruler problem, not a system one.

With an honest diagnosis in hand — two demotions, both inside the top-5 cut
— the obvious lever was a bigger reranker. I built a free proxy first: a
local re-scoring of the agent's persisted queries that reproduces the RAGAS
judged context-precision score exactly on 11 of 12 rows, so I could measure
a swap without spending a single metered judge call. Swapped in a
higher-capacity cross-encoder (568M params against the deployed 278M),
reran the proxy once, and decided on that one run rather than iterating
until the number looked better. The result was a null: +0.0095 on the
comparable rows, and not a clean win even at that — three rows regressed,
one of them (cash/securities) going from a partial hit to missing entirely,
and both original demotions got worse, not better, under the larger model.
Meanwhile its warm per-call cost was roughly four times the deployed
model's — 5.7s mean going to 23.9s, with two calls spiking past 58s — against
a p95 budget the project is already excluded from, not narrowly missing. A
marginal, mixed precision gain bought at a 4x latency cost that lands on an
already-failing metric isn't a trade worth taking. I reverted it and
confirmed the revert at weight level rather than trusting the commit
message: 278,044,417 parameters back on disk, not 567,755,777.

Nothing in the §02 contract moved this session. Retrieval precision is still
0.774, still FAIL, on the same judged run as before — I never spent a judge
call, because the proxy's own result didn't clear the bar for asking whether
the real metric agreed. What I have instead is better than a number that
didn't move: a diagnosis that actually reproduces, a zero-cost ruler I can
reuse the next time a retrieval change is proposed, and two specific rows
that are now a known, unfixed behavior rather than an unexamined one. I'd
carry the proxy pattern into any project with a metered grader — validate a
free local approximation against the expensive ground truth once, then
spend real judge calls only on changes the free ruler says are worth it.
And I'd carry the discipline that produced the null result in the first
place: run the experiment once, report what it actually showed even when
that's "no," and don't let a plausible-sounding fix ship on the strength of
its story instead of its measurement.

## Turn 6 — Product Shell (Tenancy)

The brief was one sentence — two users cannot see each other's corpus — and
the survey I ran before writing anything found out how little of that was
already true. The engine's FastAPI port had been published to the host since
Turn 1. `/ask` was reachable from any process on this machine, unauthenticated,
for five turns, and nobody had noticed because nothing had ever needed it to
be private until a second tenant made the question unavoidable. Fixing it was
one compose line — stop publishing the port, move the healthcheck inside the
container. The lesson isn't the line, it's that an open port doesn't announce
itself; it sits there passing every test you happen to run, because none of
those tests are "is this reachable from somewhere it shouldn't be."

The shell had the same shape of problem in miniature. Django had been running
on sqlite behind a Dockerfile that had, as far as I can tell, never actually
been built and run end to end — Postgres was already provisioned in compose,
unused. When I finally exercised that Dockerfile, the last line was a second
copy of the `uv` binary-copy instruction, pasted where a `CMD` should have
been. The image built without error and would have failed the instant
anything tried to run it, because it had no entrypoint at all. A Dockerfile
that has never been run isn't verified, it's just untested code with a
misleading file extension — the build succeeding tells you nothing about the
one instruction that only matters at `docker run`.

Both of those are the same failure with different costs: something absent
(auth, a CMD) leaves no trace of its absence until an unrelated requirement
forces someone to actually invoke the path. Tenancy's own test carries the
antidote. Proving alice only sees alice's chunks is not proof the owner
filter works — if the filter were silently a no-op, or if `owner_id` were
being read from the request body instead of the verified token, a
single-tenant test would still pass, because there would be nothing else in
the store to leak. The filter earns its claim only against a case designed to
break it: a second tenant's data actually present, and a forged token
presented and rejected before it ever reaches the query. A match is not
evidence the mechanism ran; a correctly-rejected forgery is. I'd carry that
into any access-control feature: write the negative test first, because the
positive one alone can't tell a working filter from an absent one.

Turn 6 is not complete. T6.0–T6.5 are done — Django on Postgres, incremental
owner- and doc-scoped ingest, signed-token auth on the engine, two-tenant
isolation proven with the forged-token control above. What never got proven
is the thing the whole turn is for: an authenticated ask, through the shell,
end to end, with a live model answering it. The free-tier Gemini quota was
exhausted before that run happened, and I did not spend against a paid tier
to force it this session. That's the honest state to hand off — the wiring
is proven at every seam I could test for free, and the one call that proves
all the seams together at once is still unmade.

That call happened this session. One question — Apple's fiscal 2025 net
income — through a Django-minted token, into the engine, and back with the
right figure and page citations, tool_calls showing a self-composed
retrieval query rather than a hardcoded one. It closes a gap the forged-token
control could never close by itself: rejecting a bad token proves the check
rejects what it should, but nothing before this proved it *accepts* what it
should. A system that rejects every token passes a forged-token test
perfectly while being useless — only a call that succeeds distinguishes
"the check works" from "the check rejects unconditionally." Everything free
around that seam got proven the session before spending anything: health
checks, missing and unresolvable engine addresses failing in under a second
instead of hanging to a timeout, forged and malformed tokens rejected with a
clean error instead of a crash. The plan named the one thing free testing
structurally cannot produce — a positive auth control — and declined to
fake it rather than dress up the negative case as proof of the positive one.

Building the page in front of that seam surfaced a bug with nothing to do
with tenancy: gunicorn's worker timeout defaults to 30 seconds, and the
engine's own worst observed `/ask` latency is ~196 seconds. Nothing in five
sessions of engine work had ever run a slow query through the Django process
sitting in front of it, so nothing had ever hit this. Shipped as built, the
failure would have looked like a frontend problem — a stuck request, a
dropped connection — when the actual fault was a server config value nobody
had ever needed to move off its default. It's the same shape as this turn's
opening finding, an unpublished port invisible for five turns because
nothing had ever asked it to be private: something silent that only breaks
the first time a real requirement forces the path to run at its actual worst
case, not a synthetic one. Found by asking what the timeout even was before
building a UI on top of a call known to run long, not by watching it fail.
Fixed at `--timeout 220`, clearing the client's own 210s ceiling — but the
lesson is to check every implicit ceiling in a chain, not just the one just
tuned, because whatever eventually sits in front of a genuinely slow call
gets to have an opinion about how long is too long, whether or not it was
consulted.

One more bug came out of that same page, caught, not fixed. The refusal
card — the UI's way of showing "no grounded answer" as success, not
failure — is chosen by one line comparing the engine's answer against the
canonical refusal sentence with exact string equality. That passed clean
against a mocked response built to be exactly that sentence and nothing
else, because a mock can only ever be exactly what it was written to be. It
failed against a real refusal in the browser: the model led with the
refusal sentence and then kept going, adding grounded figures after it, so
the full answer's prefix matched but the full string did not. Equality was
never going to survive contact with a model that's allowed to keep talking
after it refuses — only a real, ungrounded question asked of a real model
could have produced the input that broke that assumption, and no amount of
mock design would have found it first. Left open on purpose, as the first
item of the next session rather than a fix bolted onto the end of this one.
