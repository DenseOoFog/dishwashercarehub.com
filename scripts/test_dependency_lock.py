#!/usr/bin/env python3

import unittest

from audit_dependency_lock import audit_lock_text, logical_requirements


class DependencyLockTests(unittest.TestCase):
    def test_continuation_lines_form_one_requirement(self):
        text = "package==1.2.3 \\\n+            --hash=sha256:" + "a" * 64 + "\n"
        self.assertEqual(len(logical_requirements(text)), 1)

    def test_unpinned_dependency_fails(self):
        errors, _ = audit_lock_text("google-auth>=2\n")
        self.assertTrue(any("not exactly" in error for error in errors))

    def test_missing_hash_fails(self):
        text = "\n".join(
            f"{name}==1" for name in sorted({
                "google-api-python-client", "google-auth", "google-auth-httplib2"
            })
        )
        errors, _ = audit_lock_text(text)
        self.assertTrue(any("no valid SHA-256" in error for error in errors))

    def test_valid_required_packages_pass(self):
        digest = "b" * 64
        text = "\n".join(
            f"{name}==1.0 --hash=sha256:{digest}"
            for name in sorted({
                "google-api-python-client", "google-auth", "google-auth-httplib2"
            })
        )
        errors, packages = audit_lock_text(text)
        self.assertEqual(errors, [])
        self.assertEqual(len(packages), 3)


if __name__ == "__main__":
    unittest.main()
