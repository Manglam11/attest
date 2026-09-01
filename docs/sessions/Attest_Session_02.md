# 🧭 Attest — Session 02: Ground Setup — WSL2 on E:, Repo Born, the Great Distro-Move Ordeal

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
| **Current phase**     | 🧭 **Ground setup — environment LIVE, repo born.** 0 of 7 spiral turns built.                                      |
| **Last session**      | [02] — locked the environment, relocated Ubuntu to E:, created the repo, pushed first commit to GitHub.           |
| **What exists**       | A **live Linux dev environment** (WSL2 Ubuntu on E:) + an **initialized git repo** at `~/02_dev/01_attest` with `.gitignore` + `README.md`, pushed to GitHub. **No app code, no containers, no corpus yet.** |
| **Environment**       | **Windows host → WSL2 Ubuntu (relocated to `E:\wsl\Ubuntu`) + Docker Desktop (WSL integration on) + VS Code + Remote-WSL.** Chose VS Code over PyCharm (Community can't reach WSL for free). |
| **Storage**           | **Everything on E: (external SSD)** — Ubuntu distro lives on E:. Traded a little speed for storage peace-of-mind on the internal C: (only 62 GB free). GitHub is the safety net. |
| **Repo**              | `~/02_dev/01_attest` — `git init` done, branch `main`, first commit pushed. Folder convention = `NN_name`. |
| **The build**         | **B3 — the four-container Docker skeleton** (Django + FastAPI + Postgres + Qdrant via one compose file) is the next thing to build. |
| **Success criteria**  | §02 FROZEN (proposed), **still not challenged.** Deferred again to the turn that enforces them. |
| **Stack**             | Django (shell) + FastAPI (engine) + Qdrant (vectors) + PostgreSQL. LangChain/LangGraph · RAGAS · PyMuPDF · Docker. |
| **Domain / corpus**   | Financial. Live set = SEC EDGAR + annualreports.com (self-scraped). Labeled set = FinQA / TAT-QA / ConvFinQA. **None collected yet.** |
| **Next action**       | **B3** — write `docker-compose.yml` with four running containers. Then **B4** — close §02 numbers + US-EDGAR-vs-Indian corpus. |
| **Open question**     | Are the §02 targets right? US EDGAR vs Indian filings? (Both still parked.) Also: PAT auth for GitHub push if it wasn't cleared. |

---

## ⚠️ Supersedes

- **Environment is now concrete (was "Linux from day 0, not set up yet").** It is: **WSL2 Ubuntu, relocated to `E:\wsl\Ubuntu`**, with Docker Desktop WSL-integration and VS Code Remote-WSL.
- **Editor locked = VS Code** (over PyCharm — Community tier can't do WSL remote-interpreter for free).
- **Storage decision = everything on E: (external SSD).** Supersedes any implicit "keep it on the internal drive" assumption. Consequence: **E: must be plugged in before Docker/WSL start.**
- **Project path = `~/02_dev/01_attest`** inside Ubuntu (which is physically on E:) — fast Linux-native side, NOT `/mnt/e/...`.
- **Folder-naming convention = `NN_name`** (zero-padded, lowercase) — extends the `[NN]:` session-naming DNA to directories.

---

## 🎯 Session goal

**Set up the ground** — decide *where* Attest lives, stand it up on real Linux, protect it. Scoped to
B1 (environment) + B2 (repo). B3 (skeleton) and B4 (parked decisions) deliberately pushed to a fresh context.

| Bucket | One line                                                            | Status |
| ------ | ------------------------------------------------------------------ | ------ |
| **B1** | Environment call — machine + toolchain, where the project lives.   | ✅ WSL2/Docker/VS Code |
| **B2** | Ground setup — verify tools, create repo, first protected commit.  | ✅ (repo born, pushed) |
| **B3** | Docker skeleton — four running containers via one compose file.    | ⬜ next session |
| **B4** | Parked calls — §02 numbers + US-EDGAR-vs-Indian corpus.            | ⬜ deferred |

---

## 📓 What happened

### B1 — the environment call
- Machine = **Windows**. Held the rule **Linux from day 0** (Docker containers *are* Linux boxes; developing outside Linux and Dockerizing late is the NewsVane friction).
- Landed the toolchain: **WSL2 Ubuntu + Docker Desktop + VS Code + Remote-WSL.**
- **VS Code over PyCharm** — Manglam's call, correct: PyCharm's WSL remote-interpreter is paywalled (Professional), VS Code's Remote-WSL is free and first-class. (Banks part of **Q5**.)

### B2 — ground setup (mostly a fight)
- **Tools were already present** — WSL2 2.7.3, Ubuntu (v2, default), Docker 29.6.1, Git 2.53. Machine was ~90% ready.
- **Docker didn't reach Ubuntu** at first — fixed by flipping Docker Desktop → Resources → WSL Integration → Ubuntu. `hello-world` then proved the full pipe.
- **The storage decision** — C: had only 62 GB free; E: (external SSD) had ~800 GB. Manglam chose, as a solo dev, **storage peace-of-mind over a little speed** → put everything on E:. Correct priority for an individual, not a company.
- **The distro-move ordeal** — relocating Ubuntu to E: hit every WSL error in the book: `WSL_E_DISTRO_NOT_STOPPED` (VS Code/Docker holding the disk), `E_ACCESSDENIED` (needed admin PowerShell), `ERROR_FILE_NOT_FOUND` (a half-move had split the pointer from the file). **Claude misdiagnosed the E: file as a "dead clone" and told Manglam to delete it — it was the only copy. The distro was lost.** Recovered by reinstalling fresh (nothing of Manglam's was in it — no code written yet).
- **The fix that worked = reorder:** install fresh → **move while empty** → then work. The empty-distro move completed instantly (`BasePath → E:\wsl\Ubuntu` confirmed in the registry).
- **Repo born** — `~/02_dev/01_attest`, `git init`, identity set, branch `main`, `.gitignore` + `README.md` committed and pushed to GitHub. Safety net live.

---

## ✅ Decisions Locked This Session

- **Environment = WSL2 Ubuntu + Docker Desktop + VS Code Remote-WSL**, on a Windows host.
- **Editor = VS Code** (over PyCharm).
- **Storage = everything on E: (external SSD).** E: must be connected before WSL/Docker start.
- **Project path = `~/02_dev/01_attest`** (Linux home, on E:, fast side of the border).
- **Folder convention = `NN_name`.**  Default branch = **`main`**.
- **External-drive safety protocol adopted** (see Instructions delta) — GitHub from commit one, keep only precious+small in git, never yank E:, periodic `wsl --export` snapshot.

---

## 🧠 Hard-Won Lessons

- **Move an EMPTY distro, never a loaded one.** `wsl --manage --move` on a distro with data in it is fragile — it can split the pointer from the file and orphan/lose the disk. Correct order: install → move while empty → then work. This is the load-bearing lesson of the whole session.
- **On an external drive, GitHub isn't optional — it's the foundation.** The one moment we were unprotected (repo alive, nothing pushed) is exactly the state the protocol exists to kill.
- **`--move` needs: nothing holding the disk (quit VS Code + Docker + all terminals), admin PowerShell, an NTFS destination, and an EMPTY target folder.** Miss any one → a different error.
- **The Python on the host doesn't matter** — the app's Python is pinned inside the container (`python:3.12-slim`). Host had 3.14; irrelevant. (Banks part of **Q16**.)

### ⚠️ Process errors this session — Claude's (logged honestly)
- **Misdiagnosed the E: `ext4.vhdx` as a dead clone and instructed a delete — it was the only copy. Cost a reinstall.** Flip-flopped on the diagnosis mid-crisis instead of verifying first. Root fix: **before any destructive command on an external/WSL disk, confirm the file is the only copy AND take a backup first — no `-Force` deletes without a safety copy in hand.**
- **Didn't ask up front whether existing work already lived in the Ubuntu** before touching moves. Should always ask "is there anything of yours in here?" before disturbing an environment.
- **Kept handing one-step-ahead commands without thinking portfolio-level** (flat `attest` folder) — Manglam caught it and pushed for `NN_name`. Root fix: **think one step past the immediate command — name and structure for the long game, not just the next action.**

---

## ⏭️ Next Session — make the ground walk

| Step | One line                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------ |
| 0    | **Confirm GitHub push landed** (clear the PAT-auth wall if it blocked us).                                    |
| 1    | **B3 — the Docker skeleton:** one `docker-compose.yml`, four containers (Django · FastAPI · Postgres · Qdrant) that all come up together and are reachable. Empty but alive. |
| 2    | **B4 — close the parked calls:** accept/renegotiate the §02 numbers (record in Supersedes); pick US EDGAR vs Indian filings for the live corpus. |
| 3    | **Then Turn 1 proper** — one financial PDF → chunk → embed → ask → retrieve → cited answer. Text only.        |

**Reminder for B3:** plug in E: before starting Docker. If Docker won't start, first suspect = drive not mounted.
