"""Admin console = the data-governance + audit UI, for free.

Admins get a searchable, filterable view of every search run and every candidate result,
with the audit metadata (user, timestamp, provider) front and centre. This is the
'auditability' requirement (Section 06) realised as a working interface.
"""
from django.contrib import admin

from mapping.models import SearchRun, CandidateResult


class CandidateResultInline(admin.TabularInline):
    model = CandidateResult
    extra = 0
    readonly_fields = ("rank", "score", "name", "current_designation",
                       "current_company", "location", "matched_skills")
    fields = readonly_fields
    can_delete = False


@admin.register(SearchRun)
class SearchRunAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "user", "job_title", "location",
                    "provider", "result_count", "filtered_out")
    list_filter = ("provider", "created_at", "user")
    search_fields = ("job_title", "industry", "location", "user__username")
    readonly_fields = ("created_at",)
    inlines = [CandidateResultInline]


@admin.register(CandidateResult)
class CandidateResultAdmin(admin.ModelAdmin):
    list_display = ("name", "current_designation", "current_company",
                    "location", "score", "run")
    list_filter = ("location",)
    search_fields = ("name", "current_company", "current_designation")
