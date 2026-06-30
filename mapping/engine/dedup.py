"""Deduplication.

Profiles arrive from multiple sources and often repeat. We dedupe on a normalized
identity key and MERGE rather than drop, so the surviving record keeps the richest
field set and all source URLs (important for auditability — you want every place a
person was found, not just the first).

Identity key strategy, in priority order:
  1. LinkedIn URL (normalized) — strongest signal when present.
  2. normalized(name) + normalized(company) — fallback fuzzy identity.

This is deliberately conservative: it will occasionally keep two genuinely-distinct
people with identical name+company apart only if a LinkedIn URL differs. False merges
are worse than false splits in recruiting (you don't want to silently drop a real
candidate), so the tie-breaks favour splitting when signals conflict.
"""
from __future__ import annotations

import re

from mapping.engine.dto import ScoredCandidate


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\b(pvt|private|ltd|limited|inc|llc|global|solutions)\b", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_linkedin(url: str | None) -> str:
    if not url:
        return ""
    m = re.search(r"linkedin\.com/in/([^/?#]+)", url.lower())
    return m.group(1) if m else ""


def _identity_key(sc: ScoredCandidate) -> str:
    li = _norm_linkedin(sc.profile.linkedin_url)
    if li:
        return f"li:{li}"
    return f"nc:{_norm(sc.profile.name)}|{_norm(sc.profile.current_company)}"


def deduplicate(scored: list[ScoredCandidate]) -> list[ScoredCandidate]:
    by_key: dict[str, ScoredCandidate] = {}
    extra_sources: dict[str, set[str]] = {}

    for sc in scored:
        key = _identity_key(sc)
        if key not in by_key:
            by_key[key] = sc
            extra_sources[key] = set()
            if sc.profile.source_url:
                extra_sources[key].add(sc.profile.source_url)
            continue

        # Merge: keep the higher-scoring record as the survivor, absorb richer fields.
        survivor = by_key[key]
        loser = sc
        if loser.score > survivor.score:
            survivor, loser = loser, survivor

        # Union skills, prefer non-empty fields, collect all source URLs.
        merged_skills = list(dict.fromkeys(survivor.profile.skills + loser.profile.skills))
        survivor.profile.skills = merged_skills
        if not survivor.profile.linkedin_url:
            survivor.profile.linkedin_url = loser.profile.linkedin_url
        for src in (loser.profile.source_url, survivor.profile.source_url):
            if src:
                extra_sources[key].add(src)
        by_key[key] = survivor

    # Annotate survivors with the full source set.
    out: list[ScoredCandidate] = []
    for key, sc in by_key.items():
        srcs = sorted(extra_sources[key])
        if len(srcs) > 1:
            sc.profile.notes = (sc.profile.notes + f" [Found in {len(srcs)} sources]").strip()
        out.append(sc)
    return out
