"""Webhook redelivery: all GitHub calls mocked — no network."""
from datetime import datetime, timedelta, timezone
from unittest import mock

from django.test import TestCase

from apps.atlas.models import CloudProject
from apps.atlas.services import redelivery


def _ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _d(id_, guid, status, hours_ago=1.0, redelivery=False):
    return {"id": id_, "guid": guid, "status_code": status, "event": "push", "action": None,
            "delivered_at": _ts(hours_ago), "repository_id": 1, "redelivery": redelivery}


def _detail(ref="refs/heads/main", repo="Rinkels/crm", after="abc1234def"):
    return {"request": {"payload": {"ref": ref, "after": after, "repository": {"full_name": repo}}}}


class FindMissedTests(TestCase):
    def setUp(self):
        CloudProject.objects.create(name="crm", slug="crm", github_repo="Rinkels/crm", auto_deploy=True, deploy_branch="main")
        CloudProject.objects.create(name="dg", slug="dg", github_repo="Rinkels/DG", auto_deploy=False, deploy_branch="master")

    def test_failed_main_push_to_auto_project_is_missed(self):
        deliveries = [_d(10, "g1", 502)]
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()):
            missed = redelivery.find_missed(deliveries=deliveries)
        self.assertEqual([(m.delivery_id, m.repo, m.branch, m.commit, m.project_slug) for m in missed],
                         [(10, "Rinkels/crm", "main", "abc1234", "crm")])

    def test_non_deploy_branch_ignored(self):
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail(ref="refs/heads/auto-backup")):
            self.assertEqual(redelivery.find_missed(deliveries=[_d(10, "g1", 502)]), [])

    def test_non_auto_project_ignored(self):
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail(ref="refs/heads/master", repo="Rinkels/DG")):
            self.assertEqual(redelivery.find_missed(deliveries=[_d(10, "g1", 502)]), [])

    def test_guid_that_later_succeeded_is_not_replayed(self):
        deliveries = [_d(11, "g1", 200, hours_ago=0.5, redelivery=True), _d(10, "g1", 502, hours_ago=1)]
        with mock.patch.object(redelivery.github, "delivery_detail") as det:
            self.assertEqual(redelivery.find_missed(deliveries=deliveries), [])
            det.assert_not_called()

    def test_same_guid_failed_twice_counted_once(self):
        deliveries = [_d(11, "g1", 502, hours_ago=0.5, redelivery=True), _d(10, "g1", 502, hours_ago=1)]
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()):
            missed = redelivery.find_missed(deliveries=deliveries)
        self.assertEqual([m.delivery_id for m in missed], [11])

    def test_outside_window_ignored(self):
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()):
            self.assertEqual(redelivery.find_missed(hours=24, deliveries=[_d(10, "g1", 502, hours_ago=30)]), [])

    def test_successful_and_non_push_ignored(self):
        deliveries = [_d(10, "g1", 200), {**_d(12, "g2", 502), "event": "installation"}]
        with mock.patch.object(redelivery.github, "delivery_detail") as det:
            self.assertEqual(redelivery.find_missed(deliveries=deliveries), [])
            det.assert_not_called()


    def test_superseded_by_later_successful_deploy_is_skipped(self):
        from django.utils import timezone as dj_tz
        from apps.atlas.models import DeploymentRun
        crm = CloudProject.objects.get(slug="crm")
        # Failed 3h ago; Atlas deployed HEAD successfully 1h ago → nothing to replay.
        DeploymentRun.objects.create(cloud_project=crm, action="deploy", status="success",
                                     finished_at=dj_tz.now() - timedelta(hours=1))
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()):
            self.assertEqual(redelivery.find_missed(deliveries=[_d(10, "g1", 502, hours_ago=3)]), [])
        # But a failure AFTER the last successful deploy is still missed.
        with mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()):
            self.assertEqual(len(redelivery.find_missed(deliveries=[_d(11, "g2", 502, hours_ago=0.5)])), 1)


class DashboardTests(TestCase):
    def test_dashboard_renders_health_panel_without_network(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username="ops", password="pw-123456")
        self.client.force_login(user)
        CloudProject.objects.create(name="crm", slug="crm", github_repo="Rinkels/crm", auto_deploy=True, deploy_branch="main")
        with mock.patch.object(redelivery.httpx, "get", return_value=mock.Mock(status_code=405)), \
             mock.patch.object(redelivery.github, "list_deliveries", return_value=[_d(10, "g1", 502), _d(9, "g0", 200, 2)]), \
             mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()), \
             self.settings(ATLAS_WEBHOOK_PUBLIC_URL="https://example.test/hook/"):
            resp = self.client.get("/atlas/?refresh=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Auto-deploy webhook receiver")
        self.assertContains(resp, "reachable")
        self.assertContains(resp, "Replay missed (1)")

    def test_replay_view_requires_login_and_post(self):
        self.assertEqual(self.client.post("/atlas/webhook/replay/").status_code, 302)  # → login
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user(username="ops2", password="pw-123456"))
        self.assertEqual(self.client.get("/atlas/webhook/replay/").status_code, 405)
        with mock.patch.object(redelivery.github, "list_deliveries", return_value=[]):
            resp = self.client.post("/atlas/webhook/replay/")
        self.assertRedirects(resp, "/atlas/", fetch_redirect_response=False)


class RedeliverTests(TestCase):
    def setUp(self):
        CloudProject.objects.create(name="crm", slug="crm", github_repo="Rinkels/crm", auto_deploy=True, deploy_branch="main")

    def test_redelivers_missed_and_reports(self):
        with mock.patch.object(redelivery.github, "list_deliveries", return_value=[_d(10, "g1", 502), _d(20, "g2", 502)]), \
             mock.patch.object(redelivery.github, "delivery_detail", side_effect=[_detail(after="1111111"), _detail(after="2222222")]), \
             mock.patch.object(redelivery.github, "redeliver", side_effect=[True, False]) as rd:
            summary = redelivery.redeliver_missed()
        self.assertEqual(rd.call_args_list, [mock.call(10), mock.call(20)])
        self.assertEqual(len(summary["redelivered"]), 1)
        self.assertEqual(len(summary["errors"]), 1)
        self.assertIn("2222222", summary["errors"][0])

    def test_dry_run_touches_nothing(self):
        with mock.patch.object(redelivery.github, "list_deliveries", return_value=[_d(10, "g1", 502)]), \
             mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()), \
             mock.patch.object(redelivery.github, "redeliver") as rd:
            summary = redelivery.redeliver_missed(dry_run=True)
        rd.assert_not_called()
        self.assertEqual(len(summary["found"]), 1)
        self.assertTrue(summary["dry_run"])

    def test_one_failure_does_not_stop_the_rest(self):
        with mock.patch.object(redelivery.github, "list_deliveries", return_value=[_d(10, "g1", 502), _d(20, "g2", 502)]), \
             mock.patch.object(redelivery.github, "delivery_detail", return_value=_detail()), \
             mock.patch.object(redelivery.github, "redeliver", side_effect=[RuntimeError("boom"), True]):
            summary = redelivery.redeliver_missed()
        self.assertEqual(len(summary["redelivered"]), 1)
        self.assertIn("boom", summary["errors"][0])


class HealthTests(TestCase):
    def test_405_is_healthy_and_502_is_not(self):
        from django.core.cache import cache
        for status, ok in ((405, True), (502, False)):
            cache.delete(redelivery.HEALTH_KEY)
            resp = mock.Mock(status_code=status)
            with mock.patch.object(redelivery.httpx, "get", return_value=resp), \
                 self.settings(ATLAS_WEBHOOK_PUBLIC_URL="https://example.test/hook/"):
                self.assertEqual(redelivery.webhook_health(force=True)["ok"], ok)

    def test_unreachable_is_not_healthy(self):
        import httpx
        with mock.patch.object(redelivery.httpx, "get", side_effect=httpx.ConnectError("nope")), \
             self.settings(ATLAS_WEBHOOK_PUBLIC_URL="https://example.test/hook/"):
            h = redelivery.webhook_health(force=True)
        self.assertFalse(h["ok"])
        self.assertIn("unreachable", h["detail"])
