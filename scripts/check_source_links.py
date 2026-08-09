#!/usr/bin/env python3
"""Check unique external article sources and fail only on confirmed dead links."""

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT / "articles"
USER_AGENT = (
    "Mozilla/5.0 (compatible; DishwasherCareLab/1.0; "
    "+https://dishwashercarehub.com/contact/)"
)
BLOCKED_OR_TRANSIENT = {401, 403, 408, 425, 429, 500, 502, 503, 504}
CONFIRMED_DEAD = {404, 410}


class SourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        parsed = urlparse(href)
        if (
            parsed.scheme == "https"
            and parsed.netloc
            and parsed.netloc != "dishwashercarehub.com"
        ):
            self.urls.append(href)


def source_urls(root=ARTICLE_ROOT):
    urls = set()
    for path in sorted(root.glob("*/index.html")):
        parser = SourceParser()
        parser.feed(path.read_text(encoding="utf-8"))
        urls.update(parser.urls)
    return sorted(urls)


def classify_status(status):
    if 200 <= status < 400:
        return "healthy"
    if status in CONFIRMED_DEAD:
        return "dead"
    if status in BLOCKED_OR_TRANSIENT:
        return "unverified"
    return "unverified"


def check_url(url, timeout=25):
    try:
        result = subprocess.run(
            [
                "curl",
                "--proto",
                "=https",
                "--location",
                "--max-redirs",
                "5",
                "--connect-timeout",
                "10",
                "--max-time",
                str(timeout),
                "--silent",
                "--show-error",
                "--output",
                "/dev/null",
                "--write-out",
                "%{http_code}",
                "--user-agent",
                USER_AGENT,
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        return url, "unverified", str(error)[:160]
    try:
        status = int(result.stdout.strip())
    except ValueError:
        detail = result.stderr.strip() or f"curl exit {result.returncode}"
        return url, "unverified", detail[:160]
    if result.returncode and status == 0:
        detail = result.stderr.strip() or f"curl exit {result.returncode}"
        return url, "unverified", detail[:160]
    return url, classify_status(status), f"HTTP {status}"


def main():
    urls = source_urls()
    if not urls:
        print("Source link check failed: no external article sources found", file=sys.stderr)
        return 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check_url, urls))
    dead = [result for result in results if result[1] == "dead"]
    unverified = [result for result in results if result[1] == "unverified"]
    healthy = len(results) - len(dead) - len(unverified)
    for url, _, detail in dead:
        print(f"DEAD {detail}: {url}", file=sys.stderr)
    for url, _, detail in unverified:
        print(f"UNVERIFIED {detail}: {url}")
    print(
        f"Checked {len(results)} unique official sources: {healthy} healthy, "
        f"{len(unverified)} blocked/transient, {len(dead)} confirmed dead."
    )
    return 1 if dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
