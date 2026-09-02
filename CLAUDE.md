# Attest — Working Constitution

Multimodal, self-grading RAG over financial filings. Ingests SEC 10-Ks, answers in
plain English with page citations, reads figures via a vision model, and grades its
own faithfulness — flagging answers it cannot ground instead of inventing them.

The self-grading layer is the product, not decoration. Correctness before polish.

## Execution rules — these are load-bearing

1. **Label a hypothesis as a hypothesis.** Say "my suspect is X" and name the one
   cheapest command that confirms or kills it. Never state a diagnosis as fact
   before it has been tested.
2. **Report what you observed, not what you expect.** A status line, a "Started",
   a success message — none of these are evidence. Verify the actual value, inside
   the container, on disk. Any number heading into a persisted document gets
   re-derived at the point of writing, never carried forward from an earlier
   session or message — even one stated confidently. A wrong number outlives its
   own correction.
3. **Anything metered gets resume + fail-fast from its first version.** Two API
   keys, two separate ceilings. Size a run on the worst single cost observed so
   far, read from tracked evidence, never on an average. Never spend without
   stating the cost first and waiting for a yes.
4. **Count API calls, not units of work.** One RAGAS metric fires ~10 internal
   calls. Budgets are in calls.
5. **Reconcile `git status -s -uall` at the start of a session and before any
   commit** — every file the work touched, including config and ignore files.
   Nothing dangles.
6. **Before any destructive command, confirm it is not the only copy.** Backup
   first. The repo lives on an external SSD.
7. **Read the file before diagnosing the tool.** A setting that "isn't taking" is
   usually an unsaved edit, not a Docker bug. Read the module source, not the docs.
8. **No deprecated patterns.** Verify external model names and API surfaces are
   current before pinning them.
9. **Code stays comment-lean.** No teaching comments. Any comment that earns its
   place is written in Manglam's first-person voice.
10. **When the model and the ruler disagree, suspect the ruler first.** A gold key
    is unverified until you have read the row it sits in.

## The §02 contract — frozen, changed only with a defensible reason

| Metric | Target |
| --- | --- |
| faithfulness | ≥ 0.90 |
| retrieval precision | ≥ 0.85 |
| answer relevance | ≥ 0.85 |
| hallucination flag | < 0.50 |
| figure-grounded | ≥ 80% (aspirational) |
| p95 latency | ≤ 8s |

## Where the build stands — Turn 6 (product shell), one bucket short

Turns 1–5 complete: walking skeleton, hybrid retrieval + reranker, multimodal
figures, agentic routing, trust + eval. Turn 7 (ship it) untouched.

Turn 6 — tenancy through T6.5: Django on Postgres with real signup/login/
logout; ingestion is incremental and owner/doc-scoped; the engine verifies a
signed token and derives `owner_id` from it, never from the request body;
two-tenant isolation is proven, including a forged-token-rejection control
(see `JOURNAL.md`, "Turn 6 — Product Shell (Tenancy)", and
`docs/decisions/0001-tenancy.md`). Current collection: 304 points —
`alice`/`aapl_10k` 285 (real filing, re-fetchable per `.gitignore`),
`bruno`/`bruno_10k_excerpt` 10, `carla`/`carla_10k_excerpt` 9 (both
rebuildable from the committed `engine/app/gen_synthetic_corpus.py`).

Sessions 18–19 brought the shell up as a running product — base template,
four pages, a working chat view on published port 8001 — and ran the first
live authenticated `/ask`, closing the "wiring proven, never fired
together" gap. Surfaced and fixed: gunicorn's 30s worker timeout against a
~196s worst-case engine latency (now 220s). Surfaced and left open: the
shell's exact-string refusal check failing against a real, chatty refusal.

Session 20 (T6.11–T6.18b) closed that refusal bug and built the rest of the
product shell:
- `/ask` now returns structured `sources` (`doc_id`, `owner_id`, `page`,
  reranker `score`) alongside `contexts` — untouched, still `list[str]`,
  still what the Turn 5 eval harness and judge consume — plus an explicit
  `refused` boolean. The refusal sentence collapsed from three drifted
  copies (agent prompt, judge, shell) to one canonical module the engine
  imports; the shell holds zero copies, verified by grep.
- Postgres gained its first application tables: `AskRecord` (one row per
  ask, written on success, refusal, and error alike) and `Document` (one
  row per owned document, driving the library without scanning Qdrant).
- Two real metered calls proved the stack live, through the browser: one
  refusal (`refused=True`, 4 quota units, 40.5s, 3 retrieval round-trips)
  and one grounded lookup (`112,010` exact against the gold key, 2 units,
  14.1s, 1 round-trip). Both rows and their source cards verified in
  Postgres, not assumed from the response.
- History (list + detail, per-user isolated), a trust dashboard (frozen
  §02 numbers from the Turn 5 judged run — including the failing 0.774
  precision tile, rendered as a visible FAIL, not hidden — plus a
  "not scored" recent-asks list that never invents a score for a live
  answer), and a library (backfilled for all three tenants, every field
  traced to Qdrant or the source PDF, `ingested_at` left null where no
  honest source exists) all exist and are proven against live data.
- Upload does not exist yet. A real phase-timed ingest (65-page filing,
  44.7s total) and a genuine defect — `ingest.py`'s vision call has spent
  `GEMINI_API_KEY` untracked since Turn 3 — are the blocking inputs to
  that design now, both detailed under Carried Forward below.

**Turn 6 is not complete** — logged as one bucket short (upload), not as
done, per Session 20's own decision.

§02 table — untouched this session, still six of six rows measured or
explicitly named as not:

| Metric | Target | Measured | Verdict |
| --- | --- | --- | --- |
| faithfulness | ≥ 0.90 | 1.000 (n=12, one embedder) | PASS |
| retrieval precision | ≥ 0.85 | 0.774 (n=12) | **FAIL — diagnosed** |
| answer relevance | ≥ 0.85 | 0.979 (n=12, one embedder) | PASS |
| hallucination flag | < 0.50 | 0/3 (3/3 unanswerable correctly refused) | PASS |
| figure-grounded | ≥ 80% (aspirational) | not attempted — one-figure corpus | n/a |
| p95 latency | ≤ 8s | n=7, all > 8s (43s–196s); 95%-confidence upper bound on the share below 8s ≈ 35% | **EXCLUDED, not narrowly missed** |

Retrieval precision's cause, re-diagnosed in the Turn 2 deepening pass
(Session 17): the paragraph this replaces was itself wrong — its baseline
had run on the wrong query text and never reproduced. The corrected
baseline is 11 of 12 gold rows clean; the reranker demotes the correct
chunk below its fusion-pool rank on exactly two rows (operating income:
rank 2→4; cash/securities: rank 4→5), both still inside the top-5 cutoff.
The 12th row is a derived arithmetic answer that never appears verbatim in
the corpus by construction — not a retrieval miss — and is now scored by
operand presence instead of the unattainable literal value. A
higher-capacity reranker (568M vs the deployed 278M params) was tried
against the two demotions and reverted: precision moved +0.0095 on the
comparable rows while per-call rerank cost roughly quadrupled (5.7s →
23.9s mean, warm) against an already-excluded p95 budget. Both demotions
are now a known, unfixed behavior, not an open unknown — the 0.774 judged
score stands unmoved, and the next lever for it isn't a bigger CPU
reranker. p95's cause is not yet isolated — that diagnosis is owed
whenever latency work resumes, not claimed here.

Proven: agent answers all 15 gold questions correctly; refusal path works, now
decided by an explicit `refused` flag the engine reports rather than any
consumer matching answer text; the trust dashboard renders both the passing
and the one failing §02 metric live, on a page a user can actually open.

## Carried forward, past Turn 5

- **Turn 2 retrieval-deepening pass** — closed (Session 17) with a null
  result: diagnosis above re-derived, a bigger reranker tried and
  reverted. The two demotion rows (operating income, cash/securities) are
  carried forward unfixed; the retrieval-precision contract row stays at
  0.774, FAIL.
- **p95 root cause** — not isolated. Instrument before further sampling.
  Retrieval is not the lever at the deployed reranker: 4.7–13.2% of
  observed ask latency, warm (`data/eval/retrieval_timing_20260902T012156Z.json`).
- **Judge key has no counter or ceiling** — unlike the agent key, `JUDGE_API_KEY` is protected only by fail-fast-and-resume on 429; not building one in Turn 6, which spends nothing metered.
- **The local agent-quota counter tracks this project's calls, not Google's
  free-tier state** — the two can disagree, and the counter's UTC-day
  rollover need not match the provider's own window. Live end-to-end `/ask`
  is no longer blocked on this (Session 20 ran it twice, see below); the
  divergence risk itself is unresolved and applies to any future metered run.
- **Ingest cannot run from Django, and has never been timed end to end** —
  `engine/app/ingest.py:171`'s `ingest(pdf_path, owner_id, doc_id)` is a
  clean importable function, but its ML dependencies (pymupdf,
  sentence-transformers, fastembed) live only in the engine image, not the
  shell's; and `data/corpus` is mounted `:ro` into the engine, so nothing
  can write an uploaded file there today either. A real phase-timed ingest
  of the 65-page `aapl_10k.pdf` (Session 20, T6.18b) measured 44.7s total:
  PDF extraction 0.32s, chunking 0.01s, figure/vision (1 figure) 12.99s,
  dense model load 5.32s, dense embed compute 25.32s, sparse model load
  0.39s, sparse embed compute 0.11s, Qdrant upsert 0.26s. Model-load tax
  (dense+sparse load, not compute) is 5.71s of that, 12.8% — fixable by
  caching the models once like `retrieve.py` already does instead of
  reloading them inside `embed_chunks`/`embed_chunks_sparse` on every call;
  not fixed here. This is a single 65-page/1-figure sample, not a rate —
  a larger or more figure-heavy filing is not bounded by this number,
  especially since vision was the largest single non-embedding phase and
  scales with figure count, not page count. Upload's execution model
  (sync/background/deferred) is not decided; it was deferred to the next
  session pending exactly this data.
- **`ingest.py`'s vision call spends `GEMINI_API_KEY` untracked** — found
  while timing the ingest above. `QuotaCounterCallback` (`quota.py`) only
  hooks `on_chat_model_start` on the langchain agent's model, wired in
  `agent.py:89`; `ingest.py:88`'s `client.models.generate_content(...)` is a
  direct `genai.Client` call with no callback attached, so every figure
  vision call since the multimodal pipeline landed (Session 08) has been
  invisible to `data/quota/agent_calls.json`. Scope, checked locally with no
  API spend: the current corpus has exactly one qualifying figure (>=200px,
  `aapl_10k.pdf` page 24) — a full re-ingest of everything today spends
  exactly 1 untracked call. A hypothetical uploaded 96-page filing with 20
  figures would spend ~20 untracked calls, uncounted and uncapped. This is a
  blocking input to the upload design, not a footnote: a user-facing upload
  button must not make an unbounded, uncounted number of paid calls per
  file. Not fixed here — reported per the instruction that found it.
- **No OCR path and no failure detection** — `ingest.py`'s `extract_pages`
  is bare `page.get_text()`. A scanned PDF would not error; it would
  silently produce ~0 chunks. The `Document.status` field can express
  `failed` (Session 20, T6.18b) but nothing produces that state yet —
  detecting it is upload's job.
- **`context_precision_proxy.py` cannot import inside the eval image** —
  `fastembed` is absent from `requirements-eval.txt`. Pre-existing,
  surfaced while verifying T6.13, unrelated to it.
- **The engine returns markdown; the shell renders it raw** — `**bold**`
  is visible verbatim in the browser. Cosmetic, not yet fixed.
- **`alice` is a fixture used as a human account** — password reset twice
  now (Session 19, Session 20), both times because the prior value was
  unrecoverable and undocumented on purpose. Compounding, not resolved.
- **Cross-tenant negative proof at the response level has never run** — no
  session has asked bruno or carla an Apple-specific question and confirmed
  zero alice-owned sources come back. T6.13's retrieval-level control
  (swapping `owner_id` changes the returned `doc_id`) stands in for it but
  is not the same claim.
- **`/admin/` is reachable anonymously; password reset has no
  `EMAIL_BACKEND` configured.** Standing since tenancy landed.
- **Standing, deferred to Turn 7:** Qdrant's `:latest` image tag is unpinned;
  GPU passthrough has never been attempted.

## Environment

- Repo `~/02_dev/01_attest`, branch `main`. Everything lives on the E: external SSD;
  it must be mounted before Docker starts. Push at every session boundary.
- Containers: `attest_engine` (FastAPI, :8000) · `attest_shell` (Django, :8001) ·
  `attest_qdrant` (:6333) · `attest_postgres` (:5432) · `eval` (profile-gated,
  isolated image).
- Eval runs: `docker compose --profile eval run --rm -T eval python -m app.eval.<mod>`
- One ceiling, not two: `GEMINI_API_KEY` → agent (`gemini-3.6-flash`, ~20 RPD) has a
  persisted counter+ceiling; `JUDGE_API_KEY` → judge (`gemini-3.5-flash-lite`) has
  neither — only fail-fast-and-resume on 429. Secrets per-key; nothing inherits.
- Eval artifacts in `data/eval/`. `run_*.json` ignored; `judged_*.json` and
  `latency_samples.json` tracked. Mounted read-only into `attest_shell` too
  (Session 20, T6.17) so the trust dashboard can read them — it had no path
  to this directory before that.
- Pins that are workarounds, not preferences: `ragas 0.4.3`,
  `langchain-community==0.3.31`, `jsonref`, and a direct `InstructorLLM`
  construction bypassing `llm_factory` (which cannot produce an async Google client).

## History

`docs/blueprint.pdf` is what we build. `docs/sessions/` holds twenty session logs —
read the newest first; each one supersedes older claims. `JOURNAL.md` is the
per-turn record of real problems and concrete fixes.
- **Resume paths re-validate cached fields; they do not replay them.** Three
  instances in this build: the judge write-merge (a partial run dropped rows
  scored earlier), the judge embed provenance (a cached score outlived the
  embedder that produced it), and the harness gold keys (a cached run record
  outlived a gold-set correction). Every resume-from-disk feature must state
  explicitly which fields are safe to reuse verbatim and which must be
  re-derived from current source of truth on every read. Reuse by default is
  the bug, not the exception.