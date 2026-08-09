#!/usr/bin/env python3
"""Fail CI when generated site files contain known corruption or broken local links."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(ROOT.glob("**/*.html"))
BAD_PATTERNS = {
    "repeated line-number prefixes": re.compile(r"^\s*(?:\d+\|\s*){2,}", re.MULTILINE),
    "literal output truncation": re.compile(r"\[truncated\]", re.IGNORECASE),
    "injected Chinese template text": re.compile(r"解决方法和步骤"),
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"a", "link", "script", "img"}:
            target = values.get("href") or values.get("src")
            if target:
                self.links.append(target)


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
    for label, pattern in BAD_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)}: {label}")
    parser = LinkParser()
    parser.feed(text)
    for link in parser.links:
        target = local_target(path, link)
        if target and not target.exists():
            errors.append(f"{path.relative_to(ROOT)}: broken local link {link}")

if errors:
    print("Site validation failed:")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)

print(f"Validated {len(HTML_FILES)} HTML files: no known corruption or broken local links.")
