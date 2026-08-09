#!/usr/bin/env python3

from datetime import date
import unittest

from submit_indexnow import (
    HOST,
    INDEXNOW_KEY,
    KEY_URL,
    github_summary,
    payload,
    select_urls,
    url_categories,
)


class IndexNowTests(unittest.TestCase):
    def test_payload_uses_canonical_host_and_key_location(self):
        urls = ["https://dishwashercarehub.com/", "https://dishwashercarehub.com/tools/"]
        self.assertEqual(
            payload(urls, INDEXNOW_KEY),
            {
                "host": HOST,
                "key": INDEXNOW_KEY,
                "keyLocation": KEY_URL,
                "urlList": urls,
            },
        )

    def test_recent_selection_uses_sitemap_lastmod(self):
        records = [
            ("https://dishwashercarehub.com/new/", date(2026, 8, 9)),
            ("https://dishwashercarehub.com/old/", date(2026, 8, 1)),
        ]
        self.assertEqual(
            select_urls(records, since_days=2, today=date(2026, 8, 10)),
            ["https://dishwashercarehub.com/new/"],
        )
        self.assertEqual(select_urls(records), [record[0] for record in records])

    def test_negative_since_days_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "zero or greater"):
            select_urls([], since_days=-1)

    def test_summary_reports_selection_and_url_coverage_without_key(self):
        urls = [
            "https://dishwashercarehub.com/",
            "https://dishwashercarehub.com/articles/drain/",
            "https://dishwashercarehub.com/tools/noise-decoder/",
        ]
        self.assertEqual(
            url_categories(urls), {"articles": 1, "tools": 1, "other": 1}
        )
        summary = github_summary(
            urls, "https://api.indexnow.org/indexnow", since_days=2, status=202
        )
        self.assertIn("accepted (HTTP 202)", summary)
        self.assertIn("lastmod within 2 days", summary)
        self.assertIn("3 canonical URLs", summary)
        self.assertIn("1 articles", summary)
        self.assertNotIn(INDEXNOW_KEY, summary)


if __name__ == "__main__":
    unittest.main()
