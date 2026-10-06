"""CloudWatch regressions using local response stubs only."""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from wonder_dash.dashboard import fetch_request_series


class MetricPaginationTests(unittest.TestCase):
    def test_reads_all_pages_and_merges_scalar_history(self):
        first = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        second = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
        client = Mock()
        client.get_metric_data.side_effect = [
            {"NextToken": "next-page", "MetricDataResults": [
                {"Id": "requests", "Timestamps": [first], "Values": [2], "StatusCode": "PartialData"},
                {"Id": "bytes_downloaded", "Timestamps": [first], "Values": [10], "StatusCode": "PartialData"},
            ]},
            {"MetricDataResults": [
                {"Id": "requests", "Timestamps": [second], "Values": [3], "StatusCode": "Complete"},
                {"Id": "bytes_downloaded", "Timestamps": [second], "Values": [20], "StatusCode": "Complete"},
            ]},
        ]
        scalars = {}
        window = fetch_request_series(client, "EXAMPLE", 60, 120, scalars=scalars)
        self.assertEqual([sample.value for sample in window.samples], [2, 3])
        self.assertEqual(scalars["bytes_downloaded"].total, 30)
        self.assertEqual(scalars["bytes_downloaded"].latest, 20)
        self.assertEqual(window.status, "Complete")
        calls = client.get_metric_data.call_args_list
        self.assertNotIn("NextToken", calls[0].kwargs)
        self.assertEqual(calls[1].kwargs["NextToken"], "next-page")
        self.assertEqual(calls[0].kwargs["StartTime"], calls[1].kwargs["StartTime"])

    def test_incomplete_metric_is_not_hidden_by_later_complete_metric(self):
        client = Mock()
        client.get_metric_data.return_value = {"MetricDataResults": [
            {"Id": "requests", "StatusCode": "Forbidden", "Messages": [{"Code": "Denied", "Value": "no access"}]},
            {"Id": "bytes_downloaded", "StatusCode": "Complete"},
        ]}
        window = fetch_request_series(client, "EXAMPLE", 60, 10)
        self.assertEqual(window.status, "Forbidden")
        self.assertEqual(window.messages, ["Denied: no access"])

    def test_empty_response_clears_previous_scalars(self):
        client = Mock()
        client.get_metric_data.return_value = {}
        scalars = {"stale": object()}
        window = fetch_request_series(client, "EXAMPLE", 60, 10, scalars=scalars)
        self.assertEqual(window.status, "NoData")
        self.assertEqual(scalars, {})
