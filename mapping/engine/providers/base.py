"""The pluggable data-discovery interface.

This is the single most important abstraction in the system. Everything downstream
(scoring, dedup, storage, UI) depends only on this contract, never on a concrete
data source. Swapping mock fixtures for a licensed production API is a one-class change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from mapping.engine.dto import HiringBrief, CandidateProfile


class SearchProvider(ABC):
    """Returns raw candidate profiles for a hiring brief.

    Implementations are responsible for respecting the Terms of Service and data-privacy
    obligations of whatever source they wrap. The system intentionally ships NO provider
    that scrapes a site prohibiting it.
    """

    name: str = "base"

    @abstractmethod
    def search(self, brief: HiringBrief, limit: int = 50) -> list[CandidateProfile]:
        """Discover candidate profiles relevant to the brief.

        Implementations should over-return (recall-biased); the scoring layer handles
        precision. Returning duplicates is acceptable — the dedup layer handles it.
        """
        raise NotImplementedError
