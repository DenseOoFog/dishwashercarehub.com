#!/usr/bin/env python3
"""Fail CI when a workflow uses an unpinned or unapproved external action."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
USES_PATTERN = re.compile(r"^\s*-\s+uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
APPROVED_OWNERS = {"actions"}


def audit_action_reference(reference: str):
    if reference.startswith("./"):
        return None
    if "@" not in reference:
        return "external action has no revision"
    repository, revision = reference.rsplit("@", 1)
    owner = repository.split("/", 1)[0].lower()
    if owner not in APPROVED_OWNERS:
        return f"action owner {owner!r} is not approved"
    if not FULL_SHA.fullmatch(revision):
        return "external action must be pinned to a full 40-character commit SHA"
    return None


def main():
    errors = []
    references = []
    for workflow in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        text = workflow.read_text(encoding="utf-8")
        for reference in USES_PATTERN.findall(text):
            references.append(reference)
            error = audit_action_reference(reference)
            if error:
                errors.append(f"{workflow.relative_to(ROOT)}: {reference}: {error}")
    if not references:
        errors.append("no GitHub Actions references found")
    if errors:
        print("Workflow security audit failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        f"Workflow security audit passed: {len(references)} action references "
        "use approved owners and immutable commit SHAs."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
