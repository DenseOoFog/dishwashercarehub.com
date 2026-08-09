#!/usr/bin/env python3
"""Fail CI when generated site files contain known corruption or broken local links."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(ROOT.glob("**/*.html"))
BAD_PATTERNS = {
    "repeated line-number prefixes": re.compile(r"^\s*(?:\d+\|\s*){2,}", re.MULTILINE),
    "literal output truncation": re.compile(r"\[truncated\]", re.IGNORECASE),
    "injected Chinese template text": re.compile(r"解决方法和步骤"),
    "HTML link inside title": re.compile(r"<title[^>]*>[^\n]*<a\b", re.IGNORECASE),
    "HTML link inside meta description": re.compile(
        r"<meta[^>]+name=[\"']description[\"'][^\n]*<a\b", re.IGNORECASE
    ),
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchor_links = []
        self.canonical = None
        self.json_ld = []
        self._json_buffer = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"a", "link", "script", "img"}:
            target = values.get("href") or values.get("src")
            if target:
                self.links.append(target)
        if tag == "a" and values.get("href"):
            self.anchor_links.append(values["href"])
        if tag == "link" and "canonical" in values.get("rel", "").lower():
            self.canonical = values.get("href")
        if tag == "script" and values.get("type") == "application/ld+json":
            self._json_buffer = []

    def handle_data(self, data):
        if self._json_buffer is not None:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer))
            self._json_buffer = None


def local_target(source: Path, value: str):
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith(("#", "mailto:", "tel:")):
        return None
    raw = parsed.path
    if not raw:
        return None
    target = (ROOT / raw.lstrip("/")) if raw.startswith("/") else (source.parent / raw)
    if raw.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target.resolve()


errors = []
for path in HTML_FILES:
    text = path.read_text(encoding="utf-8")
    if path.name == "index.html":
        for marker, expected in (("<!doctype html>", 1), ("</html>", 1), ("<footer", 1)):
            count = text.lower().count(marker)
            if count != expected:
                errors.append(
                    f"{path.relative_to(ROOT)}: expected {expected} occurrence of "
                    f"{marker}, found {count}"
                )
    for label, pattern in BAD_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)}: {label}")
    parser = LinkParser()
    parser.feed(text)
    if path.parent.parent.name == "articles" and parser.canonical:
        canonical = parser.canonical.rstrip("/")
        for link in parser.anchor_links:
            if urljoin(parser.canonical, link).rstrip("/") == canonical:
                errors.append(f"{path.relative_to(ROOT)}: self-referential article link {link}")
    for index, payload in enumerate(parser.json_ld, start=1):
        try:
            json.loads(payload)
        except json.JSONDecodeError as error:
            errors.append(
                f"{path.relative_to(ROOT)}: invalid JSON-LD block {index} "
                f"at line {error.lineno}, column {error.colno}"
            )
    for link in parser.links:
        target = local_target(path, link)
        if target and not target.exists():
            errors.append(f"{path.relative_to(ROOT)}: broken local link {link}")

if errors:
    print("Site validation failed:")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)

print(f"Validated {len(HTML_FILES)} HTML files: no known corruption or broken local links.")
