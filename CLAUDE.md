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

## Where the build stands — Turn 5 CLOSED, Turn 6 (product shell) next

Turns 1–5 complete: walking skeleton, hybrid retrieval + reranker, multimodal
figures, agentic routing, trust + eval. Turns 6–7 (product shell, ship it)
untouched.

§02 table, complete — six of six rows measured or explicitly named as not:

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

Proven: agent answers all 15 gold questions correctly; refusal path works; the
verbatim refusal sentence is a programmatic seam.

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
  `latency_samples.json` tracked.
- Pins that are workarounds, not preferences: `ragas 0.4.3`,
  `langchain-community==0.3.31`, `jsonref`, and a direct `InstructorLLM`
  construction bypassing `llm_factory` (which cannot produce an async Google client).

## History

`docs/blueprint.pdf` is what we build. `docs/sessions/` holds sixteen session logs —
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