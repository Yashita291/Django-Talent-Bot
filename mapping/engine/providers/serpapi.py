"""Production provider STUB — demonstrates the swap path. Not active by default.

This shows how a licensed search API (SerpAPI over Google, Bing Web Search, or a
people-data API such as Proxycurl / People Data Labs) plugs in WITHOUT touching any
downstream code. It is key-gated and raises clearly if used without configuration.

Why a search API and not a scraper:
  - LinkedIn's ToS prohibits scraping; scraping named individuals creates real legal
    and reputational exposure for an executive-search firm. See GOVERNANCE.md.
  - A SERP/people-data API is a licensed, contractual relationship with defined usage
    rights, which is the compliant production path.

The body is intentionally left as a documented skeleton: wiring a real key into an
evaluation environment is out of scope and would incur cost. The contract it satisfies
(SearchProvider.search) is identical to MockProvider, which is the whole point.
"""
from __future__ import annotations

import os

from mapping.engine.providers.base import SearchProvider
from mapping.engine.dto import HiringBrief, CandidateProfile
from mapping.engine.query import build_boolean_query


class SerpAPIProvider(SearchProvider):
    name = "serpapi"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SERPAPI_KEY")
        if not self.api_key:
            raise RuntimeError(
                "SerpAPIProvider requires SERPAPI_KEY. The MVP defaults to MockProvider; "
                "set the key and select this provider only in a configured environment."
            )

    def search(self, brief: HiringBrief, limit: int = 50) -> list[CandidateProfile]:
        query = build_boolean_query(brief)
        # Production implementation (pseudocode — left inert on purpose):
        #
        #   import requests
        #   resp = requests.get("https://serpapi.com/search", params={
        #       "engine": "google", "q": query, "num": limit, "api_key": self.api_key,
        #   }, timeout=20)
        #   resp.raise_for_status()
        #   organic = resp.json().get("organic_results", [])
        #   return [self._parse(r) for r in organic if self._looks_like_profile(r)]
        #
        # Parsing a SERP into structured fields (name/company/title) requires an
        # extraction step (regex heuristics or a small LLM call). That extraction is
        # the genuinely hard part of the production version and is documented in the
        # Technical Design notes rather than faked here.
        raise NotImplementedError(
            "SerpAPIProvider is a documented production stub. Use MockProvider for the demo."
        )
