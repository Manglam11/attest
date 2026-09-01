# 🧭 Attest — Session 14: Judge Persistence Fixed — Migration to Claude Code

> **📚 Format note.** Logs are a **stack** — one `.md` per session. Each carries a **Status Board**
> (latest file alone re-anchors everything) and a **⚠️ Supersedes** section (no older file can
> quietly contradict a newer one).
>
> **Cold-start reading order:** 📄 `docs/blueprint.pdf` → 🗒️ the **latest** session log →
> 📋 `CLAUDE.md` (execution) + project instructions (conversation).

---

## 🚦 Status Board

|                       |                                                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Current phase**     | **Turn 5 (trust + eval) STILL OPEN.** The judge now persists its work — it did not before. §02 numbers stand at **4 of 12** answerable rows. The remaining rows are blocked on an **unidentified quota wall**, not on pacing. |
| **Last session**      | [14] — discovered `judge.py` had no write at all, restored per-row persistence, fixed a `.gitignore` that blocked every exception beneath it, and moved the blueprint + 13 logs + a new `CLAUDE.md` into the repo for the Claude Code handoff. |
| **What exists**       | Everything from S13 **plus**: **(1)** `judge.py` with `summarise()` + `write_judged()` restored and firing **after every row**, untruncated error output, and `--limit` counting newly-spent rows; **(2)** a corrected `.gitignore` — `data/*` not `data/`, so `judged_*.json` is trackable and a welded corpus rule is unwelded; **(3)** `docs/blueprint.pdf` + `docs/sessions/` (13 logs) **in the repo**; **(4)** `CLAUDE.md` — the execution constitution. **Still no p95, no auth, no complete §02 table.** |
| **Environment**       | Windows host → WSL2 Ubuntu (on `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration) + VS Code Remote-WSL. **Execution moves to Claude Code from here.** |
| **Machine**           | Agastya111 — AMD Ryzen 7 7435HS · 16 GB RAM · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM). GPU still unused. |
| **Storage**           | Everything on E: (external SSD). E: must be connected before WSL/Docker start.                                     |
| **Repo**              | `~/02_dev/01_attest` — branch `main`, all pushed. This session: **6 atomic Conventional Commits** (ignore-fix / judge-persist / judged-results / corpus-gitkeep / docs / CLAUDE.md). |
| **The build**         | **Turn 5.** Remaining: identify the quota wall → finish rows 4–11 → complete the §02 table → investigate row 3's `cp=0.58` → p95 → `generate.py`'s fate. All of it in Claude Code. |
| **Success criteria**  | §02 FROZEN & DEFENDED (unchanged). **Partial, n=4:** faithfulness **1.000** · answer relevancy **0.988** · context precision **0.883** · refusal rate 3/3. ⚠️ **Not claimable** until all 12 answerable rows are judged. |
| **Stack**             | Django + FastAPI + Qdrant + PostgreSQL + isolated eval image (ragas 0.4.3, `jsonref`). No new deps this session. |
| **Domain / corpus**   | Financial. Apple 10-K FY2025, 285 records. Gold set = 15 pairs, all keys column-verified (S13). |
| **Next action**       | **Fresh Claude Code window.** Identify the row-5 quota metric from the full error, then finish the judge run. |
| **Open question**     | **What quota did row 5 actually hit?** `429 aiplatform.googleapis.com/gl…` — a **Vertex AI** metric, not the Generative Language 15 RPM ceiling the pacing was designed around. Never read in full because our own print clipped it at 120 chars. |

---

## ⚠️ Supersedes

- **`judge.py` never wrote anything. The S13 claim that it has "resume from disk" was HALF true.** It *reads* a prior `judged_*.json` to resume — but the file contained no `json.dump`, no summary computation, and no write call anywhere. The Aug-31 judged file exists only because S13's pre-fail-fast run fell out of the loop normally under a code version that has since been lost. **Every metered run since has scored rows and discarded them**, including two rows (~390s of quota) burned this session before the gap was found. Restored: `summarise()`, `write_judged()`, and a write after **every** row.

- **The `.gitignore` `data/` rule made every exception beneath it dead text.** A trailing slash stops git descending into the directory at all, so `!data/eval/` and `!data/eval/*.json` — both present since S13 — never did anything. Replaced with the four-step `data/*` → `!data/eval/` → `data/eval/*` → `!data/eval/judged_*.json` pattern. **This answers S13's open question: `judged_*.json` was not tracked, and there was no exception covering it.**

- **A welded ignore rule was silently breaking two things at once.** `!data/corpus/.gitkeepaapl_extracted.txt` — a missing newline had fused two rules, so `.gitkeep` was not re-admitted *and* `aapl_extracted.txt` was not ignored. Both split and fixed.

- **The row-5 wall is NOT the 15 RPM ceiling.** Rows 3 and 4 took ~195s each at `JUDGE_PACE_S=60`; no 60-second window came close to 15 calls. The error names `aiplatform.googleapis.com` — Vertex AI — while the free-tier RPM figure describes the Generative Language API. **Leading suspect: `gemini-embedding-001`**, used by `answer_relevancy` and `context_precision`, on a quota pool we have never counted. Untested — the full metric name has never been read.

- **`docs/` is now in the repo.** Blueprint and all 13 session logs live at `docs/blueprint.pdf` and `docs/sessions/`. The cold-start reading order now points at repo paths, not chat attachments.

- **The working model changes from this session forward.** Three tiers: chat = architecture and turn design (intent, constraints, acceptance criteria); Claude Code = execution (reads the repo, decides the how, runs it); Manglam = the gate on anything metered or destructive. **Chat stops issuing literal file paths and exact commands** — that was the root cause of this session's error rate.

---

## 🎯 Session goal

**Planned:** close Turn 5 — finish the judge, complete the §02 table, measure p95.
**Actual:** found the judge had been throwing its results away, fixed it, and made the repo self-describing for the handoff. Turn 5 stays open, honestly.

| Bucket | One line                                                                          | Status |
| ------ | --------------------------------------------------------------------------------- | ------ |
| **T5.0** | Resume gate — containers Up, tree clean, `JUDGE_API_KEY` proven in the eval container. | ✅ |
| **T5.7b**| Finish the judge — rows 3–11.                                                    | ❌ **1 row scored, then a quota wall** |
| **T5.11**| `.gitignore` — make `judged_*.json` trackable.                                   | ✅ found it was never trackable |
| **T5.7d**| Restore judge persistence (unplanned — the session's real find).                 | ✅ proven: mtime moved, 4 rows on disk |
| **T5.10**| Read the completed §02 table.                                                    | ❌ carried — 4 of 12 |
| **T5.9** | p95 latency.                                                                     | ❌ carried — untouched |
| **T5.12**| `generate.py`'s fate.                                                            | ❌ carried |
| **T5.M** | Migration — `CLAUDE.md`, `docs/`, the three-tier working model.                  | ✅ |
| **T5.C** | Close clean — 6 commits, log, instruction delta.                                 | ✅ |

---

## 📓 What happened

### T5.0 — the gate held
Four containers Up, `main...origin/main` clean, `JUDGE_API_KEY` confirmed live **inside** the eval container — the S13 rule, applied and passing this time.

### T5.7b — one row, then the wall
`JUDGE_PACE_S=60` (overridden from the file's untested 45, on the arithmetic that a metric's ~10-call burst at 45s spacing puts ~20 calls in a rolling minute). Rows 3 and 4 scored at ~195s each. Row 5 died on `429 RESOURCE_EXHAUSTED`.

Then the finding that reframed the session: **the two scored rows were not on disk.** The `judged_*.json` mtime never moved. The script had printed `wrote /code/data/eval/judged_...json` and written nothing.

### T5.7d — the hunt, and three of my own wrong turns
The diagnosis took four rounds, and three of them were my errors:

1. **Wrong path.** Looked for the JSON in `engine/app/eval/`; `EVAL_DIR` is `data/eval/`. Declared the input files missing when they were sitting there.
2. **`--limit 0` as a durability test.** `spent >= limit` is `0 >= 0` on the first iteration, so the loop broke before touching a row. The empty summary proved nothing.
3. **Suspected the mount.** Two probe writes from inside the container landed on the host immediately — the mount was read-write and always had been.

What actually settled it was reading the file to its end: `main()`'s loop is followed directly by `if __name__ == "__main__"`. **No write, anywhere.** The `wrote {path}` line was an unconditional print. A chunk of the function — summary and write — had been lost, most likely in an incomplete paste at S13's close, which that log itself flags as happening on a nearly-full context window with a run in flight.

**Fix:** `summarise()` + `write_judged()` restored, write fires after every row *including error rows*, error print unclipped, `--limit` counts newly-spent rows. **Proven at `--limit 1`:** row 3 scored, mtime moved, 4 rows on disk.

### T5.11 — the ignore rules were lying too
`git check-ignore` showed `.gitignore:19:data/` claiming `judged_20260831T101752Z.json`. S13's `!data/eval/` exceptions had been dead text from the day they were written — git never descends into a slash-terminated ignored directory. The four-step re-admit pattern fixed it, and exposed the welded `.gitkeep` / `aapl_extracted.txt` line as collateral.

### T5.M — the migration
Six rounds of paste-and-guess made the case on their own. `CLAUDE.md` written as the execution constitution (rules that fire while *doing*), project instructions retained as the conversation constitution (rules about *how we talk*) — deliberately split rather than duplicated, since `CLAUDE.md` is read on every invocation and length has a per-call cost.

**Also found during the migration: `JOURNAL.md` does not exist.** Thirteen sessions in, and the artifact the blueprint calls non-optional — the Q13/Q14/Q15 insurance — was never created. Logged as work for Claude Code, which can seed it from `docs/sessions/`.

---

## ✅ Decisions Locked This Session

- **The three-tier model.** Chat gives intent and acceptance criteria, never literal paths or exact commands. Claude Code reads the repo and decides the how. Manglam gates anything metered or destructive.
- **Manglam's monitoring is three checks, not code review:** approve before spend/destroy · `git status -s -uall` + `git log --oneline -3` at every commit · verify acceptance criteria, not implementation.
- **`CLAUDE.md` and the project instructions are split, not duplicated.** Execution rules in the repo; conversational rules in chat.
- **The judge run does not restart in this window.** ~30 minutes of blind metered waiting against an unresolved quota unknown is precisely the wrong task for a context that cannot see the output file.

---

## 🧠 Hard-Won Lessons

- **"Resume from disk" is two capabilities, and we only had one.** The judge could *read* a prior file and skip scored rows — which looks exactly like working resume — while never *writing* one. Reading and writing must be verified separately; a passing resume proves nothing about persistence.
- **A success message is not a write.** `wrote {out_path}` printed on every run, unconditionally, with no `json.dump` behind it anywhere in the file. This is S12's "never trust a status line" firing again, one layer deeper: not a tool's status line this time, but **our own**.
- **A trailing slash in `.gitignore` kills every exception beneath it.** `data/` and `data/*` look equivalent and are not. Two sessions of `!data/eval/` rules did nothing.
- **Read the file to its end before theorising about its behaviour.** Four rounds of mount checks, path guesses and flag experiments; the answer was visible the moment the last 20 lines were on screen.
- **Test the cheapest thing that can actually fail.** `--limit 0` skipped the loop entirely and tested nothing. A durability test must let at least one write happen.
- **Losing the same work twice is a process failure, not bad luck.** S13 burned nine rows to a missing fail-fast. S14 burned two to a missing write. Both were "the harness already had this" problems — `harness.py` had persistence all along.

### ⚠️ Process notes this session — Claude's (logged honestly)
- **Three wrong diagnoses stated with confidence before testing** — wrong directory, mount suspicion, and a `--limit 0` test that couldn't work. The S12 label-your-hypothesis rule was followed in wording (each was called a "suspect") but the *cheapest* test was not always the one chosen.
- **Wrote a test whose exit code I'd misread.** Told Manglam `git check-ignore ... || echo TRACKABLE` would print on success; it exits 0 on any pattern match, negation included, so the check couldn't say what I claimed.
- **Asked for a `git status` as though the commits hadn't run**, when Manglam had already run them and pasted the output. Not reading the terminal carefully enough.
- **Root cause, named honestly:** all of it comes from writing commands and code for a repo I cannot see. That is the argument for the migration, and it came from the failures rather than from planning.

---

## 🧾 Carried technical debt

- **Judge rows 4–11 unscored** — blocked on the unidentified quota wall.
- **Judge write-merge bug** — each run rewrites the judged file with only the rows *that run* touched, so a later partial pass can drop rows scored in an earlier one. Seed `judged` from the prior file's rows. **Not yet fixed.**
- **Row 3 context precision `0.58`** — first individual row under target. Uninvestigated; contexts are on disk, costs nothing.
- **`JOURNAL.md` missing entirely** — blueprint-mandated. Seed from `docs/sessions/`.
- **p95 unmeasured** — ~10 `/ask` calls against a 20 RPD ceiling; budget it deliberately.
- **`generate.py` orphaned** from `/ask` — delete or keep as documented fallback.
- *(Carried unchanged: `langchain-community==0.3.31` pin · `llm_factory` bypass · Qdrant `:latest` pin → Turn 7 · `.env.example` trailing newline · page number = PDF order, not printed footer.)*
- **RESOLVED this session:** judge persistence · the `.gitignore` `data/` trap · the welded corpus rule · S13's open question about `judged_*.json` tracking.

---

## ⏭️ Next Session — first Claude Code window

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Resume ritual** — plug E: → Docker → `up -d` → `ps` → `git status -sb`. Claude Code reads `CLAUDE.md` + the newest log. |
| 1    | **Identify the quota wall** — re-run the judge and read the **full** 429 (the clip is gone). Name the metric before changing pacing. |
| 2    | **Fix the write-merge bug** *before* the long run, so a partial pass can't drop earlier rows.                 |
| 3    | **Finish rows 4–11** → complete the §02 table → commit `judged_*.json`.                                       |
| 4    | **Open row 3's `cp=0.58`** — free, contexts on disk. Ruler or product?                                        |
| 5    | **Seed `JOURNAL.md`** from the session logs — Q13/Q14/Q15 insurance.                                          |
| 6    | **p95**, then **`generate.py`'s fate** → Turn 5 closes.                                                       |

**Reminder:** plug E: in before Docker. If Docker won't start, first suspect = drive not mounted.

**Handoff note:** this log is written for a reader with repo access and no memory of the conversation. Everything Claude Code needs is in `CLAUDE.md` and `docs/`.
