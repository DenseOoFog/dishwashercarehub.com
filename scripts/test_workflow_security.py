#!/usr/bin/env python3

import unittest

from audit_workflow_security import action_references, audit_action_reference


class WorkflowSecurityTests(unittest.TestCase):
    def test_full_sha_from_approved_owner_passes(self):
        self.assertIsNone(
            audit_action_reference(
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
            )
        )

    def test_moving_tag_fails(self):
        self.assertIn("full 40-character", audit_action_reference("actions/checkout@v7"))

    def test_unapproved_owner_fails(self):
        self.assertIn(
            "not approved",
            audit_action_reference(
                "unknown/action@3d3c42e5aac5ba805825da76410c181273ba90b1"
            ),
        )

    def test_local_action_passes(self):
        self.assertIsNone(audit_action_reference("./.github/actions/local"))

    def test_finds_shorthand_and_named_step_references(self):
        workflow = """
        steps:
          - uses: actions/checkout@abc
          - name: Set up Python
            uses: actions/setup-python@def # version
        """
        self.assertEqual(
            action_references(workflow),
            ["actions/checkout@abc", "actions/setup-python@def"],
        )


if __name__ == "__main__":
    unittest.main()
