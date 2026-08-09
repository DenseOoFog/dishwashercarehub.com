#!/usr/bin/env python3

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from check_source_links import classify_status, source_urls


class SourceLinkTests(unittest.TestCase):
    def test_status_classification_distinguishes_dead_from_blocked(self):
        self.assertEqual(classify_status(200), "healthy")
        self.assertEqual(classify_status(301), "healthy")
        self.assertEqual(classify_status(404), "dead")
        self.assertEqual(classify_status(410), "dead")
        self.assertEqual(classify_status(403), "unverified")
        self.assertEqual(classify_status(503), "unverified")

    def test_source_extraction_is_unique_and_external(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "sample" / "index.html"
            page.parent.mkdir()
            page.write_text(
                '<a href="https://www.epa.gov/example">EPA</a>'
                '<a href="https://www.epa.gov/example">EPA duplicate</a>'
                '<a href="https://dishwashercarehub.com/about/">Internal</a>',
                encoding="utf-8",
            )
            self.assertEqual(source_urls(root), ["https://www.epa.gov/example"])


if __name__ == "__main__":
    unittest.main()
