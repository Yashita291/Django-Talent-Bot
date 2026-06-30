"""Relevance scoring.

This is the "Intelligence Layer" (Section 03C). The brief requires that the methodology
be independently designed and its reasoning documented. The design goals:

  1. Explainable, not a black box. Every score decomposes into named signals so a
     recruiter can see WHY a candidate ranked where they did. (LLM-as-scorer was
     rejected for the MVP: non-deterministic, costly per call, and unauditable —
     poor fit for a system that must defend its outputs.)
  2. Deterministic and testable. Same brief + same pool => same ranking.
  3. Tunable. Weights live in one dict; recruiters/admins can reweight without code
     changes in a later version.

Signal weights (sum to 100). These reflect what an executive-search recruiter actually
prioritises for a senior operational hire:

    skills        35   most predictive of functional fit
    title         20   seniority / role alignment
    experience    20   senior hires are gated hard on years
    industry      15   domain (RCM/healthcare) transfers poorly across sectors
    location      10   movable but a real constraint for many roles

Experience is treated as a soft gate: at/above the floor scores full; below the floor is
penalised proportionally rather than hard-dropped, because a strong candidate one year
short is worth surfacing with a flag. A title that signals a completely different function
(e.g. "Software Engineer") collapses the title signal toward zero, which — combined with a
low industry/skills score — pushes off-function profiles to the bottom where the filter
threshold removes them.
"""
from __future__ import annotations

from mapping.engine.dto import HiringBrief, CandidateProfile, ScoredCandidate

WEIGHTS = {
    "skills": 35.0,
    "title": 20.0,
    "experience": 20.0,
    "industry": 15.0,
    "location": 10.0,
}

# Title seniority tiers for fuzzy seniority comparison.
_SENIORITY = {
    "intern": 0, "analyst": 1, "associate": 1, "engineer": 1, "executive": 1,
    "senior": 2, "lead": 2, "specialist": 2,
    "manager": 3, "sr manager": 3, "senior manager": 3,
    "avp": 4, "associate vice president": 4, "assistant vice president": 4, "director": 4,
    "vp": 5, "vice president": 5, "senior director": 5,
    "svp": 6, "head": 6,
    "cxo": 7, "chief": 7, "ceo": 7, "coo": 7, "cfo": 7, "president": 7,
}


def _skill_score(brief: HiringBrief, cand: CandidateProfile) -> tuple[float, list[str]]:
    wanted = set(brief.normalized_skills())
    if not wanted:
        return WEIGHTS["skills"], []
    have = {s.strip().lower() for s in cand.skills}
    matched = sorted(wanted & have)
    frac = len(matched) / len(wanted)
    return WEIGHTS["skills"] * frac, [m.title() for m in matched]


def _seniority_of(title: str) -> int:
    t = title.lower()
    best = 1  # default to IC-ish if nothing matches
    for key, level in _SENIORITY.items():
        if key in t:
            best = max(best, level)
    return best


def _title_score(brief: HiringBrief, cand: CandidateProfile) -> float:
    target = _seniority_of(brief.job_title)
    actual = _seniority_of(cand.current_designation)
    gap = abs(target - actual)
    # Asymmetric distance penalty: being UNDER the target tier is worse (candidate may
    # not be ready) than being one tier OVER (overqualified but credible). Each tier
    # under loses 40%; each tier over loses 25%.
    if actual < target:
        factor = max(0.0, 1.0 - 0.40 * gap)
    else:
        factor = max(0.0, 1.0 - 0.25 * gap)
    # Bonus if the brief's core role word appears verbatim (e.g. "operations").
    core_words = [w for w in brief.job_title.lower().replace("-", " ").split() if len(w) > 3]
    if any(w in cand.current_designation.lower() for w in core_words):
        factor = min(1.0, factor + 0.15)
    return WEIGHTS["title"] * factor


def _experience_score(brief: HiringBrief, cand: CandidateProfile) -> float:
    floor = brief.min_years_experience
    yrs = cand.years_experience
    if yrs is None:
        return WEIGHTS["experience"] * 0.4  # unknown => partial, not zero
    if yrs >= floor:
        # Full marks at/above floor; mild taper if wildly over (overqualified risk).
        over = yrs - floor
        taper = 1.0 if over <= 8 else max(0.7, 1.0 - 0.03 * (over - 8))
        return WEIGHTS["experience"] * taper
    # Below floor: proportional penalty.
    return WEIGHTS["experience"] * max(0.0, yrs / floor) * 0.7


def _industry_score(brief: HiringBrief, cand: CandidateProfile) -> float:
    if not brief.industry:
        return WEIGHTS["industry"]
    target_tokens = {t for t in brief.industry.lower().replace("/", " ").split() if len(t) > 2}
    # Match against the candidate's declared industry only — NOT notes — so a wrong-sector
    # profile (e.g. banking) can't borrow credit from incidental words.
    blob = (cand.industry or "").lower()
    if not target_tokens:
        return WEIGHTS["industry"]
    hits = sum(1 for t in target_tokens if t in blob)
    return WEIGHTS["industry"] * (hits / len(target_tokens))


def _location_score(brief: HiringBrief, cand: CandidateProfile) -> float:
    if not brief.location:
        return WEIGHTS["location"]
    target = brief.location.lower().split(",")[0].strip()
    loc = cand.location.lower()
    if target in loc:
        return WEIGHTS["location"]
    # Same-metro neighbours get partial credit (cheap heuristic; a geo layer replaces this in V2).
    neighbours = {
        "mumbai": {"navi mumbai", "thane", "mumbai"},
    }
    for metro, group in neighbours.items():
        if target == metro and any(n in loc for n in group):
            return WEIGHTS["location"] * 0.7
    return WEIGHTS["location"] * 0.1


def score_candidate(brief: HiringBrief, cand: CandidateProfile) -> ScoredCandidate:
    skills_pts, matched = _skill_score(brief, cand)
    breakdown = {
        "skills": skills_pts,
        "title": _title_score(brief, cand),
        "experience": _experience_score(brief, cand),
        "industry": _industry_score(brief, cand),
        "location": _location_score(brief, cand),
    }
    total = sum(breakdown.values())
    return ScoredCandidate(profile=cand, score=total, breakdown=breakdown, matched_skills=matched)
