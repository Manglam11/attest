# 🧭 Attest — Session 10: Turn 4 Closes — Agent Wired Into `/ask`, Red-Flag Path Proven, a 62s Latency Bug Surfaced

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
| **Current phase**     | 🎉 **Turn 4 COMPLETE — the agent is in the product. `/ask` routes through it over HTTP.** 4 of 7 spiral turns fully alive. **Turn 5 (trust + eval) IN PROGRESS** — 2 of its buckets done. |
| **Last session**      | [10] — paid down 3 debts (HF cache, per-call reloads, base64 leak), wired `run_agent` into `POST /ask`, proved routing over HTTP. Then did two Turn-5 buckets: red-flag path (proven) + latency gate (measured — **failed hard, 62s vs 8s**). |
| **What exists**       | Everything from S09 **plus**: **(1)** HF model cache on a named volume (`hf_cache` → `/root/.cache/huggingface`, `HF_HOME` set) — reranker+embedder download once, ever; **(2)** module-level **singletons** in `retrieve.py` (`_dense_model`, `_sparse_model`, `_rerank_model`, `_client`) — built once at import, not per call; **(3)** the **agent wired into `POST /ask`** — `run_agent()` parses the raw message list into `{answer, tool_calls}`, `main.py` returns `{question, answer, tool_calls}`; **(4)** the **red-flag path proven end-to-end over HTTP** — an ungrounded prediction question returns the verbatim refusal sentence. **No auth, no multimodal beyond the one figure, no eval-on-benchmark yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 1 TB SSD. **GPU still unused** — agent + retrieval run CPU; Gemini is cloud-side. |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). This session: 4 atomic Conventional Commits (HF-cache / singletons / agent-parser / `/ask`-wiring). |
| **The build**         | **Turn 5 — trust + eval.** Two buckets done (red-flag path, latency measured). Remaining heavy buckets need a fresh full context: pull FinQA/TAT-QA/ConvFinQA, wire RAGAS, build the eval harness, produce the real §02 numbers. **AND: diagnose+fix the 62s latency bug (open thread, below).** |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · figure-grounded ≥ 80% (aspirational) · **p95 ≤ 8s** ← **first measured this session and FAILED: single retrieve call = 62s.** |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **No new deps this session** — all changes were infra/perf/wiring on the existing stack. Agent = `ChatGoogleGenerativeAI(gemini-3.6-flash)` via `create_agent`. `uv` installer with cache mount + HF cache volume. |
| **Domain / corpus**   | Financial. Live set = US EDGAR (primary). Doc = Apple 10-K FY2025 (`aapl_10k.pdf`, 285 records: 284 text + 1 figure, dense+sparse, `{text, page, kind}` payload). Labeled set = FinQA / TAT-QA / ConvFinQA (**not pulled yet**). |
| **Next action**       | **Fresh chat, Turn 5 heavy.** Resume ritual → **FIRST: diagnose the 62s latency bug** (hypothesis logged below) → then pull benchmark data, wire RAGAS, build the eval harness toward the §02 numbers. |
| **Open question**     | **Why is a single `retrieve` call 62s over HTTP when the `__main__` harness was fast?** Hypothesis logged in the open-thread section — test it first next session. |

---

## ⚠️ Supersedes

- **`/ask` now routes through the AGENT — was the fixed `retrieve → generate` path.** `main.py` no longer imports `retrieve`/`generate_answer`; it imports `run_agent` from `app.agent` and returns `{question, answer, tool_calls}`. The old path's `generate.py` and `retrieve.py` **still exist and are still used** — the agent calls `retrieve` *through* the `retrieve_document_chunks` tool, and `generate.py` is now effectively orphaned from `/ask` (candidate for deletion or keep-as-fallback — decide next session). Turn 4 is now **complete**, not just "proven" (S09's honest distinction closed).

- **Response shape CHANGED — was `{question, answer, sources}`; now `{question, answer, tool_calls}`.** Reason: with the agent in charge, grounding proof is the **tool-call trace** (which tool the agent chose + the query *it wrote itself*), which is the blueprint's "no hardcoding is provable in the product" evidence. `sources` (raw retrieved chunks) was dropped from the shape — it belongs to the Turn-6 source-card UI, added back when the UI needs it. Pages are still cited *inside* the answer text (system-prompt enforced).

- **`run_agent()` now returns a PARSED dict — was the raw message list.** New `run_agent()` walks the agent's message list, collects every `AIMessage.tool_calls` into `[{tool, query}]`, and takes the final message's content as the answer. A `_flatten_content()` helper normalizes Gemini's content — which comes back as a **list of `{type, text}` blocks**, not a bare string, even for pure text — into a plain string. **The base64 leak (S09 debt #3) is closed BY DESIGN:** the parser never reads `ToolMessage` content (where the figure's raw bytes ride), so the blob can't reach the response.

- **HF model cache PERSISTED — was ephemeral (re-downloaded ~2.4GB every rebuild).** `docker-compose.yml` gained a named volume `hf_cache` mounted at `/root/.cache/huggingface` (HF's default cache path, engine runs as root) plus `HF_HOME` env var pointing at it. Distinct from the S09 `uv` cache mount: uv cache = **build-time pip wheels**; HF volume = **runtime model weights**. Two different caches, don't conflate. Proven: weights survived an overnight gap and loaded from cache (`models loaded from cache`, no download bars). This was S09 debt #1.

- **Models load ONCE at import — were reconstructed on every `retrieve` call.** `retrieve.py`'s `embed_question_dense`, `embed_question_sparse`, `rerank`, and the `QdrantClient` are now module-level singletons (`_dense_model` etc.), built at import, reused across calls. Tradeoff: first import pays the ~2.4GB-into-RAM cost once; every call after is fast. This was S09 debt #2 — **but see the open thread: the fix proved fast in the `__main__` harness yet the HTTP path is still 62s per call, so the singleton is somehow not effective at runtime under uvicorn. UNRESOLVED.**

---

## 🎯 Session goal

**Close out Turn 4 (wire the agent into the product), then open Turn 5 with the buckets that don't need the benchmark data.** Debts first (they make the base fast + the latency story honest), then wiring on a clean base, then the two self-contained Turn-5 buckets.

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T4.6** | Resume gate — E: mounted, containers Up, tree clean, last commit safe.           | ✅     |
| **T4.7** | Persist HF model cache (debt #1) — named volume so models download once.          | ✅ (proven across overnight gap) |
| **T4.8** | Fix per-call model reloads (debt #2) — singletons, not per-call construction.     | ✅ (fast in harness — see open thread) |
| **T4.9** | Wire `run_agent` into `POST /ask` — parse to `{answer, tool_calls}`, kill base64.  | ✅     |
| **T4.10** | Prove routing over HTTP — multi-step `curl` returns correct, cited answer.        | ✅ Turn 4 COMPLETE |
| **T5.4** | Red-flag path — ungrounded question triggers the verbatim refusal sentence.       | ✅ (3 grounding attempts, then refused) |
| **T5.5** | Latency gate — time `/ask` against §02 p95 ≤ 8s (debt #4).                         | ✅ measured — **FAILED, 62s single call** |
| **T4.C** | Close clean — atomic commits + push, session log, instruction delta.              | ✅     |

*(T5.1–T5.3 — pull benchmarks, wire RAGAS, build harness — deliberately deferred to a fresh full context: they're the "one hard thing" that needs its own window.)*

---

## 📓 What happened

### T4.6 — the gate
- Standard resume ritual: engine/postgres/qdrant `Up`, `main...origin/main` clean. (This session spanned **three days** — re-gated each resume. Green each time.)

### T4.7 — persist the HF model cache (debt #1)
- **The problem, named:** `sentence-transformers` downloads `bge-small` (130MB) + `bge-reranker-v2-m3` (2.27GB) on first *runtime* call into the container's writable layer, which dies on every rebuild → ~2.4GB re-download each time. The S09 uv cache mount doesn't cover this — that's pip wheels (build-time); this is model weights (runtime).
- **The fix:** named volume `hf_cache` → `/root/.cache/huggingface` (HF's default path), plus `HF_HOME` env var making the intent explicit/future-proof. Applied with `--force-recreate engine` (S08 lesson: Docker applies volume changes only on container creation).
- **Proven:** the download completed on the first run, then **survived an overnight gap** — next-day `SentenceTransformer(...)`/`CrossEncoder(...)` printed `models loaded from cache` with no download bars. Reuse confirmed.

### T4.8 — fix per-call model reloads (debt #2)
- **The problem:** `embed_question_dense/_sparse` and `rerank` each did `SentenceTransformer(...)`/`CrossEncoder(...)` *inside the function body* → rebuilt the object every call. Even with weights cached on disk, *constructing* the object reloads 2.4GB disk→RAM each time. The old one-shot `/ask` hid it; an **agent calls retrieve in a loop**, so it stacked.
- **The fix:** four module-level singletons (`_dense_model`, `_sparse_model`, `_rerank_model`, `_client`), built once at import; functions just use them. `QdrantClient` folded in too (same wasteful per-call pattern).
- **Proven in the harness:** `docker compose exec engine python -m app.retrieve` returned 5 chunks with the R&D one flagged `<-- 31,370 HERE`, fast after a one-time import cost. **⚠️ This is the fix that later did NOT hold over HTTP — see open thread.**

### T4.9 — wire the agent into `/ask`
- **Read `agent.py` + `main.py` + `tools.py` first** (S05 rule) before writing — confirmed the tool param is literally named `question` (so the trace parser's `.get("question")` is correct), and mapped the agent's return: `invoke()` → dict with `messages` list (`Human` → `AI`-with-`tool_calls` → `Tool` → … → final `AI`).
- **Response shape decided = `{question, answer, tool_calls}`** (reasoning in Supersedes). `tool_calls` = `[{tool, query}]` — the agent's self-written query is the routing evidence.
- **Base64 leak (debt #3) closed by design** — the parser never reads `ToolMessage` content (where the figure bytes ride), so the blob can't reach the response. No special-casing needed; the shape choice fixed it.
- **Two shape bugs caught + fixed live during testing:**
  1. **`answer` came back as a list** `[{"type":"text","text":...}]` — Gemini returns content as a block list, not a bare string. Fixed with `_flatten_content()` (handles both string and block-list shapes).
  2. **Empty `curl` response** twice — `Expecting value: line 1 column 1 (char 0)` from `json.tool`. **Not a code bug** — the `&&`-chained `curl` fired before the engine finished startup (singletons now load ~2.4GB into RAM at import → several-second startup). Fix: let the engine warm, run `curl` on its own (or check `/health` first).

### T4.10 — prove routing over HTTP (Turn 4's payoff)
- Multi-step `curl`: *"Compare Apple total net sales with its R&D spend, say which is larger."*
- **Clean pass:** `answer` = correct numbers ($416,161M vs $34,550M), pages cited, no base64. `tool_calls` showed `retrieve_document_chunks` with a **self-rewritten query** (`"Apple total net sales Research and development spend expense"` — not the literal question). No-hardcoding is now provable *in the product*, not just a probe. **Turn 4 COMPLETE.**

### T5.4 — the red-flag path (the differentiator, proven)
- Blueprint's exact red-row example: *"Will Apple next year revenue beat 500 billion dollars?"* (a prediction no 10-K contains).
- **Textbook-plus pass:** the agent **led with the verbatim refusal** — *"I cannot answer this from the provided sources."* — then **tried three times** to ground it (rewrote the query three ways), found nothing, and gave the real historical FY23/24/25 net-sales numbers it *could* ground, drawing a clean line between what the doc says and doesn't. Refused the prediction, stayed useful, never invented a number.
- **Why it matters for Turn 5:** the verbatim sentence is a **programmatic seam** — RAGAS/monitoring can do a literal string check to auto-flag ungrounded answers with zero LLM-judging. Designed S05, carried through the agent S09, proven through the HTTP agent path here.

### T5.5 — the latency gate (measured, failed hard)
- `curl -w "%{time_total}"` on the multi-step question: **75.09s · 74.86s · 228.81s.** Against §02 **p95 ≤ 8s** — a ~10–28× failure.
- **Diagnosed one layer down before theorising** (S06 discipline): timed a **single** `retrieve` call directly (no agent, no Gemini) → **62.05s**. So the retrieval stack *itself* is the bottleneck, and the agent calling it 3× explains the 75s+. The Gemini round-trips are NOT the main cost.
- **This is the fix-worthy finding of the session** — but diagnosing+fixing is reasoning-heavy, so deferred to a fresh window (correct call: don't start a heavy thread in a tail-end context). Hypothesis logged below.

### T4.C — close clean
- Reconciled `git status -s` (S06 lesson): exactly 4 modified files, nothing dangling. **4 atomic Conventional Commits** — HF-cache (perf) / singletons (perf) / agent-parser (feat) / `/ask`-wiring (feat) — pushed, `main...origin/main` clean. Two-places rule satisfied.

---

## 🧵 OPEN THREAD — the 62s latency bug (start here next session)

**Symptom:** a single `retrieve()` call takes **62s over the running engine**, but the same code via `docker compose exec engine python -m app.retrieve` was fast. The T4.8 singleton fix proved effective in the `__main__` harness yet is somehow **not effective at runtime under uvicorn**.

**Leading hypothesis:** uvicorn runs with `--reload` (WatchFiles). The reloader and the live-mounted `app/` may cause the module to be re-imported per request, or the singletons to live in a different process than the one serving requests — so the models reconstruct despite the module-level pattern. **Test first:** confirm whether the singletons are built once per process or per request (add a print at import + a print in the function; count them across two requests). If `--reload` is the culprit, the models should be loaded in a way that survives the reloader (e.g. app startup/lifespan event, or don't reload the heavy module).

**Secondary suspects to rule out if the above is clean:** cross-encoder rerank of 20 pairs on CPU is genuinely slow (but not 62s-slow); Qdrant query latency; some model *still* reconstructing inside `rerank`/`embed_*` that the singleton refactor missed.

**Why it matters:** §02 p95 ≤ 8s is a frozen contract number and the Turn-5 latency gate. This must be green before Turn 5 can honestly claim the §02 table.

---

## 🧾 Carried technical debt (updated)

- **`generate.py` orphaned from `/ask`** — the agent path replaced it; decide delete vs keep-as-fallback next session.
- **62s latency** — the open thread above (was S09 debt #4, now measured and confirmed real).
- **`.env.example` trailing newline** — cosmetic, still open.
- *(Carried unchanged: Qdrant `:latest` pin → Turn 7; page number = PDF order not printed footer label; string-anchored interim ruler undercounts, real gate is RAGAS/FinQA at Turn 5.)*
- **RESOLVED this session:** HF cache persistence (#1), per-call reloads (#2 — *code* resolved, *runtime* effect unconfirmed, see open thread), base64 trace leak (#3).

---

## ✅ Decisions Locked This Session

- **`/ask` routes through the agent** — Turn 4 is complete (in the product, not just proven).
- **Response shape = `{question, answer, tool_calls}`** — tool-call trace is the no-hardcoding proof; `sources` deferred to Turn-6 UI.
- **`run_agent()` returns parsed `{answer, tool_calls}`**; `_flatten_content()` normalizes Gemini's block-list content to a string.
- **Base64 leak closed by design** — parser never reads `ToolMessage` content.
- **HF model cache on a named volume** (`hf_cache`, `HF_HOME` set) — models download once, ever.
- **Retrieve models are module-level singletons** — built once at import.
- **Red-flag path proven** — verbatim refusal sentence fires through the agent HTTP path; it's the programmatic self-grading seam.
- **Latency measured, failed (62s)** — deferred to a fresh window with a logged hypothesis. Not swept under the rug.

---

## 🧠 Hard-Won Lessons

- **"Proven in the harness" ≠ "works in the product."** The singleton fix was fast under `python -m app.retrieve` and 62s under uvicorn. The runtime environment (reloader, process model, live-mount) can defeat a fix that the isolated test blesses. **Time the real path, not just the harness** — the exact Attest measure-first DNA, this time turned on our own perf fix.
- **Diagnose one layer down before theorising the fix.** 75s at `/ask` could have been blamed on Gemini or the agent loop. One direct `retrieve` call (62s) proved the retrieval stack is the bottleneck and the agent just multiplies it. Same move as the S06 rank-7 probe — locate, don't guess.
- **Gemini's message content is a block list, not a string.** Even a pure-text answer comes back as `[{"type":"text","text":...}]`. Any code reading `message.content` must flatten it. A silent shape mismatch that only shows when you actually inspect the output.
- **Two caches, two lifecycles — don't conflate them.** uv cache mount = build-time pip wheels; HF volume = runtime model weights. Fixing one doesn't fix the other; they live at different stages.
- **A fixed refusal sentence is infrastructure, not politeness.** Because it's verbatim, Turn 5 can string-match it to auto-flag ungrounded answers — no LLM judge needed. The seam planned at S05 survived two architecture changes (agent at S09, HTTP path here) and still fits.
- **An empty `curl` after `--force-recreate` is usually a warm-up race, not a bug.** With heavy models loading at import, the server isn't listening for several seconds. Check `/health` or don't `&&`-chain the request onto the recreate.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **`&&`-chained the test `curl` onto `--force-recreate`, causing two false-alarm empty responses.** The engine wasn't up yet (models loading at import). Cost two confusing round-trips before I named the warm-up race. Root fix: **after a recreate that loads heavy models at import, don't chain the request — warm first, or gate on `/health`.**
- *(No standing-rule-level mistakes this session; the above is a one-off note, not a promoted rule.)*

---

## ⏭️ Next Session — Turn 5 heavy (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (engine/postgres/qdrant Up; shell Exited-0 fine) → `git status -sb`. |
| 1    | **FIRST: diagnose + fix the 62s latency bug** (open thread) — test the uvicorn-reload/singleton hypothesis; get a single `retrieve` call comfortably under budget before anything else. The §02 p95 ≤ 8s gate depends on it. |
| 2    | **Pull the benchmark data** — FinQA / TAT-QA / ConvFinQA; read their schemas, pick which becomes the real test set. |
| 3    | **Wire RAGAS** — verify current API live before pinning (standing rule); understand the four §02 metrics it computes. |
| 4    | **Build the eval harness** — run RAGAS over the agent `/ask` path on a labeled slice; produce the real §02 numbers vs the ≥0.90 / ≥0.85 targets. |
| 5    | **Decide `generate.py`'s fate** — delete (orphaned) or keep as a non-agent fallback. |

**Decided at the step, not now:** which benchmark(s) become the test set, how RAGAS is fed the agent path, and the exact latency fix — chosen inside the step when the ground is in front of us.

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
