#!/usr/bin/env python3
"""Credential-free regression tests for Search Console reporting helpers."""

import unittest

from gsc_fetch import aggregate_rows, fetch_all_rows, normalize_property_url, select_property


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
