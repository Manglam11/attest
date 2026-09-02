# 0001 — Tenancy

Status: decided, unimplemented. Recorded Turn 6 (2026-09-02). Implementation is
T6.2–T6.5.

## Context

Turn 6's definition of done: two users cannot see each other's corpus. The
survey (T6.1a) found none of the pieces that would make that true assumed to
exist actually did:

- No Django app, model, or auth exists beyond the framework skeleton. Django
  runs on sqlite, not the Postgres compose already provisions.
- There is no seam between Django and the engine — Django has no HTTP client
  dependency and no code that calls it.
- The engine's FastAPI routes (`/health`, `/ask`) have no authentication.
  Its port was published to the host, so any host process could call `/ask`
  directly, bypassing Django entirely — not a hypothetical, the live state.
- Qdrant payload carries `text`, `page`, `kind` only. No `doc_id`, no owner,
  no per-document identifier at all. `ingest.py` deletes and rebuilds the
  whole collection on every run against one hardcoded PDF.
- `payload_schema` on the collection was empty — no indexes of any kind.

Full detail: T6.1a chat record; not duplicated here.

## Decision

1. **Tenancy is a payload field in the single collection**, not a collection
   per tenant. `owner_id` as a keyword payload index with `is_tenant: true`.
   `doc_id` added in the same pass, since there is currently no per-document
   identity to hang ownership off either. This follows Qdrant's own current
   guidance: collection-per-tenant is their explicit anti-pattern outside
   regulatory-isolation or wildly-uneven-volume cases, neither of which
   applies here.
2. **Ingest becomes incremental.** Upsert per document; a document can be
   removed without touching others. Delete-and-rebuild-the-whole-collection
   dies.
3. **The engine authenticates its caller.** Django mints a short-lived signed
   token carrying `owner_id`; the engine verifies the signature and derives
   `owner_id` from the token, never from the request body. Standard library
   only — no new dependency for this.
4. **The engine's port is not published to the host.** (Done this bucket —
   see below.)
5. **Django owns Postgres.** The engine neither reads nor writes it.

## Threat model

**Defends against:** one authenticated user reading another authenticated
user's chunks — through the product UI, through a direct call to the engine
API, or through a request body that lies about whose data it wants. The
owner filter is enforced server-side in the retrieval query itself, keyed off
a signature the caller can't forge, not off anything the caller asserts.

**Does not defend against:** a compromised or malicious process already
inside the compose network (it can still reach `engine:8000` — unpublishing
the host port narrows the attack surface, it doesn't authenticate
container-to-container traffic); a leaked or replayed token within its
validity window; Django's own admin or superuser boundary, which is a
separate, unbuilt concern; anything at the Postgres or Qdrant transport layer
itself (no TLS, no per-service DB credentials yet); and multi-tenant
isolation *within* a single user's own documents, which was never the ask.

## Implementation note (T6.4) — canonical owner_id

Django's user identity is an integer pk; the 285 points already in Qdrant
carry `owner_id="alice"`, a username string. Canonical choice: **the
username string**, not the pk.

Reasons: the live payloads already match it — zero backfill, versus a
forced rewrite of all 285 points for the pk option with no functional
gain. The engine has no Django dependency and never will (it would
violate point 3's "no new dependency" for the *engine's* image), so
`owner_id` has no foreign-key relationship to `auth_user` to protect by
using the pk — it is just an opaque string claim in a signed token
either way. The only argument for pk (immunity to username rename) does
not apply: this app has no username-change flow, and a rename via
`/admin` is already out of scope per the threat model above (Django's
own admin/superuser boundary is a separate, unbuilt concern).

## Consequence of point 4

With the engine unreachable from the host, its liveness can no longer be
checked by hitting `localhost:8000/health` from outside. Compose now runs
the health check *inside* the engine container instead, over
`python3 -c "urllib.request.urlopen(...)"` — already present in the image,
no new dependency. `docker compose ps` reports the result the same way it
did when the check was external.
