#!/usr/bin/env python3

from email.message import Message
import unittest

from check_live_site import (
    ADSENSE_SCRIPT_URL,
    Response,
    sitemap_urls,
    validate_html_page,
)


def headers(content_type):
    result = Message()
    result["Content-Type"] = content_type
    return result


class LiveSiteMonitorTests(unittest.TestCase):
    def test_valid_html_page(self):
        url = "https://dishwashercarehub.com/tools/"
        body = (
            f'<link rel="canonical" href="{url}">'
            f'<script src="{ADSENSE_SCRIPT_URL}"></script>'
        )
        response = Response(url, url, 200, headers("text/html; charset=utf-8"), body)
        self.assertEqual(validate_html_page(response, url), [])

    def test_bad_page_reports_canonical_ads_and_noindex(self):
        url = "https://dishwashercarehub.com/tools/"
        body = (
            '<link rel="canonical" href="https://example.invalid/">'
            '<meta name="robots" content="noindex, follow">'
        )
        response = Response(url, url, 200, headers("text/html"), body)
        errors = validate_html_page(response, url)
        self.assertTrue(any("matching canonical" in error for error in errors))
        self.assertTrue(any("AdSense" in error for error in errors))
        self.assertTrue(any("noindex" in error for error in errors))

    def test_sitemap_requires_unique_canonical_domain_urls(self):
        xml = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://dishwashercarehub.com/</loc><lastmod>2026-08-09</lastmod></url>
        </urlset>"""
        response = Response(
            "https://dishwashercarehub.com/sitemap.xml",
            "https://dishwashercarehub.com/sitemap.xml",
            200,
            headers("application/xml"),
            xml,
        )
        self.assertEqual(sitemap_urls(response), ["https://dishwashercarehub.com/"])
        duplicate = xml.replace("</urlset>", xml.split("<urlset", 1)[1].split(">", 1)[1].split("</urlset>", 1)[0] + "</urlset>")
        response.body = duplicate
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            sitemap_urls(response)


if __name__ == "__main__":
    unittest.main()
