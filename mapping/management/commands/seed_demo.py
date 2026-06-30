"""Seed demo roles and users so the evaluator can log in immediately.

Creates:
  - groups 'recruiter' and 'admin'
  - recruiter / recruiterpass   (role: recruiter, sees own runs only)
  - admin / adminpass           (role: admin + staff, sees everything + /admin)
"""
from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed demo groups and users."

    def handle(self, *args, **opts):
        recruiter_grp, _ = Group.objects.get_or_create(name="recruiter")
        admin_grp, _ = Group.objects.get_or_create(name="admin")

        if not User.objects.filter(username="recruiter").exists():
            u = User.objects.create_user("recruiter", password="recruiterpass")
            u.groups.add(recruiter_grp)
            self.stdout.write("created recruiter / recruiterpass")

        if not User.objects.filter(username="admin").exists():
            a = User.objects.create_user("admin", password="adminpass", is_staff=True, is_superuser=True)
            a.groups.add(admin_grp)
            self.stdout.write("created admin / adminpass (staff+superuser)")

        self.stdout.write(self.style.SUCCESS("seed complete"))
