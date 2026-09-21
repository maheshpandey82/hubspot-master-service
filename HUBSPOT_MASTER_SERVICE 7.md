# HubSpot Master Service — What To Build

## 0. Getting Started — Account, Repo & Submission

### Create your account
- Create a GitHub account if you don't already have one (or use your existing one).
- Send your GitHub username to the project contact so you can be invited/granted access as needed.

### Set up your own repository
- Create a new repository named `hubspot-master-service`.
- Initialize it with a `README.md`, a Python `.gitignore`, and this document (saved as `DESIGN.md`).

### Timeline
- Total timeline: **1 month** from kickoff to final submission.
- Suggested milestones:
  - **Week 1** — Project set up, HubSpot test/developer account access, logging in and getting an access token works.
  - **Week 2** — Requesting and paging through data from HubSpot works, including handling rate limits correctly.
  - **Week 3** — Turning the downloaded data into clean tables works, for the main record types (Contacts, Companies, Deals).
  - **Week 4** — Saving/uploading the finished tables, handling errors and pause/resume gracefully, testing, and final submission.

### How to submit
- Push all code to your repository and make sure it runs from scratch (someone else should be able to clone it and get it running by following your README).
- Include a `README.md` that explains: how to set it up, what settings/credentials it needs, how to run it, and how to run the tests.
- Include a short write-up describing what you built, how it was working (what you tested and confirmed worked), what's incomplete, and anything you weren't able to finish.
- Share the repository link with the project contact ahead of the 1-month deadline.

## 1. What This Service Is, In Plain Terms

This service's only job is to **pull data out of HubSpot on demand and hand it off in a clean, organized form.**

Think of it as a pipeline with one job: given a HubSpot account, go get its data, clean it up, and put it somewhere it can be picked up and used. Nothing about scheduling ("when to run"), and nothing about what happens to the data afterward — this service only handles the extraction and cleanup step.

Another system (a "Coordinator") will be the one calling this service to say "start pulling data for this account", "how's it going", "pause/cancel it", etc. This service just needs to respond correctly to those requests and do the work reliably — including respecting HubSpot's rate limits so it never gets the account blocked or throttled unexpectedly.

## 2. What Exactly You Need To Build

At a high level, build these pieces:

1. **A way to authenticate to HubSpot** using credentials provided to the service (an access token, refreshed automatically when it expires) and use it to make requests.
2. **A way to request data from HubSpot, one page at a time**, for each type of record (Contacts, Companies, Deals, etc.), following HubSpot's cursor-based pagination (each page tells you the cursor to fetch the next one).
3. **Rate limit handling** — HubSpot enforces both a short burst limit (roughly 100 requests per 10 seconds) and a daily limit (tens of thousands of requests per day, depending on the account). Your service must watch for "too many requests" responses, wait the amount of time HubSpot tells it to wait, and then continue — never just fail immediately because of rate limiting.
4. **A way to save each page of data as it comes in**, so a long-running extraction doesn't lose progress if interrupted.
5. **A way to clean up and reorganize each record type** into simple, consistent tables (e.g., turn a nested "Deal" record into a flat `deals` table, plus a small related table for its associations).
6. **A way to save the finished tables** as files and upload them to shared storage (MinIO), organized so other systems know where to find them (by account and by date).
7. **A tracking system for each run** ("job"), so that at any point you can ask "what's the status of this run?" and get an accurate answer — including if it crashed partway through, in which case it should be able to pick back up from the last page it successfully fetched instead of starting over.
8. **The ability to pause and resume a run**, not just cancel it — since large HubSpot accounts can take a while to fully pull.
9. **A small set of API endpoints** so the Coordinator system can start a run, check its status, pause/resume it, cancel it, and list past runs.
10. **Basic security**, so that only the Coordinator (not just anyone on the network) can call this service.
11. **Basic error handling**, so that if HubSpot or the storage system is briefly unavailable, the service retries a few times automatically instead of failing immediately — and if it keeps failing, it records what went wrong somewhere so someone can investigate later, instead of silently losing the request.

That's the entire scope. Everything below just explains each of these in more detail.

## 3. Tech Stack

- **Language/Framework:** Python, using **FastAPI** to build the API
- **Database:** PostgreSQL — to keep track of every run ("job"), its progress checkpoints, and its status
- **File storage:** MinIO — where the finished, cleaned-up data gets uploaded
- **Packaging:** Docker, so it can run the same way anywhere

You don't need anything more exotic than this — no message queues, no extra infrastructure beyond a database and a place to store files.

## 4. Step-By-Step: How A Single Run Should Work

1. The Coordinator tells your service: "start pulling data for this HubSpot account."
2. Your service saves a new "job" record so it can track progress, and immediately replies "started" (it doesn't make the Coordinator wait for the whole thing to finish).
3. In the background, your service, for each record type it needs to pull (Contacts, Companies, Deals, etc.):
   a. Gets a valid access token (refreshing it first if needed).
   b. Requests a page of records.
   c. If HubSpot responds with "too many requests," waits the required time and tries again.
   d. Saves a checkpoint (which page/cursor it just finished) so it can resume from here if interrupted.
   e. Repeats until there are no more pages.
4. Once all record types are pulled, it reorganizes the raw data into clean tables, saves them, and uploads them to storage.
5. It marks the job as complete — or as failed, with a reason, if something went wrong.
6. At any point, the Coordinator can ask your service for the status of a job, pause it, cancel it, or resume it from wherever it left off.

## 5. What Data To Pull From HubSpot

Build support for at least these record types to start:

- Contacts
- Companies
- Deals (and their line items/associations)
- Tickets
- Owners (the HubSpot users records are associated with)

Each one should end up as its own clean table (or a small handful of related tables) after processing.

## 6. API Endpoints You Need To Expose

| What it does | Example endpoint |
|---|---|
| Start a new run for an account | `POST /scan/start` |
| Check the status of a run | `GET /scan/{id}/status` |
| Pause a run | `POST /scan/{id}/pause` |
| Resume a paused/failed run | `POST /scan/{id}/resume` |
| Cancel a run | `POST /scan/{id}/cancel` |
| List past/active runs | `GET /scan/list` |
| Remove a run's records | `DELETE /scan/{id}/remove` |
| Trigger the "clean up the data" step for a run | `POST /normalize/{id}` |
| Check that credentials are valid before starting a run | `POST /validate-credentials` |
| Basic health check (is the service up) | `GET /health` |

You don't need to build much beyond this list — keep the API small and focused.

## 7. Handling Errors Gracefully

- If a call to HubSpot or to storage fails because of a temporary problem (timeout, connection issue, "server busy" response), automatically try again a few times before giving up.
- If HubSpot responds with a rate-limit error, treat it differently from a normal failure: wait the amount of time HubSpot specifies and continue, rather than counting it as one of your normal retry attempts.
- If it still fails after retries, don't lose the request — save a record of what failed and why, so it can be looked into later.
- If the service crashes or gets restarted mid-run, it should be able to tell (from its tracking records) that a run was left in an unfinished state, and either resume it from its last checkpoint or mark it as failed rather than leaving it stuck forever.

## 8. Security

- Only the Coordinator system should be able to call this service — every request coming in should be signed with a shared secret key, and the service should reject anything that isn't signed correctly.
- Credentials used to log into HubSpot should never be permanently stored in plain form — use them to get a token, then handle them carefully (encrypt at rest if they must be kept for token refresh).

## 9. What NOT To Build

This service does **not** need:
- Any deduplication or "has this record changed" logic — every run just produces a fresh set of tables.
- Any PII masking, anonymization, or redaction of the data — the data is passed through as-is.

Keep the scope limited to: connect → page through data (respecting rate limits) → clean up → store → track status.

---

## 10. Technical Appendix

Everything above is the plain-language version. This section spells out the same system in implementation-level detail.

### 10.1 Architecture Overview

```
Coordinator (calls via signed HTTP)
        │
        ▼
HubSpot Master Service (FastAPI)
        │
        ├── Auth: HubSpot OAuth 2.0 (access token + refresh token, or private-app token)
        ├── Fetch: HubSpot CRM API v3 (cursor-based pagination via `after`/`paging.next.after`)
        ├── Rate limiting: burst limit (~100 req / 10s) + daily limit, honor `Retry-After` on 429
        ├── Checkpointing: persist last-seen cursor per object type, per run
        ├── Normalization: flatten HubSpot objects into relational tables
        └── Publish: upload normalized Parquet files to MinIO
```

Each HubSpot object (Contact, Company, Deal, Ticket, Owner) is fetched independently, tracked as a sub-unit of the overall run, with its own pagination cursor.

### 10.2 Job Lifecycle / State Machine

A single `Job` row represents one run (one extraction for one account). Status values:

```
PENDING
  → RUNNING
  → PAUSED (cooperative — checked between pages)
  → RESUMING
  → NORMALIZING
  → UPLOADING_TO_MINIO
  → COMPLETED
```

Side states: `FAILED`, `CANCELLED`, `CRASHED` (heartbeat timeout while `RUNNING`).

Transition rules:
- `pause`: only from `RUNNING`/`PENDING`; rejected if already terminal (`COMPLETED`/`FAILED`/`CANCELLED`).
- `resume`: only from `PAUSED`/`CRASHED`; idempotent if already `RUNNING`/`RESUMING`; rejected if terminal.
- `cancel`: allowed from any non-terminal state.
- A background heartbeat is updated periodically while `RUNNING`; a separate maintenance check flags jobs whose heartbeat has gone stale as `CRASHED`.
- Resuming picks back up from the last saved cursor/page per object type, not from scratch.

### 10.3 API Endpoints (FastAPI routers)

All endpoints below (except `/health` and `/stats`) require HMAC-signed requests from the Coordinator (`X-HS-Signature`, `X-HS-Timestamp`, `X-HS-Client-ID`, `X-HS-Nonce` headers).

**`scan` router — `/api/scan`**

| Method | Path | Function |
|---|---|---|
| POST | `/scan/start` | `start_scan(request: ScanStartRequest)` — validates payload, creates job, kicks off background workflow, returns 202 with scan id |
| GET | `/scan/{scan_id}/status` | `get_scan_status(scan_id: str)` — returns current job status + per-object-type progress |
| POST | `/scan/{scan_id}/pause` | `pause_scan(scan_id: str)` — flags the job to pause at the next checkpoint boundary |
| POST | `/scan/{scan_id}/resume` | `resume_scan(scan_id: str)` — resumes from the last saved checkpoint per object type |
| POST | `/scan/{scan_id}/cancel` | `cancel_scan(scan_id: str)` — cancels the job |
| GET | `/scan/list` | `list_scans(organization_id: str \| None, page: int, page_size: int)` — paginated scan listing |
| GET | `/scan/statistics` | `get_scan_statistics()` — aggregate counts by status |
| DELETE | `/scan/{scan_id}/remove` | `remove_scan(scan_id: str)` — deletes job row + local files (blocked while active) |

**`normalization` router — `/api/normalization`**

| Method | Path | Function |
|---|---|---|
| POST | `/normalization/{scan_id}/normalize` | `normalize_scan(scan_id: str, format: str, save_to_disk: bool, upload_to_minio: bool)` — runs normalization → save → (optional) MinIO upload |
| GET | `/normalization/{scan_id}/tables` | `list_normalized_tables(scan_id: str)` — lists normalized table files for a scan |
| GET | `/normalization/supported-objects` | `get_supported_objects()` — static catalog of supported HubSpot objects and their output tables |

**`maintenance` router — `/api/maintenance`**

| Method | Path | Function |
|---|---|---|
| POST | `/maintenance/cleanup` | `cleanup_old_scans(days_old: int)` — deletes scans + local files older than N days |
| POST | `/maintenance/detect-crashed` | `detect_crashed_jobs(timeout_minutes: int)` — flags jobs with stale heartbeats as `CRASHED` |

**`credentials`**

| Method | Path | Function |
|---|---|---|
| POST | `/api/validate-credentials` | `validate_credentials(request: HubSpotCredentials)` — validates a HubSpot token via a lightweight identity call, without creating a job |

**Public/unauthenticated**

| Method | Path | Function |
|---|---|---|
| GET | `/api/health` | `health()` — liveness/readiness probe (DB + MinIO reachability) |
| GET | `/api/stats` | `service_stats()` — lightweight service-level counters |

**`audit` router — `/api/audit`**

| Method | Path | Function |
|---|---|---|
| GET | `/audit/logs` | `get_audit_logs(org_id, event_category, event_type, outcome, from_date, to_date, page, page_size)` — paginated audit log query |
| GET | `/audit/stats` | `get_audit_stats(window_minutes: int)` — rolling-window audit aggregates |

### 10.4 Core Services & Functions

**`JobService`**
- `create_job(scan_id, organization_id, request_config)` — creates the job row (credentials are never persisted in plain form)
- `get_job(scan_id)` — fetches a job by id
- `update_job_status(scan_id, status)` — transitions job status, enforcing the state machine rules in §10.2
- `update_heartbeat(scan_id)` — called periodically during long-running stages
- `save_checkpoint(scan_id, object_type, cursor, records_processed)` / `get_latest_checkpoint(scan_id, object_type)`
- `complete_job(scan_id, stats)` / `fail_job(scan_id, error)` / `cancel_job(scan_id)` / `pause_job(scan_id)` / `resume_job(scan_id)`
- `detect_crashed_jobs(timeout_minutes)` — heartbeat-based crash detection
- `cleanup_old_jobs(days_old)`

**`HubSpotAuthClient`**
- `get_access_token(credentials)` — exchanges/refreshes an OAuth token (or returns a configured private-app token directly); caches until near expiry
- `validate_credentials(credentials)` — performs a lightweight identity call (e.g. token/account info) to confirm credentials are valid without starting a run

**`HubSpotAPIClient`**
- `get_page(object_type, after_cursor, page_size)` — fetches one page of a given object type (`contacts`, `companies`, `deals`, `tickets`, `owners`), returning records + the next cursor (or `None` if done)
- `get_associations(object_type, record_id, to_object_type)` — fetches related-record associations where needed (e.g. deal → contacts)
- Internally wraps every call with rate-limit awareness: on a 429, reads the `Retry-After` header (or a configured default), sleeps, and retries — this is separate from, and checked before, the generic retry/backoff logic in §10.5

**`ExtractionService` (top-level orchestrator)**
- `start_scan(request_config)` — creates the job, launches the background workflow, returns immediately
- `_execute_scan(scan_id)` — for each configured object type: authenticate → page through records (checkpointing + pause/cancel checks between pages) → hand records to the normalizer
- `resume_scan(scan_id)` — resumes each object type from its last saved cursor
- `pause_scan(scan_id)` / `cancel_scan(scan_id)`
- `get_scan_status(scan_id)` / `get_scan_statistics()` / `remove_scan(scan_id)`

**`NormalizationService` + per-object normalizers**

Per-object normalizers, each implementing `normalize(records) -> dict[str, list[dict]]`:
- `ContactNormalizer` → `contacts`
- `CompanyNormalizer` → `companies`
- `DealNormalizer` → `deals`, `deal_line_items`, `deal_associations`
- `TicketNormalizer` → `tickets`
- `OwnerNormalizer` → `owners`

`NormalizationService.normalize_scan(scan_id, output_format, save_to_disk, upload_to_minio)`:
1. Lists the raw fetched records per object type.
2. Runs each normalizer, saves output as JSON or Parquet.
3. Aggregates stats, marks the job's normalization stage complete.
4. If `upload_to_minio`, uploads via `MinIOClient.upload_normalized_data`.
5. Cleans up local scan data on success.

**`MinIOClient`**
- `upload_file(local_path, object_key)`
- `upload_normalized_data(scan_id, organization_id, processing_date, tables)` — writes to `hubspot/{table_name}/glynac_organization_id={org_id}/processing_date={date}/{table}.parquet`
- `ensure_bucket_exists()`

**`AuditService`**
- `write_audit(event_category, event_type, organization_id, outcome, extra_metadata)` — fire-and-forget insert into `audit_logs`, non-blocking

### 10.5 Resilience — Retry, Rate-Limit Handling & Dead-Letter Queue

**`rate_limiter.py`**
- `handle_rate_limit_response(response)` — detects a 429, reads `Retry-After` (falling back to a configured default delay if absent), sleeps, and signals the caller to retry the same request — this check happens **before** generic retry logic, since a rate-limit response is not a failure to count against retry budget, just a "wait and continue" signal

**`retry.py`**
- `is_retryable(exc)` — classifies transient failures (timeouts, connection errors, `500/502/503/504`; `429` is handled separately by the rate limiter, not treated as a generic retryable error)
- `retry_call(fn, max_retries, delays, jitter, op_label)` — bounded-retry executor used around every external call (HubSpot API, MinIO)

**`dlq.py`**
- `write_to_dlq(target_service, operation, payload, attempts, error, organization_id=None, scan_id=None)` — persists an exhausted external call into `failed_external_calls`, scrubbing sensitive fields and capping payload size; never raises
- `scrub_payload(payload)` — redacts sensitive keys before persisting

### 10.6 HMAC Authentication

Dual-key scheme:
- **Coordinator key** — full access (GET/POST/DELETE)
- **Engineer/read-only key** — GET-only, for inspection endpoints
- Required headers: `X-HS-Signature`, `X-HS-Timestamp`, `X-HS-Client-ID`, `X-HS-Nonce`
- Canonical string: `METHOD\nPATH\nTIMESTAMP\nNONCE\nSHA256(BODY)`, signed with HMAC-SHA256
- Nonce replay protection, timestamp freshness window, and audit logging on every auth outcome (success, missing header, expired timestamp, invalid signature, replay, unauthorized)
- Implemented as a FastAPI dependency (`Depends(hmac_auth_required)`) applied per-router

### 10.7 Data Models

**`Job` (`jobs` table)**

Core identity/status/timing columns, plus:
- `object_types` (JSON list of configured HubSpot objects for this run)
- `entity_record_counts` (JSON, per-object-type counts)
- `normalized_at`, `minio_uploaded_at`
- `last_heartbeat` — used for crash detection

**`JobCheckpoint` (`job_checkpoints` table)**

FK to `jobs.id`, one row per (job, object_type): `cursor`, `records_processed`, `last_updated_at` — this is what makes pause/resume and crash-recovery possible without re-fetching everything.

**`AuditLog` (`audit_logs` table)**

`event_category`, `event_type`, `actor_client_id`, `actor_role`, `organization_id`, `entity_type`, `resource_type`, `resource_id`, `http_method`, `endpoint`, `request_ip`, `status_code`, `outcome`, `severity`, `error_detail`, `extra_metadata`, `created_at`.

**`FailedExternalCall` (`failed_external_calls` table)**

`target_service`, `operation`, `organization_id`, `scan_id`, `payload` (scrubbed/capped JSON), `attempts`, `last_error`, `status`, `created_at`.

### 10.8 Config

Environment-driven config (`Settings` via Pydantic `BaseSettings`), grouped as:
- App metadata (`APP_ENV`, `LOG_LEVEL`)
- Database (`DATABASE_URL`, pool size)
- HubSpot API (`HUBSPOT_CLIENT_ID`, `HUBSPOT_CLIENT_SECRET`, `HUBSPOT_API_BASE_URL`, `HUBSPOT_API_VERSION`, timeouts)
- Rate limiting (`HUBSPOT_BURST_LIMIT` default ~100 per 10s, `HUBSPOT_DAILY_LIMIT`, `HUBSPOT_RATE_LIMIT_WINDOW_SECONDS`, default retry-after fallback if the header is missing)
- Pagination (`HUBSPOT_DEFAULT_PAGE_SIZE`, `HUBSPOT_MAX_PAGE_SIZE`)
- MinIO (`MINIO_ENDPOINT`, `MINIO_BUCKET`, credentials)
- Resilience (`EXTERNAL_CALL_MAX_RETRIES`, `EXTERNAL_CALL_RETRY_DELAYS`, `EXTERNAL_CALL_JITTER`, `DLQ_PAYLOAD_MAX_BYTES`)
- HMAC (`HMAC_ENABLED`, `HMAC_SECRET_KEY_CORE`, `HMAC_SECRET_KEY_ENGINEER`, `HMAC_SIGNATURE_MAX_AGE`, `HMAC_CLIENT_CONFIG`)
- Health check flags

Environment-specific validation (staging/production) should fail fast at startup if secrets are placeholder values, HMAC is disabled, or DEBUG is enabled in production.

### 10.9 Deployment

Single Docker image, deployed to Nomad in dev/stage/prod, one task per environment, health check on `/api/health`, secrets templated from Vault (`secrets/data/hubspot/hubspot-master-service-{env}`).

### 10.10 Utils

- `deep_serialize(obj)` — recursively converts Decimals, UUIDs, Enums, and datetimes into JSON-safe structures for API responses
- `calculate_duration(start, end)` — ISO datetime diff in seconds for job duration reporting
- `build_pagination_info(page, page_size, total)` — standard pagination envelope
- `Encrypter` — optional Fernet-based symmetric encryption utility for any sensitive config blob that must be stored at rest
