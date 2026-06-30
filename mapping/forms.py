"""Search form. Mandatory fields per Section 03A, optional filters collapsed."""
from __future__ import annotations

from django import forms
from django.contrib.auth.models import User  # Added to support user generation

class SearchForm(forms.Form):
    job_title = forms.CharField(label="Job Title / Designation", max_length=255,
                                initial="AVP - Operations")
    industry = forms.CharField(label="Industry / Sector", max_length=255,
                               initial="RCM / US Healthcare")
    location = forms.CharField(max_length=255, initial="Mumbai")
    min_years_experience = forms.IntegerField(label="Min Years of Experience", min_value=0,
                                              max_value=40, initial=12)
    skills = forms.CharField(
        label="Key Skills (comma-separated)",
        initial="Revenue Cycle Management, Operations, Delivery, Transformation",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    # optional
    target_companies = forms.CharField(required=False, label="Target companies")
    exclude_companies = forms.CharField(required=False, label="Exclude companies")
    keywords = forms.CharField(required=False)
    exclusion_keywords = forms.CharField(required=False, label="Exclusion keywords")
    threshold = forms.IntegerField(label="Relevance threshold", min_value=0, max_value=80,
                                   initial=35)
    top_k = forms.IntegerField(label="Max results", min_value=5, max_value=50, initial=25)

    @staticmethod
    def split(text: str) -> list[str]:
        return [t.strip() for t in (text or "").replace("\n", ",").split(",") if t.strip()]


# --- NEW: Recruiter Self-Registration Form ---
class RecruiterRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Create Password"}),
        label="Password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat Password"}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={"placeholder": "Enter Username"}),
            'email': forms.EmailInput(attrs={"placeholder": "Enter Corporate Email"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("The passwords you entered do not match.")
        return cleaned_data