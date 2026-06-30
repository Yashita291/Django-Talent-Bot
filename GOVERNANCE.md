# Security & Data Governance (Section 06)

This system processes **personal data of named individuals** (PII) — that fact drives
every decision below. The governance model is designed in, not bolted on.

## 0. Lawful basis and the scraping question (the decision that matters most)

The single most consequential choice in this project is *where candidate data comes
from*. The MVP deliberately **does not scrape LinkedIn or any site whose Terms of
Service prohibit it.**

- LinkedIn's User Agreement prohibits automated scraping. The often-cited `hiQ v.
  LinkedIn` decision addressed the *Computer Fraud and Abuse Act*; it did **not**
  establish that scraping public profiles is free of contract/ToS liability, and
  LinkedIn has obtained injunctions against scrapers. Building scraping into the tooling
  of an **executive-search firm** — whose business depends on its reputation and
  relationships with these same platforms and candidates — imports a legal and
  reputational liability into the core product.
- For India, the **DPDP Act 2023** governs processing of personal data of data
  principals in India. For any EU-based candidates, **GDPR** applies. Both require a
  lawful basis; "we scraped it because it was visible" is not one.

**The compliant production path** is a licensed data relationship: a SERP API (SerpAPI,
Bing Web Search) over public results, or a people-data API (Proxycurl, People Data Labs,
Apollo) that contractually grants usage rights. The architecture is built so these drop
in behind the `SearchProvider` interface with no downstream change. The MVP ships with a
mock provider so it can be evaluated with zero ToS exposure.

This is not over-caution. It is the difference between a tool the firm can actually
deploy and a demo that creates liability the moment it touches real data.

## 1. Data storage strategy — what, where, how long

- **What is stored:** the hiring brief, the ranked result set (name, company, title,
  location, experience, profile/source URLs, score breakdown), and an audit row per
  search.
- **Where:** SQLite for the MVP (file-based, zero-ops). Explicitly a swap point —
  Postgres in production for concurrency, encryption-at-rest, and managed backups. The
  schema is written to port without change.
- **How long — retention:** candidate result rows are **purged after 90 days by
  default** (`Storage.purge_older_than`). Rationale: a shortlist for a closed or stale
  requisition is PII with no continuing purpose, and data-minimisation principles
  (DPDP/GDPR) require not retaining it indefinitely. Audit rows are retained longer
  (traceability) but contain no candidate PII beyond the brief.

## 2. Access controls

- **MVP reality (stated honestly):** the prototype has **no authentication**. It is a
  single-user local tool. This is the **first production gap** and is flagged as such —
  not hidden.
- **Production model:** SSO (OIDC) + role-based access control. Two roles minimum —
  *recruiter* (run searches, see own results) and *admin* (see all, manage retention,
  read audit log). Provider API keys live in a secrets manager (e.g. AWS Secrets
  Manager / Vault), never in source or the database.

## 3. Auditability

Implemented now: every search writes a `search_runs` row capturing **who** (user),
**when** (UTC ISO timestamp), **what** (full brief JSON), **which provider**, and **how
many results**. Any output can be traced to a user and a moment. The UI surfaces the
last 50 runs. Production adds: immutable/append-only audit storage, and per-result
provenance (which provider returned each profile, already carried on the model).

## 4. What breaks at 10x — security model scalability

| Concern | MVP | Breaks at scale because | Production fix |
|---|---|---|---|
| AuthN/Z | none | multi-user PII access with no identity is non-compliant | SSO + RBAC |
| Storage | SQLite | single-writer; no encryption-at-rest | Postgres, encrypted, row-level security |
| Secrets | env var | not rotatable, leak-prone | secrets manager + rotation |
| Audit | mutable rows | repudiation risk | append-only / WORM audit store |
| Rate/abuse | none | a compromised account could exfiltrate the candidate DB | per-user quotas, anomaly alerts, export limits |
| Retention | manual purge fn | won't run itself | scheduled retention job + legal-hold exceptions |

## 5. Summary

The governance posture is: **minimise what is collected, license what is collected,
trace every access, and retain nothing longer than its purpose.** The MVP implements
audit and retention today and is explicit about the auth gap rather than pretending it
is solved — which is the honest senior-engineer position the brief asks for.
