# 🧭 Attest — Session 12: The Harness Runs — Correct Retrieval, Wrong Numbers

> **📚 Format note.** Logs are a **stack** — one `.md` per session. Each carries a **Status Board**
> (latest file alone re-anchors everything) and a **⚠️ Supersedes** section (no older file can
> quietly contradict a newer one).
>
> **Cold-start reading order:** 📄 `Attest_Blueprint_v1.pdf` → 🗒️ the **latest** session log →
> 📋 Instructions.

---

## 🚦 Status Board

|                       |                                                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Current phase**     | **Turn 5 (trust + eval) IN PROGRESS.** The eval *plumbing* is built and the full gold set is collected. The RAGAS **judge itself is not yet written** — `judge.py` is next session's opening move. |
| **Last session**      | [12] — surfaced retrieved contexts through `/ask`, stood up an isolated eval container, built a resumable collection harness, collected all 15 gold questions, and found a real correctness bug: **the agent answers multi-year table questions with the wrong year's number.** |
| **What exists**       | Everything from S11 **plus**: **(1)** `/ask` now returns `contexts` — deduped, chunk-level, split on the `[page N]` marker from `tools.py`; **(2)** `engine/Dockerfile.eval` + `requirements-eval.txt` + a **profile-gated `eval` service** (never starts on a normal `up -d`); **(3)** `engine/app/eval/harness.py` — fires the gold set at `/ask`, records answer + contexts + tool_calls, **resumes** from prior runs, paces requests; **(4)** `data/eval/run_*.json` — **15/15 questions collected, 0 failed**, now version-controlled. **No RAGAS judge yet, no auth, no p95 number.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM). GPU still unused. |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`. This session: **4 atomic Conventional Commits** (contexts / eval-container / harness / versioned-runs). |
| **The build**         | **Turn 5.** Collection half done. Remaining: write `judge.py` (RAGAS over the collected JSON), produce faithfulness / answer-relevance / context-precision, grade the refusals, and fix the wrong-year generation bug. |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). **No metric can be claimed yet.** p95 ≤ 8s is currently **unmeasurable** — see Supersedes. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL + an isolated eval image (ragas 0.4.3). |
| **Domain / corpus**   | Financial. Apple 10-K FY2025, 285 records. Gold set = 15 string-anchored pairs. |
| **Next action**       | **Fresh chat.** Write `engine/app/eval/judge.py` — reads the newest `data/eval/run_*.json`, scores each sample with `ragas.metrics.collections`, writes results beside it. Then diagnose the wrong-year bug. |
| **Open question**     | Is the wrong-year answer a prompt problem (no instruction to prefer the leftmost/current column) or a chunk problem (the three-year rows split so the year headers separate from the values)? Decide with the contexts already on disk — no API calls needed. |

---

## ⚠️ Supersedes

- **THE HEADLINE — hit rate was hiding a correctness bug. `12/12 hit rate` from S11 does NOT mean 12 correct answers.** Running the full gold set through the *agent* path (not the retriever) exposed **2 confidently wrong answers**: total assets answered **`359,241`** when the filing says **`364,980`**; operating income answered **`133,050`** when the filing says **`123,216`**. Both wrong values were **present in the retrieved contexts**, and both answers carried a page citation. So: **retrieval succeeded, generation picked the wrong fiscal-year column.** This is the S06 comparative-statement trap (a 10-K prints three years side by side) reappearing on the *generation* side. The string scorer is structurally blind to it — it only asks whether the right chunk arrived, never whether the answer used it.

- **The S11 latency numbers cannot be carried forward — and no p95 exists yet.** The first harness run showed 54–117s per question. That is **not pipeline cost**. AI Studio confirms `gemini-3.6-flash` on this project is **5 RPM / 20 RPD** (free tier), so LangChain was backing off against a per-minute wall. The only near-clean readings were 13.7 / 15.4 / 15.2s. **Do not quote any latency figure from this session.** p95 gets measured once the quota stops distorting it.

- **Free-tier quota is per PROJECT, not per API key** (Google's own rate-limits page). A second key inside the same project shares the same bucket — confirmed live when the old project's counter climbed 21 → 25 while we believed we had switched keys. Key separation requires a **separate project**.

- **RAGAS lives in its own container, NOT in the engine.** `ragas==0.4.3` drags in `langchain-community`, `langchain-openai`, `openai`, `datasets`, `instructor`. Putting that in the engine image would bloat the deploy shell and risk resolving LangChain v1 downward. Instead: `Dockerfile.eval` + `requirements-eval.txt` + a `profiles: ["eval"]` service. The engine's dependency tree is untouched.

- **`ragas.metrics` is deprecated; the real API is `ragas.metrics.collections`** — and RAGAS's own deprecation message is wrong about the names. It tells you to import `ResponseRelevancy` and `LLMContextPrecisionWithoutReference` from collections; those don't exist there. The actual names are **`AnswerRelevancy`** and **`ContextPrecisionWithoutReference`** (plus `Faithfulness`).

- **Collections metrics are async and per-sample — there is no `evaluate()` orchestration.** Each metric is `await metric.ascore(...)`. `Faithfulness` and `ContextPrecisionWithoutReference` take `(user_input, response, retrieved_contexts)`; `AnswerRelevancy` takes only `(user_input, response)` plus an embeddings model at construction. This is *better* for us: per-question scores (no averaging away a bad question) and we control pacing against rate limits.

- **`ragas==0.4.3` is broken against `langchain-community>=0.4`.** It hard-imports `langchain_community.chat_models.vertexai`, removed in the 0.4 line. Pinned **`langchain-community==0.3.31`** in the eval image. Revisit when RAGAS patches it.

- **Judge model pinned = `gemini-3.5-flash-lite`** (stable, not preview, own quota bucket, and judging is extraction/classification work — not long-form reasoning). Embeddings = `gemini-embedding-001`, verified live at **100 RPM / 1K RPD** with only 119 used. Deliberately **not** the `-latest` alias: a floating tag would silently change what produced the §02 numbers.

---

## 🎯 Session goal

**Wire RAGAS and produce the judged §02 numbers.** Half delivered: the collection path is built and the data is on disk. The judge itself was pushed out by a full session of quota archaeology.

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T5.0** | Resume gate — E: mounted, containers Up, tree clean.                            | ✅ |
| **T5.5** | Wire RAGAS — verify API live, isolate deps, pin judge model.                     | ✅ container built, API pinned |
| **T5.6** | Harness — run the gold set through `/ask`, capture answer + contexts.            | ✅ 15/15, 0 failed |
| **T5.7** | Judged numbers — faithfulness, answer relevance, context precision.               | ❌ carried — `judge.py` unwritten |
| **T5.8** | Grade the refusals → hallucination flag.                                         | 🟡 refusals confirmed by hand (3/3), metric not built |
| **T5.9** | Latency under agent load — p95.                                                  | ❌ blocked — numbers are rate-limit artifacts |
| **T5.C** | Close clean — commits + push, log, instruction delta.                            | ✅ |

---

## 📓 What happened

### T5.5 — wire RAGAS (three traps, all caught before shipping)
- Verified live: ragas **0.4.3** current. Their quickstart still wires Gemini through the **deprecated** `google.generativeai` SDK and calls `gemini-2.0-flash` "latest" — stale on both counts. We use `google-genai` and our own verified model pins.
- Placement call: eval deps isolated from the engine (see Supersedes). Vindicated immediately — the `langchain-community` clash would otherwise have hit production code.
- Two failed builds before green: the vertexai import error, then the collections naming error. Both fixed by **reading the module** instead of trusting the docs.

### T5.6 — the harness, and the quota wall
- `/ask` extended to return `contexts`: `ToolMessage` bodies split on the `[page N]` prefix (our own marker from `tools.py`), deduped — a multi-step question retrieves the same chunk more than once, and un-deduped it would double-count in context precision. The tool's output format was deliberately **not** changed mid-eval: that string is exactly what the model saw.
- **Run 1: 9 of 15, then six 500s.** Root cause in the traceback: `429 RESOURCE_EXHAUSTED`, `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, **limit 20/day**.
- Harness rewritten with **resume mode** (reuses answered questions from any prior run) + **30s pacing**. Latency reporting was **removed** — printing a number that is really a rate-limit artifact invites quoting it.
- The key-swap then failed silently three times: `.env` was correct, the shell was clean, `docker compose config` resolved the new key — but the container kept the old one. `--force-recreate` reported "Started" and did not replace the environment. **`stop` → `rm -f` → `up -d` fixed it.**
- **Run 2: 15/15, 0 failed.**

### The finding
- All **3 UNANSWERABLE** questions refused. (One buried the refusal after a prose lead-in rather than opening with it — a substring check catches it, `startswith` would not. Note this before building the metric on it.)
- Both **figure anchors** (`208`, `100`) HIT, cited to page 24 — the Turn-3 vision description is genuinely retrievable through the agent path. First real evidence for the figure-grounded criterion.
- Both **MISSes** turned out to be wrong answers, not scoring artifacts — see Supersedes. Found by our own harness, not by a reviewer.

---

## ✅ Decisions Locked This Session

- **Eval is a separate concern with a separate image** — profile-gated, never starts on a normal `up -d`, talks to `/ask` over HTTP.
- **Collect and judge are split.** Collection writes JSON; judging reads it. Re-judge without re-running the system — which matters enormously when a run costs a day of quota.
- **Eval run artifacts are versioned** (`.gitignore` exception). They are evidence, not scratch.
- **Judge model `gemini-3.5-flash-lite`; agent stays `gemini-3.6-flash`.** Different models = different quota buckets.
- **Judge gets its own key via `JUDGE_API_KEY`** — and it must come from a **separate project** to be worth anything.
- **No latency claim from this session.**
- **Billing declined for now** (Manglam's call). Verified cost for reference: a full 15-question run plus RAGAS judging ≈ **$0.33 / ₹30**, pay-as-you-go, no subscription.

---

## 🧠 Hard-Won Lessons

- **A hit-rate ruler cannot see a wrong answer.** Twelve of twelve chunks arrived and two answers were still wrong. Measuring *retrieval* and measuring *correctness* are different jobs — which is the entire argument for the trust layer, now proven on our own build rather than asserted.
- **The comparative-statement trap has two sides.** S06 solved it for *scoring* (anchor on the FY2025 value). It was never solved for *generation* — nothing tells the agent which column is current.
- **A green container status is not proof the environment changed.** `--force-recreate` said "Started" while serving stale env vars. Verify the value inside the container, never the status line — especially before spending a metered resource.
- **Health-gate anything that costs quota.** Two questions died on `Connection refused` because the harness fired while the engine was still booting — each burning 30s of pacing for nothing.
- **Read the module, not the docs.** RAGAS's own deprecation warning named classes that don't exist. `dir()` settled in one call what the documentation got wrong.
- **Free-tier limits are per project, and the counter is the ground truth.** The 21 → 25 climb proved the key swap hadn't taken effect, when three other checks all looked fine.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **Two confident wrong diagnoses, stated as conclusions rather than hypotheses.** (1) The 500s were blamed on the S10 base64/figure debt because the failures landed on the figure questions — it was a daily quota wall. (2) The two MISSes were called a number-formatting mismatch — they were genuinely wrong answers. Both were plausible, neither was tested first, and the second would have written a false "formatting artifact" line into the log. This is the **S11 "measure before you theorise" lesson relapsing one session later**, so it is promoted to a standing rule below.
- **A wrong hypothesis cost real quota.** Diagnosis 1 sent us hunting a figure-payload bug while the actual cause was printed in the traceback we already had.

---

## 🧾 Carried technical debt

- **`judge.py` unwritten** — the three judged §02 metrics remain unmeasured. **The** Turn-5 job.
- **Wrong-year generation bug** — 2 of 12 answerable questions wrong. Diagnose from the contexts already on disk (free), then fix (likely the system prompt).
- **Refusal detection needs a substring check, not `startswith`** — one refusal arrived after a prose lead-in.
- **p95 latency unmeasured** — blocked on quota distortion.
- **`langchain-community==0.3.31` pin** — a workaround for a RAGAS 0.4.3 bug; revisit on their next release.
- **Free-tier ceiling (5 RPM / 20 RPD)** — makes the product itself hard to test at ~10 questions/day. Revisit billing if it keeps costing sessions.
- *(Carried unchanged: `generate.py` orphaned from `/ask`; `.env.example` trailing newline; Qdrant `:latest` pin → Turn 7; page number = PDF order not printed footer label.)*
- **RESOLVED this session:** contexts are now exposed from `/ask`; the S10 base64 leak did not appear in any of the 15 collected runs.

---

## ⏭️ Next Session — the judge (start fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → Docker → `up -d` → `ps` → `git status -sb`. Verify `JUDGE_API_KEY` is from a **separate project**. |
| 1    | **Diagnose the wrong-year bug FIRST** — it's free (contexts are on disk) and it changes what faithfulness will score. |
| 2    | **Write `judge.py`** — read newest `run_*.json`, `llm_factory("gemini-3.5-flash-lite", provider="google", client=genai.Client(api_key=JUDGE_API_KEY))`, `GoogleEmbeddings(client=..., model="gemini-embedding-001")`, three collections metrics, per-sample `await ascore`, pace between calls, write `judged_*.json`. |
| 3    | **Produce the §02 numbers** — faithfulness, answer relevance, honest context precision (fixes the 0.31 ruler artifact). |
| 4    | **Grade the 3 refusals** → the hallucination-flag metric. Substring match on the locked sentence. |
| 5    | **Decide `generate.py`'s fate.** |

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted.

**Also queued (Manglam's call, discussed this session):** move to **Claude Code** at the Turn 5 boundary — with the constitution committed as `CLAUDE.md`, blueprint + logs moved into `docs/`, and this chat kept for planning turns rather than file work.
