from django.urls import path
from mapping import views

app_name = "mapping"

urlpatterns = [
    path("", views.search_view, name="search"),
    path("audit/", views.audit_view, name="audit"),
    path("run/<int:run_id>/", views.run_detail, name="run_detail"),
    path("run/<int:run_id>/csv/", views.run_csv, name="run_csv"),
]
