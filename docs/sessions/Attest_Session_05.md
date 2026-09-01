# 🧭 Attest — Session 05: Turn 1 Comes Alive — The Ask Path Walks (Question → Cited Answer over HTTP)

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
| **Current phase**     | 🎉 **Turn 1 COMPLETE — the walking skeleton walks.** 1 of 7 spiral turns fully alive end-to-end. **Turn 2 (retrieval quality) is next.** |
| **Last session**      | [05] — built the entire ask path (retrieve → generate → `/ask`), Turn 1 now alive over HTTP: question → cited answer over the real 10-K. |
| **What exists**       | Everything from S04 **plus a live ask path**. `engine/app/retrieve.py` (embed question → search Qdrant top-5 → pull chunk text) + `engine/app/generate.py` (faithfulness-first prompt → Gemini → cited answer) + a **`POST /ask`** endpoint chaining them. A real `curl` returns Apple's net sales `$416,161M` **with citations `[1],[3]`** and the source chunks. **No auth, no multimodal, no eval yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya_111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 1 TB SSD. GPU still unused (Turn 1 embedding is CPU). |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). 4 atomic Conventional Commits this session (retrieve / generate+dep / endpoint / secret-plumbing). |
| **The build**         | **Turn 2 — retrieval quality**: chunking review + hybrid (vector + BM25) + cross-encoder rerank, precision measured on a small set. Also the queued `pip → uv` migration and the first `page-number` provenance work land around here. |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · figure-grounded ≥ 80% · p95 ≤ 8s. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **New this session:** `google-genai==2.17.0`. Generator = **`gemini-3.6-flash`** (revised from 2.5-flash — see Supersedes). `pip` in containers (→ `uv` at Turn 2). |
| **Domain / corpus**   | Financial. Live set = US EDGAR (primary). Doc = Apple 10-K FY2025 (`aapl_10k.pdf`, 284 chunks in Qdrant). Labeled set = FinQA / TAT-QA / ConvFinQA (not pulled yet). |
| **Next action**       | **Turn 2 — retrieval quality, fresh chat.** Resume ritual → then hybrid retrieval (vector + BM25) + cross-encoder reranker, with precision measured on a small labeled set. |
| **Open question**     | **None parked at project level.** Turn-2 decisions (BM25 lib, reranker model, how to measure precision) get decided at the step that needs them. |

---

## ⚠️ Supersedes

- **Generation model REVISED — was `gemini-2.5-flash` (implied by "Gemini locked").** Now: **`gemini-3.6-flash`**. Reason: a live web check showed **2.5-flash shuts down Oct 16 2026** (two months out — a shutdown date mid-project is the deprecated-pattern trap). `gemini-3.6-flash` (launched Jul 21 2026) is the current cheap + multimodal Flash-tier pick — stronger and cheaper than what it replaces, and still vision-capable so it reuses at Turn 3. Free-tier access **confirmed working live on Manglam's key** (the runtime question answered itself on first call). Local LLM (Ollama) remains §10 future-work.
- **SDK library DECIDED — was implicitly the old `google-generativeai`.** Now: **`google-genai==2.17.0`** — Google's new unified SDK. The old `google-generativeai` is deprecated and winding down. Enforces "no deprecated patterns" at the library level; caught before it shipped.

---

## 🎯 Session goal

**Finish Turn 1 — build the ask path so Attest walks end-to-end** (question → cited answer over HTTP,
text-only, no auth). Scoped to the ask half only; the ingest half was already done in S04.

| Bucket | One line                                                                    | Status |
| ------ | --------------------------------------------------------------------------- | ------ |
| **T1.3** | Resume gate — E: mounted, four containers Up, tree clean, last commit safe. | ✅     |
| **T1.4** | Secure the Gemini key — into `.env` (gitignored), prove it's untracked.     | ✅     |
| **T1.5** | Retrieve half — embed question (same bge-small) → search Qdrant top-5 → pull text. | ✅     |
| **T1.6** | Generate half — faithfulness-first prompt → Gemini → cited answer.          | ✅     |
| **T1.7** | Wire `POST /ask` — chain retrieve + generate behind HTTP. Turn 1 alive.     | ✅     |
| **T1.C** | Close clean — atomic commits + push, session log, instruction delta.        | ✅ (journal skipped by choice) |

---

## 📓 What happened

### T1.3 — the gate
- Standard resume ritual: all four containers `Up`, Postgres `healthy`, `main...origin/main` clean. Ground green before code.
- Micro-lesson banked: `git status -sb` = `-s` (short headline view) + `-b` (branch-vs-cloud line). That `## main...origin/main` with nothing under it = local and cloud in sync.

### T1.4 — secure the key (a gate before code, not a formality)
- Proved `.env` is git-ignored **before** the key went in: `.gitignore` carries `.env`, `.env.*`, and `!.env.example`; `git check-ignore -v .env` printed the matching rule. Belt and suspenders.
- Key written to `.env` (no spaces/quotes around `=`). `.env.example` got a **placeholder** (`paste_your_key_here`), verified via `git diff` that the real key is NOT in the tracked template — the exact leak the gate exists to catch.

### T1.5 — the retrieve half (`retrieve.py`)
- **Read `ingest.py` first** to match conventions, not guess — confirmed the payload key is `"text"`, the Qdrant connection pattern, and the embed call. (Same discipline as reading a file before writing its neighbour.)
- Three moves: `embed_question` (same `bge-small-en-v1.5`, non-negotiable — question and chunks must share one vector space / "same ruler"), `search` (Qdrant `query_points`, top-k=5), pull `hit.payload["text"]` back.
- **k=5 decided** — enough coverage for a single-doc skeleton, small enough to stay clean; tuned properly at Turn 2 when precision is measurable.
- **Deprecation avoided:** used `query_points(...)`, not the deprecated `client.search(...)`.
- Proved before building on top: `__main__` harness printed real Apple financial text for "total net sales" — retrieve works.

### T1.6 — the generate half (`generate.py`)
- New dep **`google-genai==2.17.0`** (latest, pinned via `pip index versions`). Rebuild = 565s (a real install — the correct healthy signal for a heavy dep).
- **Key-reaches-container probe FAILED first (`KEY MISSING`)** — caught before writing code that needs it. Root cause + fix in Lessons.
- **The prompt is the product.** `build_prompt` numbers chunks `[1]…[5]` and encodes Attest's DNA in three rules: answer ONLY from sources (grounding), cite each claim (traceability), and a **fixed refusal sentence** when ungrounded ("I cannot answer this from the provided sources") — a machine-checkable seam for Turn 5 self-grading, built now.
- `generate_answer` = the three `google-genai` moves: `Client(api_key=...)` → `models.generate_content(model, contents)` → `response.text`.
- First full-path run (retrieve → generate): **`$416,161 million [1],[3],[4]`** — a real, grounded, cited answer.

### T1.7 — wire `POST /ask` (pure wiring, no new logic)
- Added an `/ask` **POST** route (client *sends* the question → POST, not GET) with a Pydantic `AskRequest(question: str)` model (free validation + auto `/docs`).
- The route chains the **already-proven** `retrieve` + `generate_answer`, returns `{question, answer, sources}` — `sources` is the seed of the blueprint's "source card" (proof of grounding).
- Live-mount + `--reload`, no rebuild. A real `curl` to `http://localhost:8000/ask` returned the cited answer **over HTTP** with the net-sales-by-category table as source [1]. **Turn 1 genuinely, fully alive.**

### T1.C — close clean
- **Journal skipped by Manglam's choice** — he keeps interview/HR framing out of build sessions; `JOURNAL.md` deferred (noted: it's a repo problem+fix log, distinct from HR practice — available whenever he wants it).
- **4 atomic commits**, Conventional Commits, one-line bodies, pushed. `main...origin/main` clean — external-drive two-places rule satisfied.

---

## ✅ Decisions Locked This Session

- **Generator model = `gemini-3.6-flash`** (revised from 2.5-flash, which has an Oct 2026 shutdown).
- **SDK = `google-genai==2.17.0`** (the new unified SDK, over the deprecated `google-generativeai`).
- **Retrieval top-k = 5** for the single-doc skeleton (re-tuned at Turn 2).
- **Secret injection = least-privilege** — engine gets only `GEMINI_API_KEY` via `environment:`, not the whole `.env` (that stays postgres's `env_file`).
- **Prompt encodes the DNA** — sources-only + cite-each-claim + fixed refusal sentence (the self-grading seam).
- **Response shape = `{question, answer, sources}`** — sources returned as grounding proof.
- **Turn 1 declared complete** — walking skeleton alive end-to-end over HTTP.

---

## 🧠 Hard-Won Lessons

- **`.env` next to compose does TWO different jobs — don't conflate them.** (1) Variable substitution fills `${VAR}` *inside the compose file*; (2) injecting a var *into a container's environment* (so `os.getenv` sees it) is a **separate, explicit** step. Postgres had #2 via `env_file`; engine had neither for the Gemini key → `KEY MISSING`. Fix: `environment: - GEMINI_API_KEY=${GEMINI_API_KEY}` on the engine service, then **recreate** the container (`up -d`, not a rebuild — config change, not a dep change).
- **Least-privilege secrets are a real design choice, not pedantry.** Engine gets only the one key it uses, not the whole `.env` (no Postgres password it has no business holding). Clean answer to "how do you handle secrets?"
- **Verify model/API names LIVE before pinning.** Training memory lags the API. `gemini-2.5-flash` looked right but shuts down Oct 2026; the current pick is `gemini-3.6-flash`. A 30-second web check saved shipping a dying model. (→ promoted to Standing Rule.)
- **Same model on both sides of a vector search — non-negotiable.** Question and chunks must be embedded by the *same* `bge-small`, or the vectors live in different spaces and "nearest" is meaningless. Same ruler on both sides.
- **Read the neighbour file before writing.** Reading `ingest.py` first confirmed the payload key `"text"` — a mismatch there (`"content"` vs `"text"`) would've silently returned empty chunks. Match conventions, don't guess them.
- **Prove-then-build makes the endpoint trivial.** `/ask` was pure wiring with zero new logic because retrieve + generate were each proven in isolation first. The payoff of the discipline.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **Nearly pinned `gemini-2.5-flash` from training memory** — a model with a two-months-out shutdown date. The live web check (prompted by the "no deprecated patterns" instinct) caught it before it shipped. The rule worked, but the reflex to reach for the remembered name is the thing to keep watching.
- **Tagged `JOURNAL.md` with HR question numbers (Q13/14/15) mid-build** — pulled interview framing into a build session, which Manglam has scoped to end-of-project. The file itself is a legitimate repo record (technical problem+fix), but the framing was noise. Correction accepted: keep HR/interview framing out of build sessions.

---

## ⏭️ Next Session — Turn 2, retrieval quality (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (four Up) → `git status -sb`. |
| 1    | **Hybrid retrieval** — add BM25 (keyword) alongside the existing vector search; fuse the two result sets.     |
| 2    | **Cross-encoder rerank** — re-score the fused candidates with a reranker so the best chunks rise to the top.  |
| 3    | **Measure precision** — build a small labeled set and measure retrieval/context precision against the §02 ≥ 0.85 target. |
| 4    | **Queued housekeeping** — `pip → uv` migration in the Dockerfiles; start the page-number provenance work (chunk-id → page-N citations). |
| 5    | **(Optional) GPU passthrough** — if reranker/embedder load justifies it, wire NVIDIA Container Toolkit and watch the 4060 light up in Task Manager. |

**Decided at the step, not now:** BM25 library, exact reranker model, and how the fusion (e.g. RRF) is weighted — chosen inside Turn 2 when retrieval quality is measurable.

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
