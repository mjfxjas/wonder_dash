"""Offline regression checks for dashboard startup configuration."""

import unittest
from unittest.mock import patch

from wonder_dash.config import WonderConfig
from wonder_dash.dashboard import run_dashboard


class StopBeforePolling(Exception):
    """Stop startup before any AWS or terminal operations."""


class DashboardConfigTests(unittest.TestCase):
    def startup_config(self, saved, environment):
        with patch.dict("os.environ", environment, clear=True):
            with patch("wonder_dash.dashboard._cloudwatch_client") as client:
                client.side_effect = StopBeforePolling
                with self.assertRaises(StopBeforePolling):
                    run_dashboard(saved)
                return client.call_args.args[0]

    def test_environment_distribution_allows_startup_without_saved_config(self):
        saved = WonderConfig()
        active = self.startup_config(saved, {"CF_DISTRIBUTION_ID": "E123EXAMPLE"})
        self.assertEqual(active.distribution_id, "E123EXAMPLE")
        self.assertIsNone(saved.distribution_id)

    def test_environment_period_is_normalized_before_client_creation(self):
        saved = WonderConfig(distribution_id="E123EXAMPLE", period_seconds=300)
        for supplied, expected in [("1", 60), ("61", 120), ("120", 120)]:
            with self.subTest(period=supplied):
                active = self.startup_config(saved, {"CF_PERIOD_SECONDS": supplied})
                self.assertEqual(active.period_seconds, expected)
        self.assertEqual(saved.period_seconds, 300)

    def test_saved_distribution_is_used_when_environment_has_no_override(self):
        active = self.startup_config(WonderConfig(distribution_id="E123EXAMPLE"), {})
        self.assertEqual(active.distribution_id, "E123EXAMPLE")

    def test_blank_environment_distribution_is_rejected_before_aws_access(self):
        with patch.dict("os.environ", {"CF_DISTRIBUTION_ID": " \t "}, clear=True):
            with patch("wonder_dash.dashboard._cloudwatch_client") as client:
                with patch("wonder_dash.dashboard.console"):
                    with self.assertRaises(SystemExit) as error:
                        run_dashboard(WonderConfig())
                self.assertEqual(error.exception.code, 1)
                client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
