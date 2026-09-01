# 🧭 Attest — Session 01: Project Chosen, Named, Blueprint Frozen

> **📚 Format note (read once).** This is the FIRST log of a new project. Logs are a **stack** —
> one `.md` file per session, never one growing monolith. Each file carries a **Status Board** (so
> the latest file alone re-anchors everything) and a **⚠️ Supersedes** section (so no older file can
> quietly contradict a newer one).
>
> **Cold-start reading order every session:** 📄 `Attest_Blueprint_v1.pdf` → 🗒️ the **latest**
> session log → 📋 Instructions. Older logs are searched only for a specific detail — never read
> front-to-back.

---

## 🚦 Status Board

|                       |                                                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Current phase**     | 🧭 **Planning COMPLETE — blueprint frozen.** 0 of 7 spiral turns built.                                            |
| **Last session**      | [01] — picked the project, named it **Attest**, scoped it end-to-end, froze the blueprint PDF.                     |
| **What exists**       | The **plan only**. No repo, no code, no corpus yet.                                                                |
| **The build**         | **Turn 1 — the walking skeleton** (upload → ask → cited answer, text-only, no auth) is the next thing to build.    |
| **Success criteria**  | **§02 FROZEN (proposed):** faithfulness ≥ 0.90 · retrieval precision ≥ 0.85 · answer relevance ≥ 0.85 · hallucination < 0.50 → auto-flag · figure-grounded ≥ 80% · p95 ≤ 8s. ⚠️ **Not yet challenged by me.** |
| **Stack**             | Django (shell) + FastAPI (engine) + **Qdrant** (vectors) + PostgreSQL. LangChain/LangGraph · RAGAS · PyMuPDF · Docker. |
| **Domain / corpus**   | **Financial.** Live set = SEC EDGAR + annualreports.com (self-scraped). Labeled set = FinQA / TAT-QA / ConvFinQA. **None collected yet.** |
| **Environment**       | **Linux from day 0** (the NewsVane lesson). Not set up yet.                                                        |
| **Repo**              | Not created yet.                                                                                                   |
| **Blueprint**         | `Attest_Blueprint_v1.pdf` — Frozen v1, lives in the project.                                                       |
| **Next action**       | Either **(a)** challenge / lock the §02 numbers, or **(b)** set up the ground and start Turn 1.                    |
| **Open question**     | Are the §02 targets right, or do they get renegotiated? And US-EDGAR vs Indian filings for the live corpus?        |

---

## ⚠️ Supersedes

**None — this is the origin session.** Nothing older exists to override.

---

## 🎯 Session goal

**Decide WHAT to build, and freeze a plan I can defend at interview — before writing a single line.**
The "3 hours of planning" rule, taken seriously: this whole session was planning.

| Bucket | One line                                                                    | Status |
| ------ | --------------------------------------------------------------------------- | ------ |
| **P0** | Read the ground — my skills, my gaps, what companies actually want to see.   | ✅     |
| **P1** | Choose the project — major, multipage, fills my gaps, spiral-buildable.      | ✅ Attest |
| **P2** | Lock the domain, the name, and the core loop.                               | ✅     |
| **P3** | Settle architecture, tech stack, and the two open forks.                    | ✅     |
| **P4** | Map the pages, the 7 spiral turns, and the HR-question capture.             | ✅     |
| **P5** | Freeze the §02 success criteria.                                            | ✅ (proposed) |
| **P6** | Produce the frozen blueprint as a PDF with visuals.                         | ✅     |
| **P7** | Establish how we work — instructions, session logs, build journal.          | ✅     |

---

## 📓 What happened

### P0 — the ground

My completed stack was inventoried against my portfolio. Verdict: I'm strong end-to-end at
**data → ML/DL → serve it live** (NewsVane, Spectra, AirCast, Taska), and the **two real gaps** are
**Agentic AI** and **RAG + vector DBs** — my two stated GenAI learning goals, with zero flagship
evidence.

Then Claude searched what companies want in 2026 projects. The signals converged hard:

- **RAG is the dominant hireable pattern** (LangChain + RAG + PyTorch top the AI-engineer skill lists).
- **An evaluation harness is now a first-class hiring artifact**, not a bonus — RAG eval / monitoring is a concrete hiring need.
- **Multimodal is the frontier; text-only is aging out** (multimodal-RAG / vision-language roles pay the most).
- **Full-stack + auth + deployment is a real signal** (~78% of orgs prioritise full-stack).
- ⚠️ **The LLM-wrapper trap:** a UI on an LLM API isn't a product — defensibility comes from proprietary/self-collected data and vertical depth.

### P1–P2 — the project, the leap, the name

- Rejected **extending NewsVane** — I'm done with "visit-and-gone" single-page projects and wanted a fresh, breadth-proving flagship.
- Landed on a **multimodal, agentic, self-grading RAG system**: it fills both gaps at once, and the **self-grading eval layer** is my NewsVane measurement-honesty DNA reborn for LLMs.
- **The CV question, answered honestly:** computer vision earns its place ONLY because the domain is chart-dense. That locked the **domain = financial** (10-Ks, annual reports) — so the multimodal layer is *load-bearing*, not decoration.
- **Name journey:** ranged too wide at first (Greek myth, then Hindi/Sanskrit myth) before landing on a genuine product name — **Attest**: "to bear witness / vouch for." It carries both differentiators — it *attests* to what's in the docs (sees the charts) and only *vouches* for answers it can ground (self-grading).

### P3 — architecture + the two forks

- **Two clean halves:** Django = product shell (auth, roles, pages); FastAPI = the RAG/agent engine. Postgres = users/metadata/scores/history; Qdrant = vector embeddings of text + figure descriptions.
- **Frontend = Django**, chosen over React/JS (haven't touched JS in a while; staying in Python) and over Streamlit (which can't do real multi-user auth / true multipage / data isolation cleanly).
- **Fork A — Vector store: Qdrant over pgvector.** Resume-visible, purpose-built, first-class hybrid search + reranking, clean separation from Postgres. Costs one extra container — Docker handles it.
- **Fork B — Multimodal: image-to-text figure description over pure CLIP embeddings.** A vision-LLM describes each figure into rich text, embedded alongside the doc text — cheap, integrates with the text-RAG pipeline, and human-inspectable so it's easy to eval. CLIP-style embeddings parked as future work.

### P4 — pages, spiral, HR capture

- **Pages:** Public (Landing · Login · Signup) · User (Dashboard · Upload/Library · Chat · Answer viewer · Trust dashboard · History · Account) · Admin (Ingestion monitor · Observability). User-vs-admin split = real multi-tenant isolation, not cosmetic.
- **Spiral = 7 turns**, ~50–64h total, read bottom-up: 1 Skeleton → 2 Retrieval quality → 3 Multimodal → 4 Agentic → 5 Trust+eval → 6 Product shell → 7 Ship it. Turn 1 is alive end-to-end; every later turn is a layer across the whole app.
- **All 25 HR questions mapped** to the turn that locks them; team questions (Q8–10) answered in one word — solo.

### P5–P6 — freeze + blueprint

- **§02 success criteria frozen** (proposed numbers — see Status Board). The point: they're set *before* building, so Q3 is honestly answerable.
- **`Attest_Blueprint_v1.pdf` generated** — 10 sections, 5 embedded visuals (architecture, 3 page mockups, spiral map), both forks settled with reasoning.

### P7 — how we work

Established the working method: this stacked **session-log** format, a repo-side **build journal**
(`JOURNAL.md`) for Q13/14/15, the **Instructions** constitution, the **copy-paste rule** (copyable
content always in a copy-button block; long files downloaded instead), **`[NN]:` session naming**,
and the **three end-of-session deliverables** (name · log-file · instruction-delta).

---

## ✅ Decisions Locked This Session

- **Project = Attest** — a new, multipage, multimodal agentic self-grading RAG app. NOT an extension of NewsVane.
- **Domain = financial** — chosen for chart richness, so computer vision / multimodal is load-bearing.
- **Core loop** — ask → retrieve text + figures (hybrid + rerank) → cited answer → self-grade faithfulness → flag ungrounded answers.
- **Architecture** — Django shell ↔ FastAPI engine ↔ PostgreSQL + Qdrant.
- **Frontend = Django** (over React/JS and over Streamlit).
- **Fork A = Qdrant** (over pgvector). **Fork B = image-to-text figure description** (over CLIP embeddings).
- **Spiral = 7 turns**, thin living skeleton first, one capability layer per turn.
- **§02 numbers frozen** as the contract (proposed; may be renegotiated next session with a defensible reason, recorded in Supersedes).
- **Corpus** — self-scraped live set (SEC EDGAR + annual reports) + FinQA/TAT-QA/ConvFinQA as the labeled eval set.
- **Working method** — stacked session logs, repo build journal, Instructions constitution, copy-paste rule, three end-of-session deliverables.

---

## 🧠 Hard-Won Lessons

- **A tool earns its place only if the problem needs it.** Computer vision is in Attest ONLY because financial documents are chart-dense. Bolting CV on to flex the skill would have been the "reach for the shell out of habit" mistake — the load-bearing test is what kept the design honest.
- **A RAG project lives or dies on its corpus.** Decide the data source *before* the model — garbage documents, garbage system. Financial wins because the data is free (EDGAR), public, and chart-rich.
- **Plan the defensibility, not just the demo.** The eval harness + self-collected data are what separate Attest from the "LLM-wrapper trap." The login page is a multiplier on real AI depth, never a substitute for it.

### ⚠️ Process error this session — Claude's

- **The naming detour.** Asked for genuine product names, Claude first served Greek mythology, then pivoted to Hindi/Sanskrit mythology — "mythology to mythology" — before finally offering real, brandable product-word candidates. Manglam redirected twice. **Lesson: for a naming task, lead with brandable real-word candidates; keep mythology only if explicitly asked.** Logged here as a lesson; too narrow to promote to a permanent Instruction standing rule.

---

## ⏭️ Next Session — set the ground, then make it walk

| Step | One line                                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------- |
| 1    | **Decide the §02 numbers honestly** — accept or renegotiate faithfulness ≥ 0.90 etc. Record any change in Supersedes. |
| 2    | **Pick the live-corpus source concretely** — US EDGAR (standardised, easy) vs Indian filings (more relatable in interviews here). |
| 3    | **Set up the ground** — Linux, a fresh repo, Python env, a minimal Docker skeleton (Django + FastAPI + Postgres + Qdrant containers).  |
| 4    | **Build Turn 1 — the walking skeleton:** one financial PDF → chunk → embed → ask → retrieve → **cited answer**. Text only. No auth, no multimodal yet. **Alive end-to-end.** |
| 5    | **Open `JOURNAL.md`** and log the first real problem + concrete fix as it happens.                                   |

**Parked (decide at the turn that needs it, not now):** the exact vision-LLM (e.g. Gemini) and
embedding model (e.g. BGE) get chosen at the multimodal turn, not up front.
