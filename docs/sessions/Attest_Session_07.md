# 🧭 Attest — Session 07: Turn 2 Closes — The Reranker Lands, Page Provenance Threads Through, Two Bad Gold Keys Caught (0.30 → 0.57, Hit Rate Restored)

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
| **Current phase**     | 🎉 **Turn 2 COMPLETE — retrieval quality done, both halves.** 2 of 7 spiral turns fully alive. **Turn 3 (multimodal) is next.** |
| **Last session**      | [07] — migrated pip→uv, landed the cross-encoder reranker (R&D rescued rank 7→top-5), threaded page provenance end-to-end, and caught + fixed two wrong gold-set keys. |
| **What exists**       | Everything from S06 **plus**: **(1)** `uv` in both Dockerfiles (pinned `0.12.1`); **(2)** a **cross-encoder reranker** (`BAAI/bge-reranker-v2-m3` via `sentence-transformers` CrossEncoder) that re-scores the top-20 RRF pool → top-5 in `retrieve.py`; **(3)** **page provenance** carried extract→chunk→store→retrieve→generate→`/ask` (each Qdrant point payload now `{text, page}`, `retrieve` returns `list[dict]`, source cards show the page); **(4)** a **corrected gold set** (2 of 6 keys were wrong — fixed against the filing). **No auth, no multimodal, no eval-on-benchmark yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 1 TB SSD. **GPU still unused** — the reranker ran on CPU (small batches: 20 pairs/query, fine). GPU passthrough remains deferred to the turn that demands it (likely Turn 3 vision). |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). This session: 1 commit for uv (early) + 4 atomic Conventional Commits at close (reranker / page-provenance / gold-fix / scorer). |
| **The build**         | **Turn 3 — multimodal**: extract figures → describe each via the vision model (Gemini, already integrated) → embed the description alongside text → a chart-only question answered correctly. **First real GPU/Task-Manager moment likely lands here.** |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · figure-grounded ≥ 80% · p95 ≤ 8s. |
| **Turn-2 final numbers (interim ruler, 6 Qs, CORRECTED keys)** | **Hybrid + reranker, top-5:** hit rate **1.00** (6/6) · precision **0.57** (§02 ≥ 0.85 is a Turn-5 RAGAS/FinQA gate, NOT this ruler). Per-Q: net sales 4/5 · cost of sales 1/5 · net income 5/5 · R&D 1/5 · EPS 3/5 · shares 3/5. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **New this session:** `CrossEncoder` (already inside `sentence-transformers` — **no new dep**) + model `BAAI/bge-reranker-v2-m3`. **`uv` now the installer in both containers** (was `pip`). Generator = `gemini-3.6-flash`. |
| **Domain / corpus**   | Financial. Live set = US EDGAR (primary). Doc = Apple 10-K FY2025 (`aapl_10k.pdf`, **284 chunks, dense+sparse, now with `page` in payload**). Labeled set = FinQA / TAT-QA / ConvFinQA (not pulled yet). |
| **Next action**       | **Turn 3 — multimodal, fresh chat.** Resume ritual → figure extraction (PyMuPDF) → vision-LLM description → embed alongside text → chart-only question. Decide GPU passthrough at the step if the vision load justifies it. |
| **Open question**     | **None parked at project level.** Turn-3 decisions (figure-extraction approach, how figure descriptions are stored/keyed, whether GPU passthrough is wired) get decided at the step that needs them. |

---

## ⚠️ Supersedes

- **`retrieve()` contract CHANGED — was `retrieve(question) -> list[str]`; now `-> list[dict]`** where each dict is `{"text": str, "page": int}`. Reason: page provenance needs to ride with the chunk all the way to the answer, and a bare string has nowhere to hold it. Ripple was contained + fixed same session: `generate.py` reads `chunk["text"]`/`chunk["page"]`, `score.py` reads `chunk["text"]`, `main.py` needed **zero** change (it passes chunks through untouched — the contract-preserving payoff). Any future consumer of `retrieve` must expect dicts.
- **Ingest is now PER-PAGE chunked with page provenance — was join-all-pages-then-chunk.** `extract_text() -> str` replaced by `extract_pages() -> list[(page_num, text)]`; `chunk_text()` replaced by `chunk_pages()` which splits each page separately and tags each chunk with its page. Each Qdrant point payload is now `{text, page}` (was `{text}`). Page number = **PDF page order (`index+1`)**, NOT the printed footer label — known small gap, notable at interview, fine for now. Re-ingest ran clean: **284 chunks** (same count — per-page split didn't fragment the doc).
- **`pip → uv` migration DONE — was "queued, first step next session" since S03.** Both Dockerfiles now `COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/` then `uv pip install --system --no-cache -r requirements.txt`. `uv 0.12.1` verified current live (released 2026-07-31) before pinning. `--system` = install into the container's own Python (no venv — the container is already the isolation boundary).
- **Reranker ADDED — `BAAI/bge-reranker-v2-m3`.** Verified live as the current best open-weight cross-encoder; same BGE family as the `bge-small` embedder (clean, consistent story). Ships inside `sentence-transformers` (`CrossEncoder`) — **no new dependency**. Pipeline is now: dense+sparse prefetch (20 each) → **RRF fuse to a pool of 20** → cross-encoder re-scores all 20 → **top-5**. This is the layer that rescued the buried R&D chunk.
- **Gold-set keys CORRECTED — 2 of 6 were WRONG.** `cost of sales 132,729 → 220,960` (the old key was *income before taxes* — a neighbouring row) and `R&D 31,370 → 34,550` (the old key was the *2024* column — a prior-year value). Both were the comparative-statement trap that S06 *named* but still fell into. Re-verified **all six** against the filing by grep; the other four held (net sales 416,161 · net income 112,010 · diluted EPS 7.46 · diluted shares 15,004,697). The interim ruler is trustworthy again.

---

## 🎯 Session goal

**Close Turn 2's back half: land the reranker, prove it moved the number the right way, then pay down the S04 page-provenance debt — and fix whatever the deeper source-visibility exposes.**

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T2.7** | Resume gate — E: mounted, four containers Up, tree clean, last commit safe.       | ✅     |
| **T2.8** | `pip → uv` migration in both Dockerfiles, in its own clean window.                 | ✅ uv 0.12.1 |
| **T2.9** | Cross-encoder reranker — prove in isolation, wire into `retrieve`, re-measure.     | ✅ rank 7→top-5 · 0.30→0.57 · hit 1.00 |
| **T2.11** | Page provenance — thread page through extract→store→retrieve→generate→`/ask`.     | ✅ (unplanned bonus: caught 2 bad gold keys) |
| **T2.C** | Close clean — atomic commits + push, session log, instruction delta.              | ✅     |

---

## 📓 What happened

### T2.7 — the gate
- Standard resume ritual: four containers `Up`, Postgres `healthy`, `main...origin/main` clean. Green before code.

### T2.8 — the uv migration
- Swapped `pip` for `uv` in both `engine/Dockerfile` and `shell/Dockerfile`: `COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/` + `RUN uv pip install --system --no-cache -r requirements.txt`.
- **Verified `uv 0.12.1` current live before pinning** (standing rule) — latest release 2026-07-31.
- Rebuild took 438s — that's the torch/onnxruntime **wheel downloads** on a clean rebuild, not uv being slow (uv's speedup is on resolve/install, not the download bytes). All four containers back `Up`.
- Committed early as its own atomic unit (`build: migrate engine + shell to uv from pip`), pushed.

### T2.9 — the reranker (prove-then-build, three sub-steps)
- **Tool choice:** cross-encoder — reads (question, chunk) **together** and scores their match, vs the bi-encoder embedder that scored them apart. That joint read is exactly what rescues a keyword-poor chunk. `BAAI/bge-reranker-v2-m3`, verified current best open-weight, same BGE family, ships in `sentence-transformers` → **no new dep**.
- **Sub-1 — proved in isolation:** scored one clearly-relevant vs one clearly-irrelevant pair for the R&D question → `[0.377, 0.00002]` — a ~17,000× gap. Tool works.
- **Sub-2 — wired into `retrieve.py`:** RRF now returns a **pool of 20** (was final 5); `rerank()` re-scores all 20 with the cross-encoder → top-5. Public contract preserved at this point (still `list[str]`), so scorer + `/ask` untouched *at this step*. Ran the file: **`31,370`/R&D chunk landed at position 2 — rescued from rank 7 into the top-5.** Exactly the S06 diagnosis, now fixed.
- **Sub-3 — re-measured:** hit rate **0.83 → 1.00** (regression dead), precision **0.30 → 0.57** (nearly doubled the baseline). Both targets moved the right way. Fixed the stale `--- baseline: vector-only ---` printout to `--- hybrid + reranker, top-5 ---` so the log stops lying.

### T2.11 — page provenance (the S04 debt, plus an unplanned catch)
- **The debt:** `extract_text()` joined all 65 pages with `\n` before chunking → page boundaries erased → citations could only ever say "chunk N".
- **The fix (one real design decision):** chunk each page *separately* so every chunk is born knowing its page. `extract_pages()` returns `(page_num, text)`; `chunk_pages()` splits per page and tags `{text, page}`. Payload now carries `page`. Re-ingest → **284 chunks** (same count — sanity signal). Verified payload: `dict_keys(['text','page'])`, page 1 on first chunk.
- **Rippled the dict up the stack:** `retrieve.py` returns `list[dict]` (contract change — see Supersedes); `generate.py` prompt now shows `[i] (page N) …`; `main.py` **needed zero change** (passes chunks through → `/ask` gained the page for free — the prove-then-build payoff). Live `curl` confirmed `"page": N` on every source card over HTTP.
- **THE CATCH:** with the full source text + page now in front of us, the `/ask` output on the R&D question exposed that the model answered **34,550** while our gold key said **31,370** — and reading the income statement (page 33), 34,550 is the *2025* value, 31,370 is *2024*. Pulling the raw statement (lines 1850–1935) showed a **second** bad key too: cost of sales was keyed to `132,729`, which is *income before taxes*, not cost of sales (`220,960`). Two of six gold keys were wrong. Re-verified all six by grep against the filing, corrected the two, closed the open `]` in `gold_set.py`. Re-ran scorer → **1.00 / 0.57 on trustworthy keys.**

### T2.C — close clean
- Reconciled `git status -s` before committing (S06 lesson): 5 modified files, Dockerfiles already in. **4 atomic commits** — reranker / page-provenance (ingest+generate together) / gold-fix / scorer-dict — pushed, `main...origin/main` clean. (`retrieve.py` changed twice this session — reranker then dict-switch — folded into the reranker commit by choice; both are this session's work landing together.)
- **Journal:** the gold-key bug (problem: 2 keys wrong → caught via page-visibility → re-verified all six by grep → fixed) is textbook `JOURNAL.md` / Q13-14-15 material. Left to Manglam's choice, as before.

---

## ✅ Decisions Locked This Session

- **`uv` is the container installer** (both Dockerfiles), pinned `ghcr.io/astral-sh/uv:0.12.1`, `--system` install (no venv in-container).
- **Reranker = `BAAI/bge-reranker-v2-m3`** via `sentence-transformers` CrossEncoder (no new dep). Pipeline: RRF pool 20 → rerank → top-5.
- **Page provenance = per-page chunking**, payload `{text, page}`, page = PDF order (`index+1`), NOT printed footer label.
- **`retrieve()` returns `list[dict]`** (`{text, page}`) — contract change, ripple fixed same session.
- **Gold set corrected** — cost of sales `220,960`, R&D `34,550`; re-verified all six by grep.
- **Turn 2 declared COMPLETE.** Retrieval is measurably, defensibly better. **Not** grinding toward 0.85 on six questions — that's overfitting the interim ruler; the real gate is RAGAS/FinQA at Turn 5.

---

## 🧠 Hard-Won Lessons

- **The comparative-statement trap can hide INSIDE your measuring stick.** S06 *named* the three-year-column trap and still shipped two wrong keys (a prior-year value AND a neighbouring-row value). A poisoned gold set silently mis-scores forever. **When one key is found wrong, re-verify ALL of them** — don't spot-fix the one you noticed.
- **Deeper source visibility is a bug-catching tool, not just a UX nicety.** We only caught the bad gold keys because the page-provenance work put the full source text + page in front of us. Auditability catching our *own* error is the Attest thesis proving itself on our own build.
- **Name the ripple before you make it: contract-preserving vs contract-breaking.** Adding rerank *inside* the existing `list[str]` contract touched nothing downstream. Switching to `list[dict]` for the page *did* ripple — but only to the two consumers that read chunk internals; `main.py` (which just passes them through) was untouched. Knowing which changes ripple = knowing what to test.
- **A cross-encoder rescues what RRF buries.** Empirically shown, not taken on faith: the keyword-poor R&D chunk sat at rank 7 under fusion and climbed to top-5 once a model read query+chunk together. This is *why* the reranker earns its place — the concrete Q4/Q13 answer.
- **Page provenance forces per-page chunking.** You cannot recover the page after a `\n`-join; the page has to be captured at extraction and carried through every stage. Provenance is an architecture decision, not a formatting afterthought.
- **Scratch files in `/code` don't survive a rebuild.** `aapl_extracted.txt` from S06 was gone after the uv rebuild (it lives inside the image's writable layer, not a mount). Correct move: regenerate from the *same* extractor (`extract_pages`) so keys match what got chunked — never re-implement extraction for ground truth.
- **`uv --system` in a container needs no venv.** The container is already the isolation boundary; a venv inside it is redundant. `COPY --from` the pinned uv binary is the clean, reproducible install pattern.
- **A trusted 0.57 beats an overfit 0.85.** The string-anchored ruler *undercounts* (a chunk can be genuinely relevant without repeating the literal number), so chasing 0.85 on six hand-picked questions optimises the ruler, not the system. Hold the line until the real RAGAS/FinQA gate at Turn 5.

### ⚠️ Process errors this session — Claude's (logged honestly)
- **Reverted to predict-first quizzing AGAIN** ("predict it first: which should be higher?") despite this being a **promoted Standing Rule** since S03/S04. Manglam flagged it mid-session ("I told you I will ask whenever I feel something odd"). This is the rule's *third* recorded relapse — the pattern is sticky and needs active suppression, not just the rule on the page. **No predict-first / quiz framing unless Manglam says "activate learning mode." Deliver the recommendation, let him pull.**
- **Over-explained early in the session** — multi-line teaching on things Manglam wanted in 1–2 lines. He set an explicit format rule: **keep explanations to 1–2 lines until he asks for detail.** → Instruction delta this session.

---

## ⏭️ Next Session — Turn 3, multimodal (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (four Up) → `git status -sb`. |
| 1    | **Extract figures** — pull images/charts out of the PDF (PyMuPDF), decide how a figure is identified + where it's stored. |
| 2    | **Describe each figure** — vision LLM (Gemini, already integrated — one API reused) turns each figure into rich text. |
| 3    | **Embed alongside text** — the figure description drops into the same dense+sparse pipeline, tagged so we know it's a figure (and its page). |
| 4    | **Chart-only question** — prove a question whose answer lives ONLY in a chart gets answered correctly (the §02 figure-grounded ≥ 80% aspiration). |
| 5    | **(Likely) GPU passthrough** — the vision model is the heaviest load yet; if CPU crawls, wire NVIDIA Container Toolkit and **watch the 4060 light up in Task Manager** (probably the first real GPU moment). |

**Decided at the step, not now:** figure-extraction approach, how figure descriptions are keyed/stored in Qdrant, and whether GPU passthrough is justified — chosen inside Turn 3 when the load is measurable.

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
