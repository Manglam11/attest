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
