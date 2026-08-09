#!/usr/bin/env python3
"""Verify that interactive tool pages remain useful and indexable without JavaScript."""

from html.parser import HTMLParser
from pathlib import Path
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL_ROOT = ROOT / "tools"
MIN_VISIBLE_WORDS = 400
MIN_H2S = 3
MIN_FAQS = 3
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’.-][A-Za-z0-9]+)*")


class MainParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.main_depth = 0
        self.ignored_depth = 0
        self.h1_count = 0
        self.h2_count = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.main_depth += 1
            return
        if not self.main_depth:
            return
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        if self.ignored_depth:
            return
        if tag == "h1":
            self.h1_count += 1
        elif tag == "h2":
            self.h2_count += 1

    def handle_data(self, data):
        if self.main_depth and not self.ignored_depth:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
            return
        if tag == "main" and self.main_depth:
            self.main_depth -= 1


def main():
    paths = sorted(TOOL_ROOT.glob("*/index.html"))
    errors = []
    counts = {}

    if len(paths) != 10:
        errors.append(f"expected 10 interactive tools, found {len(paths)}")

    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        parser = MainParser()
        parser.feed(source)
        word_count = len(WORD_RE.findall(" ".join(parser.parts)))
        counts[relative] = word_count

        if word_count < MIN_VISIBLE_WORDS:
            errors.append(
                f"{relative}: only {word_count} visible main words "
                f"(minimum {MIN_VISIBLE_WORDS})"
            )
        if parser.h1_count != 1:
            errors.append(f"{relative}: expected 1 h1, found {parser.h1_count}")
        if parser.h2_count < MIN_H2S:
            errors.append(f"{relative}: only {parser.h2_count} h2 headings")
        if "<noscript>" not in source:
            errors.append(f"{relative}: missing useful no-JavaScript fallback")
        if not re.search(r"stay in this browser|runs? in your browser", source, re.I):
            errors.append(f"{relative}: missing browser-local privacy disclosure")
        if 'class="surface-card tool-result"' in source and (
            '<script src="../../assets/result-actions.js" defer></script>' not in source
        ):
            errors.append(f"{relative}: result tool is missing local copy and print actions")

        faq = re.search(r'<ul class="faq-list">(.*?)</ul>', source, re.DOTALL)
        faq_count = len(re.findall(r"<li\b", faq.group(1))) if faq else 0
        if faq_count < MIN_FAQS:
            errors.append(f"{relative}: only {faq_count} visible FAQ items")

        structured_types = []
        for raw in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL
        ):
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                structured_types.append(item.get("@type"))
        if "WebApplication" not in structured_types:
            errors.append(f"{relative}: missing WebApplication structured data")

    if counts:
        thinnest = min(counts, key=counts.get)
        fullest = max(counts, key=counts.get)
        print(
            f"Audited {len(counts)} tools: {counts[thinnest]}–{counts[fullest]} "
            "visible main words."
        )
        print(f"Shortest: {thinnest}; longest: {fullest}.")

    if errors:
        print("Tool quality audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Tool quality audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
