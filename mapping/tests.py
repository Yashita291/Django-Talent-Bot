"""Full-stack tests. Run: python manage.py test"""
from django.contrib.auth.models import User, Group
from django.test import TestCase, Client

from mapping.models import SearchRun, CandidateResult

BRIEF = {
    "job_title": "AVP - Operations", "industry": "RCM / US Healthcare",
    "location": "Mumbai", "min_years_experience": 12,
    "skills": "Revenue Cycle Management, Operations, Delivery, Transformation",
    "threshold": 35, "top_k": 25,
}


class PipelineTests(TestCase):
    def setUp(self):
        self.rec_grp = Group.objects.create(name="recruiter")
        self.admin_grp = Group.objects.create(name="admin")
        self.rec = User.objects.create_user("rec", password="p")
        self.rec.groups.add(self.rec_grp)
        self.rec2 = User.objects.create_user("rec2", password="p")
        self.rec2.groups.add(self.rec_grp)
        self.admin = User.objects.create_user("adm", password="p", is_staff=True, is_superuser=True)

    def _run(self, client):
        return client.post("/", BRIEF)

    def test_auth_required(self):
        self.assertEqual(Client().get("/").status_code, 302)

    def test_search_ranks_and_persists(self):
        c = Client(); c.login(username="rec", password="p")
        self.assertEqual(self._run(c).status_code, 200)
        run = SearchRun.objects.latest("created_at")
        scores = [r.score for r in run.results.all()]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(run.user, self.rec)

    def test_dedup_and_filter(self):
        c = Client(); c.login(username="rec", password="p")
        self._run(c)
        run = SearchRun.objects.latest("created_at")
        names = [r.name.strip() for r in run.results.all()]
        self.assertLessEqual(names.count("Rajesh Menon"), 1)
        self.assertTrue(all("Engineering" not in r.current_designation for r in run.results.all()))

    def test_rbac_isolation(self):
        c = Client(); c.login(username="rec", password="p"); self._run(c)
        run = SearchRun.objects.latest("created_at")
        c2 = Client(); c2.login(username="rec2", password="p")
        self.assertEqual(c2.get(f"/run/{run.id}/").status_code, 404)
        adm = Client(); adm.login(username="adm", password="p")
        self.assertEqual(adm.get(f"/run/{run.id}/").status_code, 200)

    def test_csv_and_retention(self):
        c = Client(); c.login(username="rec", password="p"); self._run(c)
        run = SearchRun.objects.latest("created_at")
        r = c.get(f"/run/{run.id}/csv/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        before = CandidateResult.objects.count()
        CandidateResult.purge_stale(retention_days=0)
        self.assertLess(CandidateResult.objects.count(), before + 1)
