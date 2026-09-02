# Demo Runbook — Attest

Cold-start-to-demo procedure for running Attest live, from this machine, under
time pressure. Every command and expected output below was run against a live
cold start and copied verbatim, not written from memory. See
`docs/sessions/Attest_Session_20.md` for the gate this runbook was built from.

## a. Pre-flight

Check these before touching Docker. Each failure mode below has actually
happened on this project.

| Check | How | Failure looks like |
| --- | --- | --- |
| External SSD (E:) connected | `ls /mnt/e` from WSL | WSL itself won't start, or `/mnt/e` is empty/missing — the whole distro lives on E:, this isn't optional |
| WSL running | any command in this shell succeeding | Terminal can't reach WSL at all |
| Docker Desktop running with WSL integration | `docker info` returns without error | `docker: command not found` or a connection error to the daemon |
| Repo clean, on `main`, matches remote | `git status -s -uall` (expect empty) and `git log --oneline -1` | Uncommitted changes or a HEAD that doesn't match what you pushed last session |

## b. Start sequence

```
cd ~/02_dev/01_attest
docker compose up -d
```

**Expect ~50 seconds** from this command to all four services answering
healthy. This is a measured figure, not an estimate — do not Ctrl-C it as a
hang. `engine` has a 60-second health-check `start_period` specifically
because model/embedding load is slow on first boot; watch `docker compose ps`
rather than the terminal going quiet.

## c. Verification block

Run these four in order. Real output observed on the last cold start is shown
under each — a match means go, a mismatch means stop and diagnose before
demoing.

**1. Engine health.** The engine container publishes no host port (see
`docker-compose.yml` — `engine:` has no `ports:` block, only `shell` does).
`curl localhost:8000` from the host will not work; check it from inside the
Docker network:

```
docker compose exec -T engine python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health', timeout=3).read().decode())"
```
Expected: `{"status":"alive","service":"engine"}`

**2. Postgres.**
```
docker compose exec -T postgres pg_isready -U "$(grep POSTGRES_USER .env | cut -d= -f2)" -d "$(grep POSTGRES_DB .env | cut -d= -f2)"
```
Expected: `/var/run/postgresql:5432 - accepting connections`

**3. Qdrant.**
```
curl -s http://localhost:6333/collections
```
Expected: `{"result":{"collections":[{"name":"attest_chunks"}]},"status":"ok",...}`

To confirm the corpus itself (304 points across three tenants):
```
curl -s http://localhost:6333/collections/attest_chunks | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['points_count'])"
```
Expected: `304`

**4. Shell.**
```
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/
```
Expected: `302` (redirect to login — this is correct, not a failure)

## d. Login

Use the `alice` account — she owns the real filing (`aapl_10k`, 285 points)
that every gold-set question and both proven live asks were run against.
`bruno` and `carla` only hold synthetic excerpts.

**Her password is not written anywhere in this repo, by design** — it has
already had to be reset twice (Sessions 19 and 20) because the prior value
was deliberately left undocumented. Confirm you have it before the audience
sits down. If it's lost, this resets it and spends no quota (Django-only,
touches no model):
```
docker compose exec shell python manage.py changepassword alice
```

## e. Demo path — live asks are OFF

**Live asks are off for tomorrow.** Provider latency is variable and has been
observed at 250s+ for a question shape that previously took 14s — see
`docs/sessions/Attest_Session_20.md` and JOURNAL.md for the two prior
observations (196s worst case, 40.5s / 14.1s live) this new figure sits
above. Root cause is not isolated; do not click **Ask** live in front of an
audience. Everything else below reads from Postgres or a frozen file on
disk and makes no engine call.

Walk pages in this order — every one of these is safe, no quota:

1. **Home** (`/`) — landing page. Static, no backend call.
2. **Login** — sign in as `alice`. Django auth only, no engine call.
3. **Library** (`/library/`) — shows all 3 tenants' documents backfilled from
   Qdrant/the source PDF ahead of time. Reads Postgres (`Document` rows)
   only — no live Qdrant or engine call at page-load time.
4. **Trust dashboard** (`/trust/`) — the frozen §02 numbers read from
   `data/eval/judged_20260831T101752Z.json`, including the one FAIL tile
   (retrieval precision, 0.774) rendered visibly, not hidden. Good place to
   narrate "we show our failures." Reads a file on disk, no engine call.
5. **History** (`/history/`) — the two already-proven live asks (one refusal,
   one grounded `112,010` net-income answer), read from Postgres
   `AskRecord` rows written in Session 20. No new call.

**Do not open `/ask/` and click Ask.** It is the only page in the product
that calls the engine and spends Gemini agent-key quota, and it is the page
whose latency is currently unexplained and has run 250s+. If asked live to
demonstrate it, say so plainly and show History instead — two real answers,
already proven, sitting in the database.

Current quota count for today (2026-09-02): **16** of ~20 — see
`data/quota/agent_calls.json`. This runbook update itself spent none of it.

## f. Shutdown

```
docker compose down
```

**Do not add `-v`.** That flag deletes the named volumes
(`postgres_data`, `qdrant_data`, `hf_cache`) — the corpus, the two proven
AskRecord rows, and every account including `alice`'s freshly-reset password
would be gone, and `hf_cache` would force a slow re-download of embedding
models on next boot. Plain `down` stops containers and keeps all volumes.

Only after containers are down is it safe to disconnect the external drive.

---

## Troubleshooting

Only failures this project has actually hit, from the session logs.

- **Docker won't start at all.** → First suspect is E: not plugged in, not a
  Docker bug (Sessions 02–17, repeatedly). Reconnect the drive, retry.
- **`docker compose ps` shows containers absent, not stopped/exited.** → They
  were never created this session (e.g. after a `down -v` or a fresh clone).
  Run `docker compose up -d`, don't try to "restart" something that doesn't
  exist.
- **A service reports started but doesn't answer.** → Session 12 lost two
  eval questions this way: the harness fired at the engine while it was still
  booting. Check `docker compose ps` health status (or `docker inspect
  --format='{{.State.Health.Status}}' attest_engine`) before treating a
  service as ready — "Up" is not the same as "healthy."
- **An answer is taking a long time.** → Not a hang. Session 19/20 measured a
  196-second worst case before the worker timeout was raised to 220s; grounded
  answers have taken as long as 14s and refusals as long as 40s in the two
  live runs so far. Give it up to ~4 minutes before suspecting a real failure.

## What NOT to do

- **Do not open `/ask/` and click Ask at all tomorrow.** Live asks are off
  for this demo — see section e. It is the only user action in the product
  that spends metered quota, and its latency is currently unexplained
  (250s+ observed against a 14s baseline for the same question shape).
  `GEMINI_API_KEY` has ~20 requests/day; today's count is already 16.
- **Do not open `/admin/`.** It's reachable without any special setup
  (standing since tenancy landed) and shows Django internals — not part of
  the product story.
- **Do not trigger a real Django error page.** `DEBUG = True` is still set in
  `shell/config/settings.py:27`, so an unhandled exception would render a full
  stack trace with settings values, not a clean error page.
- **Do not attempt to upload a document.** The feature does not exist yet —
  there is no upload button in any template, and `ingest.py` cannot currently
  run from the Django container even if invoked manually (its ML
  dependencies live only in the engine image, and `data/corpus` is mounted
  read-only into engine). If asked live, say "upload is the next bucket."
- **Do not point out the bold-text rendering as a demo highlight.** The
  engine returns markdown (`**bold**`) and the shell renders it as literal
  asterisks — cosmetic, known, not fixed. Not dangerous, just don't dwell on
  it if it comes up in an answer.
- **Library page is safe to show as-is** — checked its template
  (`shell/accounts/templates/accounts/library.html`): every field has an
  explicit fallback (`page count unknown`, `date unknown`, `0 chunks`) for
  missing data, so it will not render blank or throw for any of the three
  tenants' current records.
