# AI Talent Mapping & Research Bot — Django MVP

A Django application that turns a structured hiring brief into a **ranked, deduplicated,
fully-sourced, access-controlled, audited** candidate shortlist.

## Why Django (the justification the assignment asks for)

The hard part of this product — relevance scoring, deduplication, source abstraction — is
pure Python and framework-independent. Django is chosen for what surrounds that core,
because the assignment weights **security & governance** heavily and Django delivers those
as working features instead of promises:

| Requirement (Section 06) | Django gives it |
|---|---|
| Access controls / RBAC | Auth system + Groups (`recruiter`, `admin`), enforced in every PII view |
| Auditability | Every search → a `SearchRun` row (who/when/what/provider/count); admin console browses them |
| Data storage + retention | ORM + migrations; `CandidateResult.purge_stale()` enforces a 90-day PII window |
| 10x scalability | One-line Postgres swap (models unchanged); pipeline is Celery-ready for the overnight delivery mode |

The intelligence layer lives in `mapping/engine/` and imports **nothing** from Django —
the same code ran under the earlier FastAPI/Streamlit MVP. That clean boundary is the
design point: Django is the shell, not the brain.

## Quick start

```bash
cd talent_django
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # creates demo roles + users
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in:

| User | Password | Role | Sees |
|---|---|---|---|
| `recruiter` | `recruiterpass` | recruiter | only their own searches |
| `admin` | `adminpass` | admin (staff+superuser) | all searches + `/admin` console |

Try the example brief (pre-filled): AVP – Operations, RCM / US Healthcare, Mumbai, 12+ yrs.

## What to look at

- **Score breakdown** under each result — the system explains *why* each candidate ranked
  where they did (skills/title/experience/industry/location). Not a black box.
- **Audit log** (`/audit/`) — recruiters see their own runs; admins see everyone's.
- **RBAC** — log in as `recruiter2` (create via admin) and try to open another recruiter's
  run URL: 404. Admins can open any.
- **Admin console** (`/admin/`) — the governance/audit UI, for free.

## Architecture

```
Browser ──login──► Django (auth + RBAC)
   │ POST brief
   ▼
mapping/views.py ──► mapping/services.py ──► mapping/engine/  (framework-agnostic)
                                                ├ providers/ (Mock | SerpAPI stub)
                                                ├ scoring.py  (weighted, documented)
                                                ├ dedup.py
                                                └ query.py
                          │
                          ▼
                   ORM: SearchRun + CandidateResult  (SQLite → Postgres swap point)
                          │
                          ▼
                   templates (search / audit / detail) + CSV export
```

## Tests

```bash
python e2e_check.py      # full-stack: auth gate, search, ranking, dedup, RBAC, CSV, retention
```

## Governance

See `GOVERNANCE.md` — including why this MVP ships **no LinkedIn scraper** and uses a
licensed-provider abstraction instead.

## Production gaps (stated honestly)
- SQLite → Postgres for concurrency + encryption-at-rest (models already portable).
- Provider keys → secrets manager, not env vars.
- Synchronous delivery → Celery task for deep/overnight batch searches (the seam exists in `services.run_search`).
- Add SSO (OIDC) on top of the existing auth.
