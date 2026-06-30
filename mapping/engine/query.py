"""Builds a boolean search string from a hiring brief.

Used by real search providers (and useful to show recruiters the query that was run,
which aids the auditability requirement). Kept separate so every provider expresses
intent the same way.
"""
from __future__ import annotations

from mapping.engine.dto import HiringBrief


def build_boolean_query(brief: HiringBrief) -> str:
    parts: list[str] = []
    if brief.job_title:
        parts.append(f'"{brief.job_title}"')
    if brief.location:
        parts.append(f'"{brief.location}"')
    if brief.industry:
        parts.append(f'"{brief.industry}"')

    skill_clause = " OR ".join(f'"{s}"' for s in brief.skills if s.strip())
    if skill_clause:
        parts.append(f"({skill_clause})")

    for kw in brief.keywords:
        if kw.strip():
            parts.append(f'"{kw.strip()}"')
    for tc in brief.target_companies:
        if tc.strip():
            parts.append(f'"{tc.strip()}"')

    for ex in brief.exclude_companies:
        if ex.strip():
            parts.append(f'-"{ex.strip()}"')
    for ex in brief.exclusion_keywords:
        if ex.strip():
            parts.append(f'-"{ex.strip()}"')

    return " ".join(parts)
