#!/usr/bin/env python3

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from audit_performance_budget import audit_page


class PerformanceBudgetTests(unittest.TestCase):
    def test_small_deferred_page_passes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "site.css").write_text("body{}", encoding="utf-8")
            (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
            page = root / "index.html"
            page.write_text(
                '<link rel="stylesheet" href="site.css">'
                '<script src="app.js" defer></script>'
                '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=test"></script>',
                encoding="utf-8",
            )
            self.assertEqual(audit_page(page, root)[0], [])

    def test_unknown_or_blocking_external_script_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text('<script src="https://tracker.example/script.js"></script>', encoding="utf-8")
            errors, _ = audit_page(page, root)
            self.assertTrue(any("unexpected external script" in error for error in errors))
            self.assertTrue(any("render-blocking external script" in error for error in errors))

    def test_blocking_local_script_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.js").write_text("", encoding="utf-8")
            page = root / "index.html"
            page.write_text('<script src="app.js"></script>', encoding="utf-8")
            errors, _ = audit_page(page, root)
            self.assertTrue(any("render-blocking local script" in error for error in errors))

    def test_oversized_html_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text("x" * 100_001, encoding="utf-8")
            errors, _ = audit_page(page, root)
            self.assertTrue(any("HTML is" in error for error in errors))
            self.assertTrue(any("page weight" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
