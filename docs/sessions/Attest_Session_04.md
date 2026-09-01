# 🧭 Attest — Session 04: Turn 1 Begins — The Ingest Path Lives (PDF → Vectors in Qdrant)

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
| **Current phase**     | 🧭 **Turn 1 IN PROGRESS — the ingest half is DONE.** The ask half (question → cited answer) is next. 0 of 7 turns fully complete. |
| **Last session**      | [04] — built the entire ingest path: one real 10-K → PyMuPDF text → recursive chunk → bge-small embed → 284 vectors live in Qdrant. |
| **What exists**       | Everything from S03 **plus a working ingest pipeline**: `engine/app/ingest.py` turns `data/corpus/aapl_10k.pdf` into **284 points in Qdrant collection `attest_chunks`** (384-dim, Cosine). First real corpus file on disk (gitignored). **No ask path, no auth, no multimodal yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine (NEW — logged for planning heavy turns)** | **Agastya_111** — AMD Ryzen 7 7435HS · **16 GB RAM** · **NVIDIA RTX 4060 Laptop GPU (8 GB VRAM)** · 1 TB SSD headroom. Real GPU available → plan Turn 2/3 heavy models around GPU passthrough. |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). Atomic Conventional Commits held. |
| **The build**         | **The ask path** — question → embed → search Qdrant top-k → build prompt → **Gemini answers with citations** — is the next thing to build. Text only, no auth. That closes Turn 1 (alive end-to-end). |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged from S03). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · figure-grounded ≥ 80% · p95 ≤ 8s. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **New this session:** `pymupdf` · `langchain-text-splitters` · `sentence-transformers` (torch) · `qdrant-client`. Generator = **Gemini (free tier) — locked.** `pip` in containers (→ `uv` at Turn 2). |
| **Domain / corpus**   | Financial. Live set = **US EDGAR (primary)**. First doc = **Apple 10-K, FY ended 2025-09-27** (`aapl_10k.pdf`, 65 pages, 2.5 MB). Labeled set = FinQA / TAT-QA / ConvFinQA (not pulled yet). |
| **Next action**       | **Ask path, in a fresh chat.** Step 0 = put Gemini key in `.env` (gitignored), confirm not tracked. Then embed question → search → prompt → Gemini cited answer. |
| **Open question**     | **None parked at project level.** First ask-path decisions (top-k value, prompt shape) get decided at the step that needs them, next chat. |

---

## ⚠️ Supersedes

- **Generation LLM DECIDED — was parked ("a fast instruct model, chosen at the turn").** Now: **Gemini, free tier, locked.** Reasoning: (1) faithfulness is the product — a strong instruction-follower is needed so Turn 5 self-grading *measures* the generator instead of fighting it; (2) **one API reused at Turn 3** (Gemini is vision-capable — same integration extends to reading charts); (3) free tier covers a solo builder at this scale; (4) **deployment cost** — an API LLM ships as a lightweight shell calling someone else's GPU, so the production host stays tiny/cheap (Manglam's own reasoning — the real "why local doesn't ship" answer). Local LLM (Ollama) parked as §10 future-work / "runs fully offline" flex. Groq considered (faster, but not vision-capable) → rejected in favour of one-API-reused.
- **GPU passthrough DEFERRED — deliberate, was implicit.** Turn 1 runs embedding on **CPU** (bge-small embedded 284 chunks in ~22s — GPU would save seconds on a one-time job). GPU-in-Docker passthrough (NVIDIA Container Toolkit) becomes a **logged decision at Turn 2/3** when heavy models (bigger embedders, rerankers, the vision model) actually demand it. One hard thing at a time.

---

## 🎯 Session goal

**Start Turn 1 — build the ingest path end-to-end, prove-then-build at every step.** Scoped to the
ingest half only (PDF → searchable vectors); the ask half deliberately pushed to a fresh context
window when this chat got long.

| Bucket | One line                                                                    | Status |
| ------ | --------------------------------------------------------------------------- | ------ |
| **T1.0** | Resume gate — E: mounted, four containers Up, tree clean.                  | ✅     |
| **T1.1** | First document — one real US EDGAR 10-K into `data/corpus/` (gitignored).  | ✅ Apple 10-K |
| **T1.2** | Ingest path — extract → chunk → embed → store in Qdrant.                   | ✅ 284 pts |
| **T1.C** | Close clean — commit, log, prime next chat (ask path).                     | ✅     |

---

## 📓 What happened

### T1.0 — the gate
- Standard resume ritual: all four containers `Up`, Postgres `healthy`, `main...origin/main` clean. Ground confirmed before a line of code.

### T1.1 — the first document (a genuine first-time-EDGAR fight)
- **Source is EDGAR HTML, not PDF.** Chose Apple's latest **10-K** (FY ended 2025-09-27) — clean digital text, famous numbers to sanity-check, real EDGAR filing.
- **The Inline Viewer trap.** `Print → Save as PDF` from EDGAR's `ix?doc=` viewer captured **only one page** (the viewer is a scrolling frame; Print sees only the visible slice).
- **The fix = strip `ix?doc=` from the URL** → points straight at the raw `.htm` → full document → Print → 65-page PDF. (Reusable trick: removing `ix?doc=` from any EDGAR URL gives the printable original.)
- Landed at `data/corpus/aapl_10k.pdf` (2.5 MB). Created `data/corpus/` + `.gitkeep`, added ignore rule (`data/corpus/*` except `.gitkeep`). **Confirmed git does NOT track the PDF** — the external-drive rule holding (precious+small in git; corpus re-fetchable outside).

### T1.2 — the ingest path (prove-then-build, six sub-problems)
- **Sub-1: PyMuPDF reads it.** Added `pymupdf==1.24.10`, mounted `./data/corpus:/code/data/corpus:ro` (read-only — a filing is source-of-truth evidence, code must never corrupt it). Probe proved page 1: 65 pages, 2111 clean chars, real English. (Requirements change forced the rebuild — deps bake into the image at build time; the mount applies at container start.)
- **Sub-2/3: full extract.** Wrapped in `extract_text()`, joined all 65 pages → **215,074 chars.** Flagged a known debt: joining with `\n` drops page provenance; citations start as "chunk N" before "page N" — paid when real citations get wired.
- **Sub-4: chunking (the 1000/150 decision goes live).** Added `langchain-text-splitters==0.3.2`, used `RecursiveCharacterTextSplitter` (smart boundary-seeking: paragraph → sentence → word). Result: **284 chunks, avg 847 chars.** Sample chunk eyeballed = coherent paragraph, no mid-word butchery. Decision validated on real data.
- **Sub-5: embedding.** Added `sentence-transformers==3.3.1` (pulls torch, 526 MB — a *long* build is the correct healthy signal here, opposite of S03's 2s-build alarm). `bge-small-en-v1.5`, CPU. First run downloaded the model (~130 MB, cached after). **284 vectors × 384 dims** in ~22s on CPU.
- **Sub-6: store in Qdrant.** Added `qdrant-client==1.12.1`. Collection `attest_chunks` (384-dim, **Cosine** — compares direction/meaning, standard for sentence embeddings). Each point = id + vector + **payload carrying the chunk text** (so retrieval hands back the words to cite). Reached Qdrant **by service name `qdrant`, not `localhost`** (S03 lesson, load-bearing). Dashboard confirmed: **284 points, green.**
- **Deprecation caught in the wild (Manglam spotted it).** `recreate_collection` warned as deprecated → replaced with the modern explicit pattern (`collection_exists` → `delete_collection` → `create_collection`). "No deprecated patterns" rule enforced live.

### The two decisions closed this session
- **Generator = Gemini** (see Supersedes for full reasoning — the deployment-cost argument was Manglam's).
- **GPU deferred to Turn 2/3** (see Supersedes).

---

## ✅ Decisions Locked This Session

- **First corpus doc = Apple 10-K** (FY 2025-09-27), via the strip-`ix?doc=` EDGAR trick.
- **Chunking = 1000 chars / 150 overlap, `RecursiveCharacterTextSplitter`** (validated: 284 chunks, avg 847).
- **Embedding = `bge-small-en-v1.5`, local, CPU for Turn 1** (384-dim, Cosine in Qdrant).
- **Qdrant collection = `attest_chunks`**, points carry chunk text as payload.
- **Generator = Gemini, free tier** (over Groq and over local LLM — one API, vision-reusable, cheap to ship).
- **GPU passthrough deferred** to Turn 2/3 (deliberate).
- **Modern Qdrant collection pattern** (no `recreate_collection`).
- New deps pinned: `pymupdf` · `langchain-text-splitters` · `sentence-transformers` · `qdrant-client`.

---

## 🧠 Hard-Won Lessons

- **EDGAR's Inline Viewer (`ix?doc=`) can't be printed whole.** It's a scrolling frame; Print captures one page. Strip `ix?doc=` from the URL to reach the raw printable `.htm`. (First-time-EDGAR trap, now a reusable trick.)
- **`exec` never downloads; `--build` does — and only when `requirements.txt` changed.** The torch download is a one-time cost baked into the image. Stable requirements → instant `exec`, zero re-downloads. (Cleared a real confusion.)
- **A long build is the healthy signal for heavy deps** — the inverse of S03's "2s build = nothing installed." Read build time in context: fast when it should be slow = alarm; slow when pulling torch = correct.
- **Reach neighbours by service name, never `localhost`** — reconfirmed in live code (`QDRANT_HOST = "qdrant"`). The S03 lesson is now load-bearing in the ingest path.
- **Deployment cost decides local-vs-API LLM.** A local model needs a 24/7 GPU host (expensive) or crawls on CPU; an API LLM ships as a light shell calling someone else's GPU, keeping the production box tiny. This is the honest interview answer for "why not local?" — and Manglam reasoned to it himself.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **Too-thin EDGAR guidance for a first-time user.** Told Manglam to "download the 10-K" without walking the EDGAR UI step-by-step; he (rightly) asked for proper hand-holding. Root fix: when a tool/site is new to Manglam, walk the UI click-by-click the first time, don't assume familiarity.
- **Reverted to guru-quiz habit again** ("which change forces the rebuild?") after the standing rule to stop. Manglam flagged it a second time → now **promoted to Instructions** (Session 04 delta), not just logged. This is the mechanism working: flagged twice → promoted so it can't recur.

---

## ⏭️ Next Session — the ask path, Turn 1 comes alive (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (four Up) → `git status -sb`. |
| 1    | **Gemini key into `.env`** (gitignored) — confirm it is NOT tracked before writing any code that uses it.     |
| 2    | **Embed the question** — reuse `bge-small` (SAME model as ingest, non-negotiable) to vectorise the incoming question. |
| 3    | **Search Qdrant** — retrieve top-k nearest chunks (decide k at the step). Pull back the payload text.          |
| 4    | **Build the prompt** — stuff retrieved chunks + question into a faithfulness-first prompt ("answer only from these sources; cite them; admit if you can't"). |
| 5    | **Call Gemini** — get the answer, wire it into the engine `/ask` endpoint, return a **cited answer**. Text only. **Turn 1 alive end-to-end.** |
| 6    | **Open `JOURNAL.md`** — log the first real Turn-1 problem + concrete fix (Q13/14/15 insurance).               |

**Decided at the step, not now:** top-k value, exact prompt wording, and how citations are represented in the response (chunk-id first, page-number later — see the provenance debt above).

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
