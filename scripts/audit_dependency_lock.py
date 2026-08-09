#!/usr/bin/env python3
"""Validate the hash-locked dependencies used by the credentialed GSC workflow."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = ROOT / "requirements-gsc.lock"
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "gsc_fetch.yml"
EXPECTED_INSTALL = (
    "python -m pip install --require-hashes --only-binary=:all: "
    "-r requirements-gsc.lock"
)
REQUIRED_PACKAGES = {
    "google-api-python-client",
    "google-auth",
    "google-auth-httplib2",
}


def logical_requirements(text: str):
    entries = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        continuing = line.endswith("\\")
        if continuing:
            line = line[:-1].strip()
        current = f"{current} {line}".strip()
        if not continuing:
            entries.append(current)
            current = ""
    if current:
        entries.append(current)
    return entries


def audit_lock_text(text: str):
    errors = []
    packages = set()
    for entry in logical_requirements(text):
        requirement = entry.split()[0]
        if "==" not in requirement:
            errors.append(f"dependency is not exactly version-pinned: {requirement}")
            continue
        package, version = requirement.split("==", 1)
        packages.add(package.lower().replace("_", "-"))
        if not version:
            errors.append(f"dependency has an empty version: {package}")
        if not re.search(r"(?:^|\s)--hash=sha256:[0-9a-f]{64}(?:\s|$)", entry):
            errors.append(f"dependency has no valid SHA-256 hash: {requirement}")
    missing = REQUIRED_PACKAGES - packages
    if missing:
        errors.append(f"required top-level packages are missing: {', '.join(sorted(missing))}")
    if not packages:
        errors.append("dependency lock contains no packages")
    return errors, packages


def main():
    errors, packages = audit_lock_text(LOCK_FILE.read_text(encoding="utf-8"))
    workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
    if EXPECTED_INSTALL not in workflow:
        errors.append("GSC workflow does not install the lock with hashes and binary-only mode")
    if errors:
        print("Dependency lock audit failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        f"Dependency lock audit passed: {len(packages)} exact packages have "
        "SHA-256 hashes and the GSC workflow enforces them."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
