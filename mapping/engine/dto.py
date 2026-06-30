"""Domain models for the talent mapping system.

Plain dataclasses, no framework coupling. These are the contract between the
search providers, the scoring/dedup layer, the storage layer, and the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import datetime as _dt


@dataclass(frozen=True)
class HiringBrief:
    """The structured input. Mandatory fields per Section 03A; optional fields enhance ranking."""
    job_title: str
    industry: str
    location: str
    min_years_experience: int
    skills: list[str]
    # optional / enhancing
    target_companies: list[str] = field(default_factory=list)
    exclude_companies: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    exclusion_keywords: list[str] = field(default_factory=list)

    def normalized_skills(self) -> list[str]:
        return [s.strip().lower() for s in self.skills if s.strip()]


@dataclass
class CandidateProfile:
    """A raw candidate record as returned by a SearchProvider. Provider-agnostic."""
    name: str
    current_company: str
    current_designation: str
    location: str
    years_experience: Optional[int]
    skills: list[str] = field(default_factory=list)
    linkedin_url: Optional[str] = None
    source_url: Optional[str] = None
    industry: Optional[str] = None
    notes: str = ""
    provider: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScoredCandidate:
    """A candidate after relevance scoring. Carries a breakdown for transparency."""
    profile: CandidateProfile
    score: float                      # 0..100
    breakdown: dict[str, float]       # per-signal contribution, for explainability
    matched_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = self.profile.to_dict()
        d["score"] = round(self.score, 1)
        d["breakdown"] = {k: round(v, 1) for k, v in self.breakdown.items()}
        d["matched_skills"] = self.matched_skills
        return d


@dataclass
class SearchRun:
    """One execution of the pipeline. Backs the audit trail (Section 06)."""
    run_id: str
    user: str
    timestamp: str
    brief: dict
    provider: str
    result_count: int

    @staticmethod
    def now_iso() -> str:
        return _dt.datetime.now(_dt.timezone.utc).isoformat()
