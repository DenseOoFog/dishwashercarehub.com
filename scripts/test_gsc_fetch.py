#!/usr/bin/env python3
"""Credential-free regression tests for Search Console reporting helpers."""

import unittest

from gsc_fetch import (
    aggregate_rows,
    compare_aggregates,
    fetch_all_rows,
    metric_totals,
    normalize_property_url,
    select_property,
)


class PropertySelectionTests(unittest.TestCase):
    def test_url_prefix_trailing_slash_matches_exact_api_property(self):
        entries = [{"siteUrl": "https://dishwashercarehub.com/"}]
        self.assertEqual(select_property(entries, "https://dishwashercarehub.com"),
                         "https://dishwashercarehub.com/")

    def test_domain_property_is_not_given_a_trailing_slash(self):
        self.assertEqual(normalize_property_url("sc-domain:dishwashercarehub.com/"),
                         "sc-domain:dishwashercarehub.com")


class AggregationTests(unittest.TestCase):
    def test_ctr_and_position_use_impression_weighting(self):
        rows = [
            {"keys": ["/guide", "query-a"], "clicks": 1, "impressions": 10, "position": 2},
            {"keys": ["/guide", "query-b"], "clicks": 9, "impressions": 90, "position": 12},
        ]
        page = aggregate_rows(rows, 0)["/guide"]
        self.assertEqual(page["clicks"], 10)
        self.assertEqual(page["impressions"], 100)
        self.assertAlmostEqual(page["ctr"], 0.1)
        self.assertAlmostEqual(page["position"], 11.0)

    def test_metric_totals_do_not_double_count_query_rows(self):
        totals = metric_totals({
            "/a": {"clicks": 2, "impressions": 10, "ctr": .2, "position": 4},
            "/b": {"clicks": 3, "impressions": 30, "ctr": .1, "position": 8},
        })
        self.assertEqual(totals["clicks"], 5)
        self.assertEqual(totals["impressions"], 40)
        self.assertAlmostEqual(totals["ctr"], .125)
        self.assertAlmostEqual(totals["position"], 7)

    def test_comparison_retains_new_and_lost_keys(self):
        current = {
            "new": {"clicks": 1, "impressions": 20, "ctr": .05, "position": 12},
            "kept": {"clicks": 2, "impressions": 30, "ctr": 2/30, "position": 8},
        }
        previous = {
            "lost": {"clicks": 1, "impressions": 5, "ctr": .2, "position": 9},
            "kept": {"clicks": 1, "impressions": 10, "ctr": .1, "position": 11},
        }
        rows = {row["key"]: row for row in compare_aggregates(current, previous)}
        self.assertEqual(rows["new"]["impression_delta"], 20)
        self.assertEqual(rows["lost"]["impression_delta"], -5)
        self.assertEqual(rows["kept"]["position_delta"], 3)


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeSearchAnalytics:
    def __init__(self):
        self.calls = []

    def query(self, siteUrl, body):
        self.calls.append((siteUrl, body))
        count = 25_000 if body["startRow"] == 0 else 1
        return FakeRequest({"rows": [{"keys": ["x"]}] * count})


class FakeWebmasters:
    def __init__(self):
        self.analytics = FakeSearchAnalytics()

    def searchanalytics(self):
        return self.analytics


class PaginationTests(unittest.TestCase):
    def test_fetches_next_page_after_full_batch(self):
        service = FakeWebmasters()
        rows = fetch_all_rows(service, "https://dishwashercarehub.com/", {})
        self.assertEqual(len(rows), 25_001)
        self.assertEqual(service.analytics.calls[1][1]["startRow"], 25_000)


if __name__ == "__main__":
    unittest.main()
