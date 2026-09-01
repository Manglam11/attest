# 🧭 Attest — Session 13: The Gold Set Was Wrong — RAGAS Judge Lands

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
| **Current phase**     | **Turn 5 (trust + eval) IN PROGRESS.** The judge is **written and proven working**. The §02 numbers exist for **3 of 12** answerable questions — the full pass was still running at close. The S12 "wrong-year generation bug" **does not exist**; it was a gold-set defect. |
| **Last session**      | [13] — audited every gold key against the raw retrieved text, found **4 defective keys**, corrected them (15/15 hit), then wrote `judge.py` and got the first real RAGAS scores out of it. |
| **What exists**       | Everything from S12 **plus**: **(1)** `gold_set.py` with 4 corrected keys — the string scorer now reports **15/15**; **(2)** `engine/app/eval/judge.py` — three RAGAS collections metrics per sample, async `InstructorLLM`, **resume** from the newest `judged_*.json`, **fail-fast on 429**, refusals graded by substring; **(3)** `JUDGE_API_KEY` now reaches the eval container (it was going to `engine`, which never judges); **(4)** `jsonref` in the eval image. **Partial §02 numbers only. No p95. No auth.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM). GPU still unused. |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`. This session: **4 atomic Conventional Commits** (compose-key / jsonref / gold-keys / judge). |
| **The build**         | **Turn 5.** Judge built. Remaining: finish the judge pass over rows 3–11, write the completed numbers up, measure p95 once quota stops distorting it. |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). **Partial, n=3:** faithfulness **1.000** · answer relevance **0.985** · context precision **0.983** · refusal rate **3/3**. ⚠️ **Not claimable as the §02 result** until all 12 answerable rows are judged. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL + isolated eval image (ragas 0.4.3, `jsonref`). |
| **Domain / corpus**   | Financial. Apple 10-K FY2025, 285 records. Gold set = 15 pairs, **all keys now column-verified**. |
| **Next action**       | Re-run `python -m app.eval.judge` (resume skips what's scored) → complete the §02 table → commit `judged_*.json` and check the `.gitignore` exception actually covers it. |
| **Open question**     | Does the `.gitignore` eval exception cover `judged_*.json`, or only `run_*.json`? It did not appear as untracked at close. |

---

## ⚠️ Supersedes

- **THE HEADLINE — S12's central finding is RETRACTED. There is no wrong-year generation bug. The GOLD SET was wrong.** S12 recorded two "confidently wrong answers" (total assets, operating income) as a product defect. Reading the raw retrieved chunk settled it: the balance sheet prints `Sept 27 2025 | Sept 28 2024`, and total assets reads `359,241 | 364,980`. **The agent answered 359,241 — which is FY2025. Our key held 364,980, the FY2024 figure.** Same on the income statement (`133,050 | 123,216 | 114,301`; key held the FY2024 column). Two independent arithmetic checks confirm the agent: `147,957 + 211,284 = 359,241`, and `195,201 − 62,151 = 133,050`. **The agent was right on all 15 questions.** The comparative-statement trap bit our *ruler*, not our product — in the exact place S06 declared it solved.

- **A third key was wrong the same way, and a fourth was structurally too weak.** The audit did not stop at the two known rows. The stock-performance key (`208`) was the **September 2024** column; September 2025 is `234`. And the net-sales-vs-R&D question — which asks for a *difference* — was keyed to `416,161`, one of its **operands**, so an answer that botched the subtraction would still have scored a hit. Re-keyed to the computed result `381,611`. (The agent had in fact computed it correctly.) **4 defective keys of 15.**

- **`llm_factory` cannot produce an async Google LLM in ragas 0.4.3.** It hardcodes `instructor.from_genai(client)` with no `use_async`, yielding a sync `Instructor`, while every collections metric calls `agenerate` — a guaranteed `TypeError: Cannot use agenerate() with a synchronous client`. **Fix: bypass the factory** and construct `InstructorLLM(client=instructor.from_genai(client, use_async=True), model=..., provider="google")` directly. This supersedes the S12 next-step instruction to use `llm_factory`.

- **`jsonref` is a required, undeclared dependency** for instructor's Gemini structured-output path. Not pulled in by `ragas` or `instructor` — added to `requirements-eval.txt` explicitly.

- **The judge model's wall is PER-MINUTE, not per-day.** `gemini-3.5-flash-lite` free tier = **15 RPM**, and the daily cap was never approached. This is materially better than the agent's 20 RPD: a stalled judge run resets in ~60 seconds, not tomorrow.

- **The string scorer now grades refusals by substring, not `startswith`** — closing the S12 debt. One refusal arrives after a prose lead-in.

---

## 🎯 Session goal

**Write the judge and put real §02 numbers on the board.** Delivered, minus the final pass — and the session's real value turned out to be the audit that came first.

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T5.0** | Resume gate — containers Up, tree clean, `JUDGE_API_KEY` proven distinct.       | ✅ (found + fixed a missing key) |
| **T5.1** | Diagnose the wrong-year bug from contexts on disk — free.                        | ✅ **inverted the S12 finding** |
| **T5.7** | Write `judge.py` — three collections metrics, per-sample, paced.                 | ✅ proven end to end |
| **T5.7b**| Produce the §02 numbers.                                                        | 🟡 3 of 12 rows |
| **T5.8** | Grade the refusals → hallucination flag.                                         | ✅ 3/3, folded into the judge |
| **T5.2** | Fix the wrong-year bug.                                                          | ✅ **no fix needed** — the bug was the gold set |
| **T5.9** | p95 latency.                                                                     | ❌ carried — still quota-distorted |
| **T5.C** | Close clean — commits, log, instruction delta.                                   | ✅ |

---

## 📓 What happened

### T5.0 — the gate caught a real miss
`JUDGE_API_KEY` read as `MISSING` inside the eval container. Two suspects named before touching anything: absent from `.env`, or not passed through. One command checked both — the key was in `.env` and was being handed to **`engine`**, which never judges, while `eval` never received it. Our secrets pattern is per-key `environment:`; nothing inherits. Fixed in both directions.

### T5.1 — the audit (the session's real finding)
Both "wrong" answers pulled the **same chunk** that contained both the right and wrong number, and the model's own breakdown reconciled internally (`147,957 + 211,284 = 359,241`) — meaning it had read one coherent column, not mixed two. That reframed the question from *which column did it pick* to **which column did we key**. Printing the raw chunk answered it in one look: our key was the year-earlier column, three separate times.

The audit then swept all 15 keys with a ±4-line window around each, and caught the two remaining defects nobody was looking for. Re-scoring the run already on disk — **zero API calls** — went from 12/15 to **15/15**.

### T5.7 — the judge, and four walls in a row
1. **`llm_factory` returns a sync client** while every metric calls `agenerate`. Read `_check_client_async` in the module rather than guessing; the fix was to construct `InstructorLLM` directly with `use_async=True`.
2. **`jsonref` missing** — surfaced only from inside a live Gemini call.
3. **First real score came back `0.0`** on a claim the context supported. Rather than accept or dismiss it, ran three probes (exact match / original / obviously false) → `1.0 / 0.0 / 0.0`. The metric was sound; the probe context said `$112,010` while the response said `$112,010 million`, and the verifier refused to infer the unit. Correct strictness for a faithfulness judge. Real contexts carry the table header, so it doesn't bite the run.
4. **Rate limit at row 3.** See below.

### T5.7b — the numbers, partial and honest
Rows 0–2: faithfulness **1.00 / 1.00 / 1.00**, answer relevance **0.96 / 1.00 / 1.00**, context precision **1.00 / 1.00 / 0.95**. All 3 unanswerable rows **REFUSED**.

The 0.98 context precision is the number that matters most here: it retires S11's **0.31** as the string-scorer artifact it always was. Real precision is near-perfect; the ruler simply couldn't see it.

**None of this is the §02 claim** — n=3 of 12. Written up as partial, deliberately.

---

## ✅ Decisions Locked This Session

- **Refusal rows skip the LLM metrics.** Faithfulness against a refusal is meaningless and costs ~30 calls. They're graded by substring against the locked sentence instead.
- **Judge bypasses `llm_factory`** and constructs `InstructorLLM` directly until upstream supports `use_async` for Google.
- **Resume + fail-fast are mandatory** on anything metered — promoted to a standing rule.
- **Session closed with a run in flight.** Debugging on a nearly-full context window is how false lines get written into logs. The judge writes to disk and resumes; nothing is lost.

---

## 🧠 Hard-Won Lessons

- **When the model and the ruler disagree, suspect the ruler.** The build's headline "correctness bug" was a measurement bug. The agent was right 15 out of 15, and had been all along.
- **A grep proves a string exists; it never proves which column it's in.** Every defective key was exactly **one column late** — always the prior fiscal year. In a comparative financial statement, that is the single most likely way to be wrong while looking right.
- **A key must anchor the answer, not an input to it.** The difference question could have passed with broken arithmetic.
- **The eval harness caught the eval harness.** A hit-rate scorer reported 12/12 while carrying three wrong keys. Only reading the raw retrieved text found it — which is the entire argument for the trust layer, now demonstrated against our own measuring instrument rather than the product.
- **Read the module, not the docs — again.** `llm_factory`'s own source explained the async failure in one line after the error message alone had explained nothing.
- **Verify a suspicious score before accepting OR dismissing it.** The `0.0` looked like a bug and was correct behaviour. Three cheap probes settled it.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **Shipped the judge without resume or fail-fast** — the exact two protections `harness.py` already had, on a run that spends a metered resource. Nine rows burned into consecutive 429s that taught nothing the first one didn't.
- **Sized pacing against the wrong unit.** Paced the three *metrics* at 4s while each metric fires ~10 calls internally — ~30 calls/minute into a 15 RPM ceiling. The budget is in **API calls**, not questions. Manglam flagged it; both are promoted to standing rules.
- **Estimated the run at 10 minutes when the arithmetic gives ~15.** Sloppy, and it made a healthy run look hung.
- **Did do this right:** every diagnosis this session was labelled a suspect and tested with one command before being stated — the S12 rule, held.

---

## 🧾 Carried technical debt

- **Judge pass incomplete** — rows 3–11 unjudged. Re-run; resume handles the rest.
- **`judged_*.json` may not be git-tracked** — did not appear as untracked. Verify the `.gitignore` eval exception covers it.
- **p95 latency unmeasured** — still blocked on quota distortion.
- **`langchain-community==0.3.31` pin** — RAGAS 0.4.3 workaround; revisit on their next release.
- **`llm_factory` bypass** — remove when upstream supports `use_async` for Google.
- **Free-tier ceilings** — agent 20 RPD, judge 15 RPM. The agent's daily cap is the binding one.
- *(Carried unchanged: `generate.py` orphaned from `/ask`; `.env.example` trailing newline; Qdrant `:latest` pin → Turn 7; page number = PDF order not printed footer label.)*
- **RESOLVED this session:** the "wrong-year generation bug" (never existed); refusal substring detection; the 0.31 precision artifact; `JUDGE_API_KEY` plumbing.

---

## ⏭️ Next Session — finish the numbers

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → Docker → `up -d` → `ps` → `git status -sb`.                                     |
| 1    | **Re-run the judge** — `docker compose --profile eval run --rm -T eval python -m app.eval.judge`. Resume skips what's scored. |
| 2    | **Complete the §02 table** — all 12 answerable rows, then commit `judged_*.json` (check the ignore exception first). |
| 3    | **Look at any row that scores below target** — a low faithfulness now means something real, since the keys are trustworthy. |
| 4    | **Decide `generate.py`'s fate** (carried from S12).                                                          |
| 5    | **p95** — only once a run completes without rate-limit distortion.                                           |

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted.

**Also queued:** move to **Claude Code** at the Turn 5 boundary — constitution as `CLAUDE.md`, blueprint + logs into `docs/`, this chat kept for planning turns.
