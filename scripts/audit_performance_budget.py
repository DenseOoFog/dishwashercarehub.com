#!/usr/bin/env python3
"""Enforce a small, repeatable first-party transfer budget for every HTML page."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGE_BUDGET_BYTES = 100_000
HTML_BUDGET_BYTES = 70_000
CSS_BUDGET_BYTES = 25_000
JS_BUDGET_BYTES = 25_000
ALLOWED_EXTERNAL_SCRIPTS = {
    "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
}


@dataclass
class PageAssets:
    stylesheets: set[str] = field(default_factory=set)
    scripts: set[str] = field(default_factory=set)
    images: set[str] = field(default_factory=set)
    external_script_errors: list[str] = field(default_factory=list)


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = PageAssets()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link" and "stylesheet" in values.get("rel", "").lower():
            href = values.get("href")
            if href:
                self.assets.stylesheets.add(href)
        elif tag == "img" and values.get("src"):
            self.assets.images.add(values["src"])
        elif tag == "script" and values.get("src"):
            src = values["src"]
            parsed = urlparse(src)
            if parsed.scheme or parsed.netloc:
                origin_path = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if origin_path not in ALLOWED_EXTERNAL_SCRIPTS:
                    self.assets.external_script_errors.append(
                        f"unexpected external script {src}"
                    )
                if "async" not in values and "defer" not in values:
                    self.assets.external_script_errors.append(
                        f"render-blocking external script {src}"
                    )
            else:
                self.assets.scripts.add(src)
                if "async" not in values and "defer" not in values:
                    self.assets.external_script_errors.append(
                        f"render-blocking local script {src}"
                    )


def resolve_local(page: Path, value: str, root: Path = ROOT) -> Path | None:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("data:"):
        return None
    raw = parsed.path
    if not raw:
        return None
    return ((root / raw.lstrip("/")) if raw.startswith("/") else (page.parent / raw)).resolve()


def audit_page(page: Path, root: Path = ROOT) -> tuple[list[str], int]:
    errors = []
    parser = AssetParser()
    parser.feed(page.read_text(encoding="utf-8"))
    relative = page.relative_to(root)
    errors.extend(f"{relative}: {error}" for error in parser.assets.external_script_errors)

    html_size = page.stat().st_size
    if html_size > HTML_BUDGET_BYTES:
        errors.append(f"{relative}: HTML is {html_size} bytes (budget {HTML_BUDGET_BYTES})")

    total = html_size
    seen = set()
    for kind, references, budget in (
        ("CSS", parser.assets.stylesheets, CSS_BUDGET_BYTES),
        ("JavaScript", parser.assets.scripts, JS_BUDGET_BYTES),
        ("image", parser.assets.images, PAGE_BUDGET_BYTES),
    ):
        for reference in references:
            target = resolve_local(page, reference, root)
            if target is None or target in seen:
                continue
            seen.add(target)
            if not target.is_file():
                errors.append(f"{relative}: missing local {kind} asset {reference}")
                continue
            size = target.stat().st_size
            total += size
            if kind in {"CSS", "JavaScript"} and size > budget:
                errors.append(
                    f"{relative}: {kind} asset {reference} is {size} bytes (budget {budget})"
                )
    if total > PAGE_BUDGET_BYTES:
        errors.append(
            f"{relative}: first-party page weight is {total} bytes (budget {PAGE_BUDGET_BYTES})"
        )
    return errors, total


def main() -> int:
    errors = []
    weights = []
    pages = sorted(ROOT.glob("**/*.html"))
    for page in pages:
        page_errors, weight = audit_page(page)
        errors.extend(page_errors)
        weights.append((weight, page.relative_to(ROOT)))
    if errors:
        print("Performance budget audit failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    largest_weight, largest_page = max(weights)
    print(
        f"Performance budget passed: {len(pages)} pages; largest first-party load "
        f"is {largest_weight} bytes ({largest_page}); budget={PAGE_BUDGET_BYTES} bytes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
