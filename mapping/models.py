"""Django ORM models.

This is the upgrade over the raw-sqlite3 version of the MVP: real migrations, the admin
console as a free audit/data-governance UI, and a one-line Postgres swap (change DATABASES
in settings; the models are unchanged).

Governance is modelled explicitly:
  - SearchRun is the audit record (who/when/what/provider/count).
  - CandidateResult holds the PII; it is FK-linked to a run so retention can cascade.
  - A RETENTION_DAYS-aware manager method purges stale PII.
"""
from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.db import models
from django.utils import timezone


class SearchRun(models.Model):
    """One execution of the pipeline. Backs the audit trail (Section 06)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, related_name="search_runs")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    provider = models.CharField(max_length=64)

    job_title = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    min_years_experience = models.PositiveIntegerField()
    skills = models.JSONField(default=list)
    optional_filters = models.JSONField(default=dict)

    result_count = models.PositiveIntegerField(default=0)
    filtered_out = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        who = self.user.username if self.user else "deleted-user"
        return f"{self.created_at:%Y-%m-%d %H:%M} · {who} · {self.job_title}"


class CandidateResult(models.Model):
    """A ranked candidate within a run. Holds PII — subject to retention."""
    run = models.ForeignKey(SearchRun, on_delete=models.CASCADE, related_name="results")
    rank = models.PositiveIntegerField()
    score = models.FloatField()

    name = models.CharField(max_length=255)
    current_company = models.CharField(max_length=255)
    current_designation = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    years_experience = models.PositiveIntegerField(null=True, blank=True)
    matched_skills = models.JSONField(default=list)
    breakdown = models.JSONField(default=dict)
    linkedin_url = models.URLField(blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["run", "rank"]

    def __str__(self) -> str:
        return f"#{self.rank} {self.name} ({self.score:.0f})"

    @classmethod
    def purge_stale(cls, retention_days: int | None = None) -> int:
        """Delete candidate PII from runs older than the retention window.

        Audit metadata (SearchRun) is kept; only the PII-bearing results are removed,
        which is the data-minimisation position from GOVERNANCE.md. Returns rows deleted.
        """
        days = retention_days or getattr(settings, "RETENTION_DAYS", 90)
        cutoff = timezone.now() - dt.timedelta(days=days)
        qs = cls.objects.filter(run__created_at__lt=cutoff)
        deleted, _ = qs.delete()
        return deleted
