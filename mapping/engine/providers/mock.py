"""Default provider: serves curated fixture data from data/fixtures.json.

Lets the entire pipeline run with zero external dependencies, zero API keys, and zero
ToS exposure. It also applies cheap pre-filters (hard excludes) so the scoring layer
receives a recall-biased but not absurd candidate set, mimicking how a real search API
would be queried with include/exclude terms.
"""
from __future__ import annotations

import json
import os

from mapping.engine.providers.base import SearchProvider
from mapping.engine.dto import HiringBrief, CandidateProfile

_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures.json")


class MockProvider(SearchProvider):
    name = "mock"

    def __init__(self, fixture_path: str = _FIXTURE_PATH):
        with open(os.path.abspath(fixture_path), "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._pool = [CandidateProfile(**rec) for rec in raw]

    def search(self, brief: HiringBrief, limit: int = 50) -> list[CandidateProfile]:
        results: list[CandidateProfile] = []
        excl_companies = {c.strip().lower() for c in brief.exclude_companies}
        excl_kw = {k.strip().lower() for k in brief.exclusion_keywords}

        for cand in self._pool:
            blob = " ".join([
                cand.name, cand.current_company, cand.current_designation,
                cand.location, cand.industry or "", " ".join(cand.skills), cand.notes,
            ]).lower()

            if cand.current_company.strip().lower() in excl_companies:
                continue
            if any(kw and kw in blob for kw in excl_kw):
                continue

            results.append(cand)
            if len(results) >= limit:
                break
        return results
