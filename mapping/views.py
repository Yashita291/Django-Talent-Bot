"""Views. Auth + RBAC enforced — the governance claims are now working features.

Roles (Django Groups, created by the seed command):
  - 'recruiter': can run searches and see ONLY their own runs.
  - 'admin' (or is_staff/superuser): can see all runs + the admin console.
"""
from __future__ import annotations

import csv

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group 
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect 

from mapping.engine.dto import HiringBrief
from mapping.forms import SearchForm, RecruiterRegistrationForm 
from mapping.models import SearchRun
from mapping.services import run_search


def _is_admin(user) -> bool:
    return user.is_superuser or user.is_staff or user.groups.filter(name="admin").exists()


def _visible_runs(user):
    qs = SearchRun.objects.all()
    return qs if _is_admin(user) else qs.filter(user=user)


@login_required
def search_view(request):
    form = SearchForm(request.POST or None)
    outcome = None
    results = []

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        brief = HiringBrief(
            job_title=cd["job_title"], 
            industry=cd["industry"], 
            location=cd["location"],
            min_years_experience=cd["min_years_experience"], 
            skills=SearchForm.split(cd["skills"]),
            target_companies=SearchForm.split(cd["target_companies"]),
            exclude_companies=SearchForm.split(cd["exclude_companies"]),
            keywords=SearchForm.split(cd["keywords"]),
            exclusion_keywords=SearchForm.split(cd["exclusion_keywords"]),
        )
        outcome = run_search(brief, user=request.user, threshold=float(cd["threshold"]), top_k=cd["top_k"])
        results = list(outcome.run.results.all())

    return render(request, "mapping/search.html", {
        "form": form, 
        "outcome": outcome, 
        "results": results, 
        "is_admin": _is_admin(request.user),
    })


@login_required
def run_detail(request, run_id: int):
    run = get_object_or_404(_visible_runs(request.user), pk=run_id)
    return render(request, "mapping/run_detail.html", {"run": run, "results": run.results.all()})


@login_required
def run_csv(request, run_id: int):
    run = get_object_or_404(_visible_runs(request.user), pk=run_id)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="shortlist_run{run_id}.csv"'
    w = csv.writer(resp)
    w.writerow(["Rank", "Score", "Name", "Designation", "Company", "Location",
                "Exp", "Matched Skills", "LinkedIn", "Source"])
    for r in run.results.all():
        w.writerow([r.rank, round(r.score, 1), r.name, r.current_designation,
                    r.current_company, r.location, r.years_experience or "",
                    "; ".join(r.matched_skills), r.linkedin_url, r.source_url])
    return resp


@login_required
def audit_view(request):
    """Audit trail — own runs for recruiters, all runs for admins."""
    runs = _visible_runs(request.user)[:100]
    return render(request, "mapping/audit.html", {"runs": runs, "is_admin": _is_admin(request.user)})


def register_view(request):
    """Allows anonymous recruiters to create an account and assigns permissions securely."""
    if request.user.is_authenticated:
        return redirect("mapping:search")
        
    if request.method == "POST":
        form = RecruiterRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data.get("password"))
            user.save()
            
            # Attaching RBAC Group roles
            recruiter_group, created = Group.objects.get_or_create(name="recruiter")
            user.groups.add(recruiter_group)
            
            return redirect("login")
    else:
        form = RecruiterRegistrationForm()
        
    return render(request, "registration/register.html", {"form": form})