"""Service layer: runs the framework-agnostic engine, persists via the ORM.

This is the seam between Django and the pure-Python intelligence layer. The engine
(scoring/dedup/providers) knows nothing about Django; this module translates a Django
request into an engine call and the engine's results into ORM rows. Keeping this boundary
clean is what made the FastAPI->Django port a copy-paste of `engine/`, not a rewrite.

Delivery mode is synchronous (real-time), justified in the docs: compliant providers
return in seconds, recruiters work interactively, and the call is structured so it can be
moved into a Celery task wholesale if/when deep batch searches justify a queue.
"""
from __future__ import annotations

from dataclasses import dataclass

from mapping.engine.dto import HiringBrief
from mapping.engine.scoring import score_candidate
from mapping.engine.dedup import deduplicate
from mapping.engine.providers.base import SearchProvider
from mapping.engine.providers.mock import MockProvider
from mapping.models import SearchRun, CandidateResult

RELEVANCE_THRESHOLD = 35.0


@dataclass
class RunOutcome:
    run: SearchRun
    filtered_out: int


def get_provider(name: str = "mock") -> SearchProvider:
    """Provider registry. Production providers register here behind config/secrets."""
    if name == "mock":
        return MockProvider()
    # if name == "serpapi": return SerpAPIProvider()   # key-gated, see GOVERNANCE.md
    raise ValueError(f"Unknown or unconfigured provider: {name}")


def run_search(brief: HiringBrief, user, provider_name: str = "mock",
               threshold: float = RELEVANCE_THRESHOLD, top_k: int | None = 25) -> RunOutcome:
    provider = get_provider(provider_name)

    raw = provider.search(brief)
    scored = [score_candidate(brief, c) for c in raw]
    kept = [s for s in scored if s.score >= threshold]
    filtered_out = len(scored) - len(kept)

    deduped = deduplicate(kept)
    deduped.sort(key=lambda s: s.score, reverse=True)
    if top_k:
        deduped = deduped[:top_k]

    run = SearchRun.objects.create(
        user=user if user and user.is_authenticated else None,
        provider=provider.name,
        job_title=brief.job_title,
        industry=brief.industry,
        location=brief.location,
        min_years_experience=brief.min_years_experience,
        skills=brief.skills,
        optional_filters={
            "target_companies": brief.target_companies,
            "exclude_companies": brief.exclude_companies,
            "keywords": brief.keywords,
            "exclusion_keywords": brief.exclusion_keywords,
        },
        result_count=len(deduped),
        filtered_out=filtered_out,
    )

    CandidateResult.objects.bulk_create([
        CandidateResult(
            run=run, rank=i, score=sc.score,
            name=sc.profile.name, current_company=sc.profile.current_company,
            current_designation=sc.profile.current_designation, location=sc.profile.location,
            years_experience=sc.profile.years_experience, matched_skills=sc.matched_skills,
            breakdown={k: round(v, 1) for k, v in sc.breakdown.items()},
            linkedin_url=sc.profile.linkedin_url or "", source_url=sc.profile.source_url or "",
            notes=sc.profile.notes or "",
        )
        for i, sc in enumerate(deduped, start=1)
    ])

    return RunOutcome(run=run, filtered_out=filtered_out)
