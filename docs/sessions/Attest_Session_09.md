# 🧭 Attest — Session 09: Turn 4 Opens — The Agent Routes, Multi-Step Questions Answered With No Hardcoding (Slow-Build Tax Killed via uv Cache Mount)

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
| **Current phase**     | 🧭 **Turn 4 IN PROGRESS — the agent routes, proven end-to-end. NOT yet wired into `/ask`.** 3 of 7 spiral turns fully complete; Turn 4's core capability proven. |
| **Last session**      | [09] — landed the LangChain agentic layer: exposed `retrieve` as a tool, stood up `create_agent` (Gemini-wrapped), and proved a multi-step question routes + answers correctly with no hardcoded branching. Also killed the slow-build tax with a uv cache mount. |
| **What exists**       | Everything from S08 **plus the agentic layer (proven, not yet in the product)**: `engine/app/tools.py` (wraps `retrieve` as `@tool retrieve_document_chunks`, returns page-tagged text) + `engine/app/agent.py` (`ChatGoogleGenerativeAI` + `create_agent`, Attest-DNA system prompt, `run_agent()`). A live agent probe answered *"compare net sales vs R&D, which is larger"* by **calling the retrieve tool multiple times on its own** and returning the correct numbers ($416,161M vs $34,550M, cited page 33). **`/ask` still runs the OLD fixed retrieve→generate path — the agent is NOT wired into the endpoint yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 1 TB SSD. **GPU still unused** — agent + retrieval run CPU; Gemini is cloud-side. |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). This session: 1 commit for the uv cache mount (earlier) + 2 atomic Conventional Commits at close (tools / agent). |
| **The build**         | **Turn 4 close-out** — wire the agent into `POST /ask` (replace the fixed retrieve→generate path), then prove routing over HTTP. Pure plumbing, no unknowns (same shape as T1.7). Then Turn 5 (trust + eval). |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · figure-grounded ≥ 80% (aspirational) · p95 ≤ 8s. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **New this session:** `langchain==1.3.14` · `langchain-google-genai==4.2.5`; bumped `langchain-text-splitters==0.3.2 → 1.1.2` (core-version clash forced it). Agent model = `ChatGoogleGenerativeAI(gemini-3.6-flash)`. `uv` installer, now with a **cache mount** (no more `--no-cache`). |
| **Domain / corpus**   | Financial. Live set = US EDGAR (primary). Doc = Apple 10-K FY2025 (`aapl_10k.pdf`, 285 records: 284 text + 1 figure, dense+sparse, `{text, page, kind}` payload). Labeled set = FinQA / TAT-QA / ConvFinQA (not pulled yet). |
| **Next action**       | **Turn 4 close-out, fresh chat.** Resume ritual → wire `run_agent` into `POST /ask` → prove the agent routes over HTTP → decide the response shape (agent answer + which tools it called, for the "no hardcoding is provable" trace). |
| **Open question**     | **None parked at project level.** The base64-in-trace question (below) and the response shape for `/ask` get decided at the wiring step. |

---

## ⚠️ Supersedes

- **Path A CONFIRMED + API PATH CORRECTED — was "`create_react_agent` (prebuilt)" from S08's plan.** The prebuilt factory `create_react_agent` from `langgraph.prebuilt` is **now deprecated** (caught live before pinning — the standing rule earning its place). Current non-deprecated path: **`from langchain.agents import create_agent`** (LangChain v1). Still built on LangGraph's StateGraph underneath, so the architecture story is unchanged; only the factory name/home moved. Signature confirmed live from the official v1 docs: `create_agent(model, tools=[...], system_prompt=...)`.

- **Agent model is a SEPARATE object from `generate.py`'s Gemini — deliberate, not a duplicate.** `create_agent` needs a **LangChain-wrapped** chat model (`ChatGoogleGenerativeAI`), whereas `generate.py` calls the raw `google-genai` client directly. Two objects, same underlying Gemini (`gemini-3.6-flash`), same key. The adapter reads **`GOOGLE_API_KEY` first, then `GEMINI_API_KEY` as fallback** — so the env var already injected into the engine (S05) is found automatically, no new secret plumbing.

- **`langchain-text-splitters` BUMPED `0.3.2 → 1.1.2` — forced, not cosmetic.** `langchain 1.3.14` requires `langchain-core >= 1.4.9`; the old splitter pinned `core < 0.4` → unsatisfiable resolve (uv failed the build loudly, the healthy outcome). Bumping the splitter to its `1.x` line dissolved the clash. `RecursiveCharacterTextSplitter` import + call unchanged across the bump. Also folded the duplicate `qdrant-client` requirement lines (bare + `[fastembed]`) into one — the extra is a superset.

- **`uv` install now uses a CACHE MOUNT — was `--no-cache`.** The Dockerfile `RUN` changed from `uv pip install --system --no-cache -r requirements.txt` to `RUN --mount=type=cache,target=/root/.cache/uv uv pip install --system -r requirements.txt`, plus `ENV UV_HTTP_TIMEOUT=120`. Reason: `--no-cache` re-downloaded ~1GB of torch/CUDA/onnxruntime wheels on **every** rebuild — the tax that drained the laptop mid-build twice this session. The cache mount persists wheels across builds → first build pays the download, every rebuild after is seconds.

---

## 🎯 Session goal

**Open Turn 4 — the agentic layer: an agent that routes a multi-step question across the existing retrieval tools with NO hardcoded branching.** Scoped to: land the deps (fighting the slow-build tax), expose `retrieve` as a tool, stand up the agent, and prove routing end-to-end. Wiring into `/ask` deliberately pushed to a fresh context.

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T4.0** | Resume gate — E: mounted, containers Up, tree clean, last commit safe.           | ✅ (spanned a battery-drain + multi-day gap; re-gated each resume) |
| **T4.1** | Introduce LangGraph/LangChain — verify non-deprecated API live, land the deps.    | ✅ `create_agent` path, deps installed |
| **T4.1a** | Kill the slow-build tax — uv cache mount so wheels download once.                 | ✅ cache mount + timeout |
| **T4.2** | Expose `retrieve` as an agent-callable tool, proven in isolation.                 | ✅ `retrieve_document_chunks` |
| **T4.3** | Stand up `create_agent` (Gemini-wrapped) with the Attest-DNA system prompt.       | ✅ `agent.py` |
| **T4.4** | Prove a multi-step question routes + answers correctly, no hardcoding.            | ✅ multi-call, correct numbers |
| **T4.C** | Close clean — atomic commits + push, log, instruction delta.                       | ✅ |
| **T4.5** | Wire the agent into `POST /ask`.                                                   | ⬜ **next session** (deliberately deferred) |

---

## 📓 What happened

### T4.0 — the gate (across a rough stretch)
- This session spanned a **battery-drain mid-build** and a **multi-day gap**. Re-gated on every resume: containers Up, `main...origin/main` clean.
- **The shell container shows `Exited (0)`** — its command is a bare `python3` that drops to an interactive prompt with nothing holding it open, so it exits cleanly. **Not a crash** — it's the known-empty placeholder until the Django app lands at Turn 6. The three that matter (engine, postgres, qdrant) are Up. Gate = green with a known-empty shell.
- Post-install sanity check before building anything: `docker compose exec engine python -c "from langchain.agents import create_agent; from langchain_google_genai import ChatGoogleGenerativeAI; print('imports OK')"` → `imports OK`. Confirmed the deps truly resolve inside the running image, not just listed in requirements.

### T4.1 — land the deps (verify-before-pin earned its place, twice)
- **Deprecation caught live (standing rule working):** S08 planned `create_react_agent` from `langgraph.prebuilt` — a live check showed it's **deprecated** in favour of `create_agent` from `langchain`. Pinned the current path instead. This is exactly the "no deprecated patterns" rule catching a trap before it shipped.
- **Verified every version live before pinning:** `langchain 1.3.14`, `langchain-google-genai 4.2.5`, `langchain-text-splitters 1.1.2`. Also confirmed the `@tool` decorator's current home (`from langchain.tools import tool`) and the `create_agent(model, tools, system_prompt)` signature from the official v1 docs.
- **The version clash (a clean, honest failure):** `langchain 1.3.14` needs `core >= 1.4.9`; old `text-splitters 0.3.2` pinned `core < 0.4`. uv **failed the build with a readable "unsatisfiable" message** instead of half-installing. Bumped the splitter → resolved.

### T4.1a — kill the slow-build tax (the session's real infra win)
- **The problem:** `--no-cache` on the `uv pip install` re-downloaded ~1GB of torch/CUDA/onnxruntime wheels on **every** rebuild. Over a home connection this ran 20+ minutes and **drained the laptop mid-build twice**. Also hit a `sympy` wheel **network timeout at the 30s default** → added `ENV UV_HTTP_TIMEOUT=120`.
- **The fix:** replaced `--no-cache` with a **persistent cache mount** — `RUN --mount=type=cache,target=/root/.cache/uv uv pip install --system -r requirements.txt`. Wheels now download once and persist across rebuilds. First build still pays the download (the last slow one); every rebuild after is seconds. Same root cause as the S06 onnxruntime timeout, now solved permanently for wheels.

### T4.2 — expose retrieve as a tool
- `engine/app/tools.py`: `@tool def retrieve_document_chunks(question) -> str` wraps the existing, already-proven `retrieve()`. **Two design calls:** (1) returns a **formatted string** (not `list[dict]`) because an agent's tools speak text to the LLM — flattened to `"[page N] <text>"` so the Turn-2 page provenance survives as words; (2) the **docstring is the tool's instruction manual** — the agent reads it to decide *when* to call the tool, so it says what it does AND when to reach for it. The one place a docstring genuinely earns its keep.
- **Proven in isolation:** a `@tool` function is wrapped in a `StructuredTool`, so it's called via `.invoke({'question': ...})`, not directly. Ran it → returned real Apple R&D text with `[page N]` tags. Tool works.

### T4.3 — stand up the agent
- `engine/app/agent.py`: `ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=...)` + `create_agent(model, tools=[retrieve_document_chunks], system_prompt=SYSTEM_PROMPT)`.
- **The system prompt carries Attest's DNA:** answer ONLY from the document, call the retrieve tool before answering, **retrieve per-part for multi-step questions** (this is what forces real routing), cite pages, and the **exact same refusal sentence** as `generate.py` — *"I cannot answer this from the provided sources."* — keeping Turn 5's machine-checkable self-grading seam intact through the agent path.
- `run_agent()` returns the **raw result** for now (the full message list) — deliberately un-prettified so the agent's routing decisions are visible as evidence.

### T4.4 — prove it routes (the payoff)
- Ran a genuinely multi-step question: *"Compare Apple total net sales with its research and development spend, and say which is larger."*
- **The agent routed with zero hardcoding:** it decided on its own to call `retrieve_document_chunks`, **rewrote its own search query** (`"Apple total net sales research and development expense R&D"`), and **called the retrieve tool multiple times** to gather both figures — the exact "multi-step, no hardcoded branching" the blueprint defines Turn 4 as.
- **The answer was correct + complete:** total net sales **$416,161M** vs R&D **$34,550M** for FY2025 (matches the corrected Turn-2 gold keys), pulled all three years, computed the ~12× ratio, cited page 33. The refusal seam and page-citation DNA held through the agent path.

### T4.C — close clean
- Reconciled `git status -s` before committing (S06 lesson): only the two new files untracked. **2 atomic Conventional Commits** (tools / agent), pushed, `main...origin/main` clean. (uv cache-mount Dockerfile edit was committed earlier in the session.)

---

## 🧾 Turn-4 technical debt (flagged this session — deliberately deferred, tracked here so nothing is forgotten)

1. **HF model cache not persisted.** The reranker (`bge-reranker-v2-m3`, 2.27GB) + embedder (`bge-small`, 130MB) **re-download on every image rebuild** — the HuggingFace cache lives in the container's ephemeral layer. Same root cause as the uv-wheel problem we *did* fix. Proper fix: a mounted HF cache volume so models download once, ever. **High-value, do early next session.**
2. **Models reload per-call inside `retrieve`.** `embed_question_dense/_sparse` and `rerank` each construct their model (`SentenceTransformer(...)`, `CrossEncoder(...)`) **on every call**. Fine for the old one-shot `/ask`, but an **agent calls retrieve in a loop** — so a multi-step question reloads a 130MB embedder + 2.27GB reranker several times. This is why the agent probe was slow. Fix: load models once (module-level or a cached singleton).
3. **Base64 image data leaks into the agent trace.** The multi-step probe dumped a long base64 blob at the end — the page-24 figure's raw bytes riding along in a retrieved record / message. Harmless to the answer, ugly in the trace. Investigate *where* it enters (figure payload vs Gemini echoing image content) at the wiring step.
4. **`retrieve` still reloads models even after the agent lands** — same as #2, noted separately because it also affects the eventual `/ask` latency vs the §02 p95 ≤ 8s target. The per-call reload will matter for the latency gate at Turn 5.

*(Carried, unchanged, from earlier turns: Qdrant `:latest` pin → Turn 7; `.env.example` trailing newline; page number = PDF order not printed footer label; string-anchored ruler undercounts, real gate is RAGAS/FinQA at Turn 5.)*

---

## ✅ Decisions Locked This Session

- **Agent factory = `create_agent` from `langchain.agents`** (LangChain v1) — the current non-deprecated path over the deprecated `langgraph.prebuilt.create_react_agent`.
- **Agent model = `ChatGoogleGenerativeAI(gemini-3.6-flash)`** — a LangChain-wrapped Gemini, separate object from `generate.py`'s raw client, same underlying model + key.
- **First tool = `retrieve_document_chunks`** — wraps the proven `retrieve()`, returns page-tagged formatted string, docstring written for the agent to read.
- **System prompt carries the DNA** — sources-only + per-part retrieval + page citations + the exact Turn-5 refusal sentence.
- **`langchain-text-splitters` bumped to `1.1.2`** (forced by the core-version clash); duplicate `qdrant-client` lines folded to one.
- **uv cache mount replaces `--no-cache`** + `UV_HTTP_TIMEOUT=120` — the slow-build tax is dead.
- **Turn 4 core capability declared PROVEN** (routes a multi-step question, no hardcoding). **NOT declared complete** — the agent isn't in `/ask` yet.

---

## 🧠 Hard-Won Lessons

- **Verify-before-pin caught a live deprecation on the headline feature.** S08's planned `create_react_agent` was deprecated by the time we built it; the live check swapped us to `create_agent` before a line shipped. The standing rule isn't ceremony — it changed what we built.
- **A loud dependency failure is a gift.** uv's "unsatisfiable: langchain needs core≥1.4.9, splitter needs core<0.4" told us *exactly* what to fix. A resolver that half-installed and failed at runtime (the S03 empty-`requirements.txt` ghost) would've cost far more. Read the resolver's message — it names the fix.
- **`--no-cache` is a false economy for heavy deps.** It guarantees a clean install but re-downloads gigabytes every build. A **cache mount** keeps the reproducibility (fresh resolve) while killing the re-download. The right pattern for any image with torch-class wheels.
- **An agent's tools speak text, not Python objects.** `retrieve` returns `list[dict]`, but the tool flattens it to a page-tagged string — because the LLM reads tool output as words to reason over. Designing the tool's *return shape for a reader*, not a caller, is the mental shift from function to tool.
- **The docstring is the routing brain's fuel.** With a prebuilt agent, you don't write `if/else` — the agent picks tools by reading their docstrings. So the docstring stops being documentation and becomes *behaviour*. Vague docstring = confused agent.
- **"Proven" and "wired" are different milestones — don't conflate them.** The agent routes correctly from a probe, but `/ask` still runs the old path. Declaring Turn 4 "done" here would be the tidy-fiction trap. It's *proven*; it's not *in the product*. Honest status beats a clean checkmark.
- **The agent path preserves the self-grading seam by design.** The same refusal sentence lives in both `generate.py` and the agent's system prompt — so Turn 5's programmatic honesty-detection works no matter which path answers. A seam planned three turns ago still fits.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **Answered a scratch-file question without flagging it wasn't Attest code.** Manglam pasted a toy vector-memory experiment (Gemini embeddings + cosine recall) to sanity-check the *template*; I debugged it straight without first noting "this isn't our engine code." Minor, but the kind of context-slip worth watching — confirm *which* codebase a paste belongs to before diving in.
- **Flagged a lot of future fixes mid-build.** Not wrong (they're real debt), but Manglam rightly noted they must be *written down* or they evaporate. Resolved by tracking them in this log's dedicated debt section — the correct home, keeping Supersedes for facts and Instructions for rules.

---

## ⏭️ Next Session — Turn 4 close-out, then Turn 5 (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (engine/postgres/qdrant Up; shell Exited-0 is fine) → `git status -sb`. |
| 1    | **Persist the HF model cache FIRST** (debt #1) — mount a volume so the reranker/embedder stop re-downloading on rebuild. High-value, cheap, do it before anything slow. |
| 2    | **Fix per-call model reloads** (debt #2) — load embedder/reranker once, not per retrieve call. Matters for agent-loop speed AND the §02 p95 latency gate. |
| 3    | **Wire `run_agent` into `POST /ask`** — replace the fixed retrieve→generate path. Decide the response shape: agent answer + **which tools it called** (so "no hardcoding" is provable in the product, not just a probe). Investigate the base64-in-trace leak (debt #3) here. |
| 4    | **Prove routing over HTTP** — a `curl` multi-step question returns a correct, cited answer through the agent. Turn 4 truly complete. |
| 5    | **Then Turn 5 — trust + eval:** pull FinQA/TAT-QA/ConvFinQA, wire RAGAS, enforce the §02 numbers, and prove the red-flag path on an ungrounded question. |

**Decided at the step, not now:** the `/ask` response shape, how the tool-call trace is surfaced, and whether GPU passthrough is ever justified (still unused; Gemini is cloud-side).

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
