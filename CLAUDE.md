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
   the container, on disk.
3. **Anything metered gets resume + fail-fast from its first version.** Two API
   keys, two separate ceilings. Never spend without stating the cost first and
   waiting for a yes.
4. **Count API calls, not units of work.** One RAGAS metric fires ~10 internal
   calls. Budgets are in calls.
5. **Before any commit, reconcile `git status -s -uall`** — every file the work
   touched, including config and ignore files. Nothing dangles.
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

## Where the build stands — Turn 5 of 7, in progress

Turns 1–4 complete: walking skeleton, hybrid retrieval + reranker, multimodal
figures, agentic routing. Turn 5 (trust + eval) is open. Turns 6–7 (product shell,
ship it) untouched.

Judge complete: **12 of 12** answerable rows, scored under one embedder
(`BAAI/bge-small-en-v1.5`), mixed-ruler guard clean. faithfulness 1.000 ·
answer relevancy 0.979 — both pass. Hallucination flag passes: refusal 3/3 on
unanswerable rows. **Context precision 0.774 fails** the 0.85 target — a
measured, diagnosed failure, not a coverage gap. Cause: the reranker ranks
lexically-similar wrong tables (equity roll-forward, segment, deferred-tax)
above the answer-bearing chunk on three rows, plus one genuine miss buried at
rank 7/20 in the fusion pool. Fixing it is the scheduled Turn 2 retrieval
deepening pass — not open Turn 5 work.

p95 latency is the one §02 number still unmeasured, blocked on the agent key's
20 RPD ceiling rather than on engineering.

Proven: agent answers all 15 gold questions correctly; refusal path works; the
verbatim refusal sentence is a programmatic seam.

## Open, in priority order

1. **Harness latency resume path** — must re-derive latency on every read, not
   replay a cached value, or it silently defeats p95 sampling.
2. **p95 unmeasured** — needs ~10 fresh `/ask` calls against the 20 RPD ceiling.
   Size the run and get a yes before spending.
3. **`JOURNAL.md` does not exist** — the blueprint requires it. Seed it from
   `docs/sessions/`.
4. **`generate.py` orphaned** from `/ask` since the agent landed — decide:
   delete, or keep as a documented fallback.

## Environment

- Repo `~/02_dev/01_attest`, branch `main`. Everything lives on the E: external SSD;
  it must be mounted before Docker starts. Push at every session boundary.
- Containers: `attest_engine` (FastAPI, :8000) · `attest_shell` (Django, :8001) ·
  `attest_qdrant` (:6333) · `attest_postgres` (:5432) · `eval` (profile-gated,
  isolated image).
- Eval runs: `docker compose --profile eval run --rm -T eval python -m app.eval.<mod>`
- Two keys, two ceilings: `GEMINI_API_KEY` → agent (`gemini-3.6-flash`, ~20 RPD,
  the binding constraint) · `JUDGE_API_KEY` → judge (`gemini-3.5-flash-lite`).
  Secrets are passed per-key in compose; nothing inherits.
- Eval artifacts in `data/eval/`. `run_*.json` ignored, `judged_*.json` tracked.
- Pins that are workarounds, not preferences: `ragas 0.4.3`,
  `langchain-community==0.3.31`, `jsonref`, and a direct `InstructorLLM`
  construction bypassing `llm_factory` (which cannot produce an async Google client).

## History

`docs/blueprint.pdf` is what we build. `docs/sessions/` holds thirteen session logs —
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