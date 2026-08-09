#!/usr/bin/env python3

from email.message import Message
import unittest

from check_live_site import (
    ADSENSE_SCRIPT_URL,
    PageParser,
    Response,
    atom_entry_urls,
    sitemap_urls,
    validate_html_page,
    validate_privacy_page,
    validate_redirect,
    validate_suspicious_probe,
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

    def test_published_page_rejects_injected_spam_copy(self):
        url = "https://dishwashercarehub.com/tools/"
        body = (
            f'<link rel="canonical" href="{url}">'
            f'<script src="{ADSENSE_SCRIPT_URL}"></script>'
            '<p>Claim an online casino bonus today.</p>'
        )
        response = Response(url, url, 200, headers("text/html"), body)
        self.assertTrue(any("casino or betting spam" in error for error in validate_html_page(response, url)))

    def test_suspicious_probe_accepts_protected_or_noindexed_missing_routes(self):
        protected_url = "https://dishwashercarehub.com/wp-login.php"
        protected = Response(protected_url, protected_url, 403, headers("text/html"), "forbidden")
        self.assertEqual(validate_suspicious_probe(protected, protected_url), [])

        missing_url = "https://dishwashercarehub.com/casino/"
        missing = Response(
            missing_url,
            missing_url,
            404,
            headers("text/html"),
            '<meta name="robots" content="noindex, follow">',
        )
        self.assertEqual(validate_suspicious_probe(missing, missing_url), [])

    def test_suspicious_probe_rejects_live_or_redirected_content(self):
        url = "https://dishwashercarehub.com/casino/"
        live = Response(url, url, 200, headers("text/html"), "live")
        self.assertTrue(any("should be rejected" in error for error in validate_suspicious_probe(live, url)))
        redirected = Response(url, "https://dishwashercarehub.com/", 404, headers("text/html"), "")
        errors = validate_suspicious_probe(redirected, url)
        self.assertTrue(any("redirected" in error for error in errors))

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

    def test_404_parser_detects_noindex_without_ads_or_canonical(self):
        body = '<html><head><meta name="robots" content="noindex, follow"></head><body data-error-page="404"></body></html>'
        response = Response(
            "https://dishwashercarehub.com/missing/",
            "https://dishwashercarehub.com/missing/",
            404,
            headers("text/html"),
            body,
        )
        parser = PageParser()
        parser.feed(response.body)
        self.assertTrue(any("noindex" in value for value in parser.robots_values))
        self.assertEqual(parser.canonicals, [])
        self.assertEqual(parser.adsense_scripts, 0)

    def test_permanent_redirect_accepts_relative_location(self):
        source = "https://dishwashercarehub.com/articles/old/"
        destination = "https://dishwashercarehub.com/articles/new/"
        redirect_headers = headers("text/plain")
        redirect_headers["Location"] = "/articles/new/"
        response = Response(source, source, 308, redirect_headers, "")
        self.assertEqual(validate_redirect(response, source, destination), [])

    def test_privacy_monitor_requires_advertising_choices_and_consent_disclosures(self):
        url = "https://dishwashercarehub.com/privacy/"
        complete_body = " ".join(
            (
                "https://policies.google.com/technologies/partner-sites",
                "https://adssettings.google.com/",
                "Google-certified consent management platform",
                "Do Not Sell or Share My Personal Information",
                "Global Privacy Platform",
                "mailto:pqiswin1@gmail.com",
            )
        )
        complete = Response(url, url, 200, headers("text/html"), complete_body)
        self.assertEqual(validate_privacy_page(complete), [])
        incomplete = Response(url, url, 200, headers("text/html"), "Privacy")
        self.assertGreaterEqual(len(validate_privacy_page(incomplete)), 6)

    def test_redirect_rejects_temporary_or_wrong_destination(self):
        source = "https://dishwashercarehub.com/articles/old/"
        redirect_headers = headers("text/plain")
        redirect_headers["Location"] = "/wrong/"
        response = Response(source, source, 307, redirect_headers, "")
        errors = validate_redirect(
            response, source, "https://dishwashercarehub.com/articles/new/"
        )
        self.assertTrue(any("permanent" in error for error in errors))
        self.assertTrue(any("expected redirect" in error for error in errors))

    def test_atom_feed_returns_unique_entry_ids(self):
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Updates</title>
          <id>https://dishwashercarehub.com/feed.xml</id>
          <updated>2026-08-09T00:00:00Z</updated>
          <link rel="self" type="application/atom+xml" href="https://dishwashercarehub.com/feed.xml" />
          <entry><title>Guide</title><id>https://dishwashercarehub.com/articles/guide/</id><updated>2026-08-09T00:00:00Z</updated><summary>Summary</summary></entry>
        </feed>"""
        response = Response(
            "https://dishwashercarehub.com/feed.xml",
            "https://dishwashercarehub.com/feed.xml",
            200,
            headers("application/atom+xml"),
            xml,
        )
        self.assertEqual(
            atom_entry_urls(response),
            ["https://dishwashercarehub.com/articles/guide/"],
        )


if __name__ == "__main__":
    unittest.main()
