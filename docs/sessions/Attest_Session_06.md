# 🧭 Attest — Session 06: Turn 2 Opens — The Eval Ruler, Then Hybrid Retrieval Lives (0.30 → 0.43, One Regression Diagnosed)

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
| **Current phase**     | 🧭 **Turn 2 IN PROGRESS — the front half is DONE.** Eval ruler built, baseline read, hybrid retrieval live. The back half (cross-encoder rerank → re-measure) is next. 1 of 7 turns fully complete. |
| **Last session**      | [06] — built a 6-question eval gold set + precision scorer, read the vector-only baseline, then landed full hybrid retrieval (dense + BM25 sparse, RRF fusion). Precision climbed, one answer regressed, regression diagnosed to rank 7. |
| **What exists**       | Everything from S05 **plus (1)** an interim eval harness — `engine/app/eval/gold_set.py` (6 fact-lookup Qs, string-anchored) + `engine/app/eval/score.py` (hit-rate + precision over the real `retrieve`); **(2)** a **hybrid** retrieval path — `attest_chunks` re-ingested with **two named vectors per chunk** (`dense` bge-small + `sparse` Qdrant/bm25, IDF on), and `retrieve.py` rewritten to prefetch both and fuse server-side with RRF. **No reranker, no auth, no multimodal, no eval-on-benchmark yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya_111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 1 TB SSD. GPU still unused (embedding + BM25 are CPU). **The reranker next session is a real neural net — first likely GPU/Task-Manager moment.** |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). 4 atomic Conventional Commits this session (eval / fastembed-dep / re-ingest / hybrid-search). |
| **The build**         | **Turn 2 back half** — cross-encoder reranker to re-sort the top-20 hybrid candidates (rescue the R&D answer from rank 7), then re-measure precision toward §02 ≥ 0.85 with hit rate restored to 1.00. Queued alongside: **`pip → uv` migration** (next session's first step) and **page-number provenance**. |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · figure-grounded ≥ 80% · p95 ≤ 8s. **First real measurement against a target began this session** (interim ruler). |
| **Baseline numbers (interim ruler, 6 Qs)** | **Vector-only top-5:** hit rate **1.00** (6/6) · precision **0.30**. **Hybrid (RRF) top-5:** hit rate **0.83** (5/6) · precision **0.43**. Precision ↑, hit-rate ↓ (R&D question regressed — diagnosed, see below). |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **New this session:** `qdrant-client[fastembed]` (the `[fastembed]` extra pulls FastEmbed + onnxruntime for BM25 sparse vectors). Generator = `gemini-3.6-flash`. `pip` in containers (→ `uv` next session). |
| **Domain / corpus**   | Financial. Live set = US EDGAR (primary). Doc = Apple 10-K FY2025 (`aapl_10k.pdf`, **284 chunks, now dense+sparse** in Qdrant). Labeled set = FinQA / TAT-QA / ConvFinQA (not pulled yet). |
| **Next action**       | **Turn 2 back half, fresh chat.** Resume ritual → **`pip → uv` migration first** → cross-encoder reranker over the top-20 hybrid candidates → re-run scorer (target: precision up, hit rate back to 1.00). |
| **Open question**     | **None parked at project level.** Reranker-model choice, rerank candidate depth, and whether GPU passthrough is justified get decided at the step that needs them, next chat. |

---

## ⚠️ Supersedes

- **`attest_chunks` collection schema CHANGED — was a single unnamed dense vector; now TWO named vectors per point.** `dense` = bge-small-en-v1.5 (384-dim, Cosine) + `sparse` = Qdrant/bm25 (with `Modifier.IDF` on, so rarity is computed server-side across all 284 chunks). This is the foundation native hybrid runs on. Any code that queried the old unnamed vector is now invalid (only `retrieve.py` did — rewritten this session).
- **Retrieval is now HYBRID — was vector-only.** `search()` in `retrieve.py` no longer takes a pre-computed vector; it takes the **question string**, embeds it two ways (dense + sparse), prefetches top-20 from each, and fuses server-side with **RRF** (Reciprocal Rank Fusion — ranks by agreement across both lists, not by adding incompatible scores). Public contract **preserved**: `retrieve(question) -> list[str]`, so the scorer and `/ask` are untouched. `retrieve()` is now a one-line pass-through.
- **New dependency — `qdrant-client[fastembed]`.** The `[fastembed]` extra installs FastEmbed (pulls onnxruntime) so the client computes BM25 sparse vectors locally — no paid cloud-inference cluster needed. `Dockerfile` pip line hardened with `--timeout 120 --retries 5` (heavy wheel, home connection).
- **Interim eval ruler ESTABLISHED — a Turn-2 instrument, not the final harness.** 6 hand-built fact-lookup questions over the Apple 10-K, **string-anchored** (a chunk is "relevant" iff it contains the exact answer string, e.g. `31,370`). Numbers were **grepped from the document**, never trusted from memory. This is the bridge ruler until FinQA/TAT-QA/ConvFinQA land as the real test set at **Turn 5** — the §02 numbers still officially come from that benchmark, not from these six.
- **`pip → uv` migration STILL queued — now explicitly the FIRST step of the next session** (was "around Turn 2"). Deliberately deferred once more to keep this session to one hard thing (hybrid re-ingest). It lands right before the reranker dep, when the dep list gets real.

---

## 🎯 Session goal

**Open Turn 2 the honest way: build a measuring stick and read the baseline before improving anything —
then (pushed on by choice) land hybrid retrieval and diagnose whatever the number reveals.**
The Attest DNA turned on our own build: *measure first, improve second; a change only ships if it moves the number.*

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T2.0** | Resume gate — E: mounted, four containers Up, tree clean, last commit safe.      | ✅     |
| **T2.1** | The measuring stick — 6-Q string-anchored gold set, numbers grepped from the doc. | ✅     |
| **T2.2** | Baseline reading — scorer over today's vector-only top-5.                         | ✅ hit 1.00 / prec 0.30 |
| **T2.3** | Sparse proof — add FastEmbed, prove one BM25 sparse vector in isolation.          | ✅     |
| **T2.4** | Re-ingest — recreate collection with named dense+sparse, re-embed all 284.        | ✅     |
| **T2.5** | Hybrid search — rewrite `search()` for dense+sparse prefetch + RRF fusion.        | ✅     |
| **T2.6** | Re-measure — run the scorer again, read the delta honestly.                       | ✅ hit 0.83 / prec 0.43 → regression diagnosed |
| **T2.C** | Close clean — atomic commits + push, log, instruction delta.                      | ✅     |

---

## 📓 What happened

### T2.0 — the gate
- Standard resume ritual: four containers `Up`, Postgres `healthy`, `main...origin/main` clean. Ground green before code.

### T2.1 — the measuring stick (the honest opener)
- **The framing that shaped the whole session:** Turn 2's job is "make retrieval better," but "better" is meaningless without a number. We had **zero** measurement — one eyeballed net-sales answer. So we built the ruler *before* touching BM25, so every later change has to **earn its place** against a baseline.
- **Two decisions locked:** (1) relevance judged **string-anchored** — a chunk counts if it contains the exact answer string → reproducible, re-runnable, no human re-judging; clean for fact-lookups (the right shape for a baseline). (2) ground-truth numbers **grepped from the document**, not read by eye and not recalled from memory → non-circular (reads the *filing*, never the retriever).
- **Same-extractor discipline:** dumped the doc text by reusing `ingest.py`'s own `extract_text()` (→ `/code/aapl_extracted.txt`, gitignored) so the grepped keys match what actually got chunked, byte-for-byte. Writing to the read-only corpus mount failed first (Errno 30 — see Claude errors); redirected to writable `/code`.
- **The comparative-statement trap, caught live:** a 10-K shows every line item across **three years** (FY2025 · FY2024 · FY2023). Keying on a bare number risks matching a *prior-year* figure. Rule adopted: **key on the FY2025 (leftmost) value**, distinctive enough not to collide.
- **Memory was wrong, the document was right:** cost of sales — memory said `132,690`, the filing said **`132,729`**. Exactly why we grep. Two thin keys (`7.46`, `15,004,697`) verified distinctive before locking (4 and 2 clean hits, no fragment collisions).
- **Gold set (6 fact-lookups, all keys sourced from the doc):** total net sales `416,161` · cost of sales `132,729` · net income `112,010` · R&D `31,370` · diluted EPS `7.46` · diluted shares `15,004,697`. Stored as a plain Python list in `engine/app/eval/gold_set.py` (tiny set → no JSON/DB warehouse for six apples).

### T2.2 — the baseline reading
- `engine/app/eval/score.py` — **imports the real `retrieve`** (measures the production path, not a copy that could drift) + the gold set. Per question: count how many of the top-5 chunks contain the key → **hit** (any > 0) and **precision** (count ÷ 5), averaged over all six.
- **Baseline, vector-only top-5:** **hit rate 1.00** (6/6 — every answer *is* findable) · **precision 0.30** (the pile is noisy; ~1.5 of 5 chunks relevant on average). The line in the sand. Turn 2's job, now measurable: *drag precision toward 0.85 without dropping hit rate below 1.00.*

### T2.3 — sparse proof (the new tool, proven on one item first)
- **The fork:** BM25 **native in Qdrant** (the exact reason Fork A chose Qdrant — "first-class hybrid search") vs a throwaway in-memory Python BM25. Chose native — not using the thing you picked Qdrant for is an interview liability.
- **Live API check first** (standing rule — verify before pinning): confirmed the current, non-deprecated path — Qdrant **Query API** (server-side RRF, in since 1.10; we're on 1.12.1) + **FastEmbed** `Qdrant/bm25` for the sparse vectors. No separate BM25 library needed.
- Added `qdrant-client[fastembed]`. **Build timed out first** on the onnxruntime wheel (`files.pythonhosted.org` read-timeout) — a network hiccup, not a code bug; fixed with a retry + `--timeout 120 --retries 5`.
- **Proved one sparse vector in isolation** (the PyMuPDF-page-1 move): 6 non-zero terms for "Apple total net sales were 416,161 million" — the content words survived (`apple, total, net, sales, 416,161, million`), the filler ("were") dropped, and **`416,161` was a lit-up slot** — the exact number vector search fuzzes over is first-class in sparse. Weights were identical (`1.665`) — correct for a lone sentence (no corpus yet for IDF; real weights emerge after the full re-ingest).

### T2.4 — the re-ingest
- Rewrote `ingest.py`: added `embed_chunks_sparse()` (BM25 over all chunks), and rebuilt the collection with **named** `dense` (VectorParams) + `sparse` (SparseVectorParams, `Modifier.IDF`) configs; each point now carries `vector={"dense":…, "sparse":…}`.
- **Honest heads-up given before running:** the moment the collection switches to named vectors, the *old* `search()` breaks → `/ask` breaks — expected mid-surgery, restored in T2.5.
- Re-ingest ran clean; verified: **284 points**, `dense: ['dense']`, `sparse: ['sparse']`.

### T2.5 — hybrid search
- Rewrote `retrieve.py`: `search(question)` embeds dense + sparse, **prefetches top-20 from each**, fuses with `FusionQuery(fusion=Fusion.RRF)`, returns top-5. **Prefetch depth 20 → keep 5** so fusion has a real pool to reconcile (a chunk ranked #12 on dense but #2 on sparse can still surface). Same bge-small on both sides (the "same ruler" rule). Contract preserved: still `list[str]`.
- Proved in isolation: five real Apple financial chunks (disaggregated net-sales table, R&D block) for the net-sales question. Hybrid works.

### T2.6 — re-measure (the mixed result, read honestly)
- **Hybrid RRF top-5:** **precision 0.30 → 0.43** (↑ ~43%, BM25 earned its keep) **BUT hit rate 1.00 → 0.83** (↓ — one answer *lost*).
- **The regression matters more than the improvement.** Per-question: net sales 3/5, cost of sales 1/5, net income 3/5, **R&D 0/5 (MISS — was a HIT at baseline)**, EPS 3/5, shares 3/5. Fusion helped five, sacrificed one.
- **Diagnosed, not hidden.** A top-20 probe found the R&D chunk (`31,370`) alive at **rank 7** — retrieval didn't lose it, RRF *buried* it (the answer is keyword-poor, so BM25 ranked it low and fusion averaged it below the top-5 cutoff — known, explainable RRF behavior). **That names the fix precisely: the cross-encoder reranker**, whose whole job is re-sorting candidates we already have. We *empirically justified* the next tool instead of taking it on the blueprint's word.

### T2.C — close clean
- **4 atomic Conventional Commits** (eval harness / fastembed dep / re-ingest / hybrid search); `.gitignore` (the scratch-file ignore) amended into the eval commit where it belongs (Manglam caught it dangling). Pushed, `main...origin/main` clean — two-places rule satisfied.
- **Journal:** the R&D regression (problem: hybrid dropped a found answer → diagnosis: rank-7 probe → fix: reranker) is textbook `JOURNAL.md` material. Left to Manglam's choice, as before.

---

## ✅ Decisions Locked This Session

- **Interim eval = 6-Q string-anchored gold set over the Apple 10-K**, numbers grepped from the doc. Bridge ruler until FinQA at Turn 5.
- **Relevance = exact-string containment**; **ground truth = grepped from the document** (non-circular).
- **Gold set keys on FY2025 (leftmost) values** — avoids the comparative-statement prior-year collision.
- **BM25 = native in Qdrant** (over throwaway in-memory), via **FastEmbed `Qdrant/bm25`** + **Query API server-side RRF**.
- **Collection re-ingested with named `dense` + `sparse` vectors**, sparse config `Modifier.IDF` on.
- **Hybrid retrieval = dense + sparse prefetch (depth 20) → RRF → top-5**, `retrieve(question) -> list[str]` contract preserved.
- **Scorer imports the real `retrieve`** — measures the production path, not a copy.
- **`pip → uv` migration = first step next session** (deferred once more, deliberately).
- **Reranker justified empirically** — R&D answer buried at rank 7 is the concrete reason, not blueprint faith.

---

## 🧠 Hard-Won Lessons

- **Build the measuring stick before the improvement.** We took a baseline (0.30) *before* adding BM25, so hybrid had to prove itself against a number — and it revealed a regression we'd otherwise have shipped blind. Can't improve what you can't measure; can't catch a regression you never baselined.
- **Grep the document, never trust memory for ground truth.** Cost of sales: memory `132,690`, filing `132,729`. A gold set built from memory would silently mis-score. Read the source, not the recollection — and not the retriever (that's circular).
- **The comparative-statement three-year trap.** 10-Ks lay out current + two prior years per line. Key on the wrong number and a *prior-year* chunk scores as relevant. Anchor on the current-year (leftmost) value.
- **Use the same extractor for ground truth as for chunks.** Reusing `ingest.py`'s `extract_text()` (not a fresh re-implementation) guarantees grepped keys match what got indexed — no drift at page boundaries.
- **Read a mixed result honestly — the regression outweighs the headline.** Precision 0.30→0.43 is real, but hit rate 1.00→0.83 means we got *worse* at the thing that matters most (finding the answer). A careless build celebrates the precision jump and ships a worse system.
- **Diagnose before fixing.** The rank-7 probe distinguished "chunk lost" (fix retrieval) from "chunk buried" (fix ranking). `FOUND at rank 7` → it's a ranking problem → the reranker, precisely. Guessing the fix without the probe would've risked touching the wrong layer.
- **RRF rewards both-list agreement and sacrifices single-signal edge cases.** A keyword-poor answer that only the dense side loves can get averaged out of the top-5. Expected fusion behavior — and exactly what a reranker (which reads query+chunk together) is built to rescue.
- **Slow build = healthy for heavy deps; network timeouts on big wheels are transient.** onnxruntime is large; a read-timeout is the connection, not the code. Retry + `--timeout 120 --retries 5` is the standard, legitimate fix.
- **IDF is computed server-side across the whole corpus.** A single sentence shows flat (identical) BM25 weights because there's no document collection to compare against; real weighting only appears once all 284 chunks are embedded and Qdrant runs IDF.

### ⚠️ Process errors this session — Claude's (logged honestly)
- **Pointed a write at the read-only corpus mount** (`/code/data/corpus/aapl_extracted.txt`) → `OSError Errno 30`. The `:ro` mount was a *deliberate* Session-04 decision (a filing is evidence, code must not corrupt it) — and I told Manglam to write straight into it. Root fix: **when handing a write command, target a writable path by default; never write into a mount we deliberately locked read-only.**
- **Forgot the `.gitignore` change in the commit sequence.** Handed four commits, missed the staged ignore-line from T2.1; Manglam caught the dangling `M .gitignore`. Root fix: **before handing a commit sequence, account for *every* file the session touched — including config/ignore/scratch files — not just the obvious code.** (Same family as the Session-03 sequencing miss; keep watching.)

---

## ⏭️ Next Session — Turn 2 back half: the reranker (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (four Up) → `git status -sb`. |
| 1    | **`pip → uv` migration FIRST** — migrate engine (+ shell) Dockerfiles to `uv` before adding the reranker dep. The queued housekeeping, in its own clean window. |
| 2    | **Cross-encoder reranker** — add it, re-score the top-20 hybrid candidates so the truly-relevant rise. **Target: rescue the R&D answer from rank 7 into the top-5.** |
| 3    | **Re-measure** — run the scorer. Success = **precision up toward §02 ≥ 0.85 AND hit rate back to 1.00**. A precision gain that leaves hit rate < 1.00 is not a win. |
| 4    | **Page-number provenance** — start the chunk-id → page-N citation work (the S04 debt: `\n`-join drops page provenance). |
| 5    | **(Optional) GPU passthrough** — a cross-encoder is a real neural net; if it's slow on CPU, wire NVIDIA Container Toolkit and **watch the 4060 light up in Task Manager** (likely the first real GPU moment). |

**Decided at the step, not now:** exact reranker model, how many candidates to rerank (top-20 vs more), and whether GPU is justified — chosen inside the step when the load is measurable.

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
