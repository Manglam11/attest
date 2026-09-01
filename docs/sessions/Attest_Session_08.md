# 🧭 Attest — Session 08: Turn 3 — Multimodal Lands, The Chart Gets Read (1 Figure Described, Vision Estimate Matched the Filed Table Within ~1%)

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
| **Current phase**     | 🎉 **Turn 3 COMPLETE — multimodal alive. The system reads charts, not just text.** 3 of 7 spiral turns fully alive. **Turn 4 (agentic) is next.** |
| **Last session**      | [08] — extracted the one real figure from the Apple 10-K, described it via Gemini vision, embedded it alongside text in the hybrid collection, and answered a chart-grounded question with the figure cited. |
| **What exists**       | Everything from S07 **plus a live multimodal ingest path**: `ingest.py` now extracts PDF images, filters logo-junk by size (<200px skipped), describes each real figure via `gemini-3.6-flash` vision, and embeds the description into the **same** dense+sparse `attest_chunks` collection tagged `kind: "figure"`. Collection is now **285 records** (284 text + 1 figure). A live `/ask` on a 5-year-return question retrieved the figure at rank 1 and answered from it. **No auth, no agentic layer, no eval-on-benchmark yet.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 1 TB SSD. **GPU STILL unused — and now knowingly so for vision** (see Supersedes: Gemini vision runs on Google's servers, not local). |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed (`main...origin/main` clean). 2 atomic Conventional Commits this session (figures-volume-mount / figure-ingest-feature). |
| **The build**         | **Turn 4 — agentic**: a LangGraph agent routes a multi-step question (retrieve / compare / summarise) with no hardcoding. First orchestration layer over the now-multimodal retrieval. |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination flag < 0.50 · **figure-grounded ≥ 80% (aspirational)** · p95 ≤ 8s. The figure-grounded criterion got its **first real evidence** this session (one figure, read accurately). |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL. **New this session:** the `google-genai` vision path (already-installed SDK, **no new dep**) used for figure description. Generator + vision = `gemini-3.6-flash` (one API, reused exactly as the S04 plan promised). |
| **Domain / corpus**   | Financial. Live set = US EDGAR (primary). Doc = Apple 10-K FY2025 (`aapl_10k.pdf`, **285 records: 284 text + 1 figure**, dense+sparse, `{text, page, kind}` payload). Labeled set = FinQA / TAT-QA / ConvFinQA (not pulled yet). |
| **Next action**       | **Turn 4 — agentic, fresh chat.** Resume ritual → introduce LangGraph → route a multi-step question across the existing retrieve/generate tools with no hardcoded branching. |
| **Open question**     | **None parked at project level.** Turn-4 decisions (agent framework specifics, how tools are exposed, what multi-step question proves it) get decided at the step that needs them. |

---

## ⚠️ Supersedes

- **Ingest is now MULTIMODAL — was text-only.** `ingest.py` gained `extract_and_describe_figures()`: it walks every page, pulls raster images (`page.get_images`), **skips anything under 200px on either side** (the logo filter — Apple logo is 46×56, the real chart is 1360×900), renders each surviving image to PNG bytes, sends it to `gemini-3.6-flash` with a "describe this financial figure precisely" prompt, and returns records shaped `{text: "Figure on page N: <description>", page, kind: "figure"}`. These records are **concatenated onto the text records** before a single embed+store pass — figures ride the exact same dense+sparse pipeline, no parallel path.

- **Payload schema CHANGED — was `{text, page}`; now `{text, page, kind}`.** `kind` is `"text"` or `"figure"`. Reason: a source card must be able to say "read from a chart on page 24", and Turn 5 eval must be able to treat figure-grounded answers separately (the §02 figure-grounded ≥ 80% criterion needs to *find* the figure answers). `chunk_pages` tags every text record `kind: "text"`; `store_vectors` writes `kind` into the payload. Any future consumer reading payloads should expect the third key.

- **Figure text is PREFIXED — `"Figure on page N: " + description`.** Deliberate (Claude's call, Manglam accepted): the words "figure"/"chart" become searchable so a question like "what does the chart show" can hit the description, and the page is baked into the text as a fallback. Small controlled injection, real retrieval gain.

- **GPU passthrough DROPPED for Turn 3 — was "likely the first real GPU moment."** The prior-session prediction was wrong in a *useful* way: the vision model is **Gemini, which runs on Google's servers**, so describing a chart put **zero** load on the local 4060. The GPU worry only ever applied to *local* heavy models (a local embedder/reranker/vision model). Since Attest deliberately ships an API-LLM (the S04 deployment-cost decision), the local GPU may never be load-bearing at all. **NVIDIA Container Toolkit remains unwired**; revisit only if a local model is ever added (e.g. the §10 Ollama flex).

- **Figure count is small BY THE NATURE OF THE DOC — a 10-K is a text-heavy legal filing, not a glossy annual report.** The Apple 10-K contains exactly **two** raster images: the logo (junk) and **one** real chart (the Item 5 five-year stock-performance graph, page 24). The blueprint mockups' "41 figures" is the aspirational annual-report case. One real figure is **enough to prove the capability end-to-end**; a chart-dense annual report is a §10 corpus-expansion item, not a Turn-3 blocker.

---

## 🎯 Session goal

**Turn 3 — teach Attest to read the charts inside a document, not just the text (Fork B: image-to-text figure description).** Prove one real chart gets extracted, described by the vision model, embedded alongside text, and answered from — end to end.

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T3.0** | Resume gate — E: mounted, four containers Up, tree clean, last commit safe.       | ✅     |
| **T3.1** | Extract figures — inventory the PDF's images, decide the figure-vs-junk rule.     | ✅ 2 images: 1 logo, 1 chart |
| **T3.2** | Describe each figure — prove Gemini vision reads the chart in isolation.           | ✅ read title, axes, all 3 indices, endpoints |
| **T3.3** | Embed alongside text — figure description into the same dense+sparse pipeline, tagged. | ✅ 285 records (1 figure) |
| **T3.4** | Chart-only question — prove a chart-grounded question is answered with the figure cited. | ✅ figure ranked #1, answered from it |
| **T3.5** | GPU passthrough — wire NVIDIA toolkit if vision crawls on CPU.                     | ⏭️ DROPPED (Gemini = cloud, no local load) |
| **T3.C** | Close clean — atomic commits + push, session log, instruction delta.              | ✅     |

---

## 📓 What happened

### T3.0 — the gate
- Standard resume ritual: four containers `Up`, Postgres `healthy`, `main...origin/main` clean. Green before code. (One container had been restarted after a full day's gap — clean, expected.)

### T3.1 — extract figures (inventory first, prove-then-build)
- **The honest reality check up front:** a 10-K is a text-heavy legal filing, so before writing any extraction pipeline we **counted the images that actually exist** rather than assume the blueprint's 41. Probe result: **2 images total** — page 1 (46×56) and page 24 (1360×900).
- **Rendered both to disk and eyeballed:** page 1 = the Apple logo (decorative junk), page 24 = the **"Comparison of 5-Year Cumulative Total Return"** graph (the real chart). Exactly the size split predicted.
- **The figure-vs-junk rule locked = minimum size threshold (200px).** Logo 46×56 fails, chart 1360×900 passes. Simple, defensible, no magic — the pipeline can filter logos automatically forever, not hand-pick page 24.

### T3.2 — describe the figure (the heart of Fork B, proven in isolation)
- Ran `gemini-3.6-flash` on the chart PNG with a precise "describe this financial figure" prompt. It **read the chart, not waved at it**: exact title, base date `9/25/20`, all three plotted series by name (Apple, S&P 500, Dow Jones U.S. Tech), every fiscal-year x-axis date, and endpoint dollar values (Dow Tech ~$285–290, Apple ~$235, S&P ~$215).
- **Fork B validated:** a vision LLM turning a chart into rich, human-inspectable, searchable text — the exact reason Fork B beat CLIP (S01) — works on our real data.

### T3.3 — embed alongside text (fold into the existing pipeline, no parallel path)
- **Read `ingest.py` first** (S05 rule) before writing — confirmed the embed functions (`embed_chunks`, `embed_chunks_sparse`) already take *any* `list[str]`, so a figure description reuses them untouched. Confirmed `store_vectors` **deletes+recreates the collection each run** and uses **positional IDs** → the design consequence: figures must be **concatenated into the same records list**, not stored in a separate call (which would wipe text / collide IDs).
- **The clean design:** one combined records list. `chunk_pages` tags text `kind:"text"`; `extract_and_describe_figures` returns `kind:"figure"` records; `__main__` does `records += extract_and_describe_figures(...)` then the single embed+store pass. Payload gained `kind`.
- **Re-ingest:** hit a `409 Conflict` (collection already existed — a delete/create timing gap or half-run leftover); cleared by dropping the collection manually, then re-ran clean → **`Ingested 285 records (1 figures).`**

### T3.4 — the chart-grounded question (the payoff)
- Live `curl` to `/ask`: *"In the 5-year cumulative total return comparison, how did Apple stock perform versus the S&P 500 Index by the end of the period?"*
- **The figure description was retrieved at RANK 1**, and the answer drew Apple ~$235 vs S&P ~$215 straight from it. The multimodal layer works end-to-end: chart → description → embedded → retrieved → cited answer.
- **The unplanned gift (and the honest caveat):** this particular 10-K prints a **data table right below the graph** (Apple `$234`, S&P `$217`, exact figures) — it came back as source [2]. So (a) this chart isn't *purely* visual, which means it's not a clean "answer lives ONLY in a chart" proof, BUT (b) it let us **verify Gemini's read against filed ground truth: the ~$235/~$215 visual estimate matched the table's $234/$217 within ~1%.** That's a *stronger* interview story than "it read a chart" — the vision estimate is accurate and the system cited both the chart and the table. A truly text-absent chart proof belongs to a glossy annual report at §10 corpus expansion.

### T3.C — close clean
- `git status -s` reconciled (S06 lesson): only `docker-compose.yml` + `ingest.py` modified. Confirmed `data/figures/` is covered by the `data/` gitignore rule (line 19) and no scratch PNGs dangled at the repo root.
- **2 atomic Conventional Commits** — figures volume mount (infra) / figure-ingest feature (code) — pushed, `main...origin/main` clean. Two-places rule satisfied.
- **Journal:** the `409 Conflict` (problem → manual-drop fix) and the vision-vs-table accuracy check (Fork B validated on ground truth) are both `JOURNAL.md` / Q13-14-15 / Q20 material. Left to Manglam's choice, as before.

---

## ✅ Decisions Locked This Session

- **Figure-vs-junk filter = minimum 200px on either dimension.** Logos out, charts in, automatically.
- **Figures fold into the SAME records list + collection** (not a separate store call) — reuses embed+store untouched, avoids ID collision and collection-wipe.
- **Payload schema = `{text, page, kind}`**, `kind ∈ {"text","figure"}`.
- **Figure text prefixed** `"Figure on page N: "` — makes "figure"/"chart" searchable.
- **Vision model = `gemini-3.6-flash`** — the already-integrated generator reused for vision (one API, the S04 promise kept). **No new dependency.**
- **GPU passthrough dropped for this turn** — Gemini vision is cloud-side, zero local load; local GPU may never be load-bearing given the API-LLM ship decision.
- **One real figure is enough to prove the capability** — chart-dense annual reports deferred to §10 corpus expansion.
- **Turn 3 declared COMPLETE.**

---

## 🧠 Hard-Won Lessons

- **Inventory the real data before building the pipeline for the imagined data.** The blueprint imagined 41 figures; the actual 10-K has one real chart. Counting first (2 images → 1 logo + 1 chart) stopped us building an elaborate figure pipeline for a document that has one figure. Prove-then-build applies to *the corpus*, not just the code.

- **A chart with an accompanying data table is a GIFT, not a failure.** It means we can verify the vision model's read against filed ground truth. Gemini's ~$235/~$215 matched the table's $234/$217 within ~1% — Fork B validated on real numbers. (It does mean this isn't a clean "chart-only" proof — noted honestly for §10.)

- **`/code`'s writable layer does NOT survive a container recreate** — reconfirmed hard this session. Figures written to `/code` vanished after a `--force-recreate`. The fix is architectural: figures belong on a **mounted, persistent path** (`./data/figures`), same as the corpus, not the ephemeral image layer. (Extends the S07 scratch-file lesson from "regenerate it" to "give it a real home".)

- **Docker only applies volume changes on container CREATION, never on reuse.** `docker compose up -d engine` that prints `Running 0.0s` **reused** the container and silently ignored the new mount. `--force-recreate` is required for a volume edit to take. Reading `Running 0.0s` vs `Started` is the tell.

- **Reusing generic functions is the payoff of clean interfaces.** `embed_chunks`/`embed_chunks_sparse` took `list[str]`, so figures needed **zero** new embed code — just more strings in the list. Designing the embed step to not care *what* the text is (chunk vs figure description) is why the multimodal layer dropped in cleanly.

- **One API, reused — the S04 bet paid off.** Choosing Gemini partly *because* it's vision-capable (over faster-but-text-only Groq) meant Turn 3's vision needed no new integration, no new key, no new dep — the same `google-genai` client, a different `contents` payload. The architecture decision three turns ago cashed out here.

### ⚠️ Process errors this session — Claude's (logged honestly)
- **Wrote figures to the ephemeral `/code` path first, causing the disappearing-file confusion.** Should have put figures on a persistent mount from the first extraction, not after they vanished twice. Root fix: **when a step produces a file we'll reuse, give it a mounted home immediately — don't write to `/code` and rediscover it's ephemeral.**
- **Chased the mount failure with too many diagnostic commands instead of just reading the file.** When the figures mount wasn't attaching, ran four `docker compose config`/`grep` probes before simply printing the compose block — where the truth was obvious (the mount line was never saved; the classic missing `Ctrl+S`, third project appearance). Manglam flagged the thrash directly ("why is this taking so long?"). Root fix: **when a config change isn't taking, READ THE FILE first, before diagnosing Docker.**
- **Handed piecemeal edits after Manglam had pasted the whole file.** He'd given the full `ingest.py`; I replied with six scattered edits to merge by hand. Manglam flagged it: if he provides the whole file, hand back the whole updated file. → Instruction delta this session.

---

## ⏭️ Next Session — Turn 4, the agentic layer (start completely fresh)

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → start Docker → `docker compose up -d` → `docker compose ps` (four Up) → `git status -sb`. |
| 1    | **Introduce LangGraph** — the orchestration layer. Verify current, non-deprecated API live before pinning (standing rule). |
| 2    | **Expose the existing pieces as tools** — retrieve / compare / summarise, over the now-multimodal collection. |
| 3    | **Route a multi-step question** — the agent picks the tool(s) with **no hardcoded branching** (the whole point of Turn 4). |
| 4    | **Prove it end-to-end** — a question that needs more than one step (e.g. retrieve-then-compare) answered correctly by the agent. |

**Decided at the step, not now:** the exact LangGraph pattern, how tools are registered, and what multi-step question proves the agent — chosen inside Turn 4 when the orchestration is live.

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted (expected, not broken).
