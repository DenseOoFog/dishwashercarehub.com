#!/usr/bin/env python3
"""Validate and optionally submit canonical sitemap URLs through IndexNow."""

from argparse import ArgumentParser
from datetime import date, timedelta
from pathlib import Path
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
HOST = "dishwashercarehub.com"
BASE_URL = f"https://{HOST}"
INDEXNOW_KEY = "3c65545768a3f277e57c54d66b2dacbe"
KEY_PATH = ROOT / f"{INDEXNOW_KEY}.txt"
KEY_URL = f"{BASE_URL}/{INDEXNOW_KEY}.txt"
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
SITEMAP_PATH = ROOT / "sitemap.xml"
NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def read_key():
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    if key != INDEXNOW_KEY:
        raise ValueError("IndexNow key file does not contain the configured key")
    if not 8 <= len(key) <= 128 or not re.fullmatch(r"[A-Za-z0-9-]+", key):
        raise ValueError("IndexNow key does not satisfy the protocol format")
    return key


def sitemap_records(path=SITEMAP_PATH):
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError(f"cannot read sitemap: {error}") from error

    records = []
    for element in root.findall(f"{NAMESPACE}url"):
        loc = element.findtext(f"{NAMESPACE}loc", "").strip()
        lastmod_text = element.findtext(f"{NAMESPACE}lastmod", "").strip()
        if not loc or not lastmod_text:
            raise ValueError("every sitemap URL must include loc and lastmod")
        parsed = urlparse(loc)
        if parsed.scheme != "https" or parsed.netloc != HOST or parsed.query or parsed.fragment:
            raise ValueError(f"non-canonical IndexNow URL: {loc}")
        try:
            modified = date.fromisoformat(lastmod_text)
        except ValueError as error:
            raise ValueError(f"invalid sitemap lastmod for {loc}: {lastmod_text}") from error
        records.append((loc, modified))

    urls = [loc for loc, _ in records]
    if not records or len(urls) != len(set(urls)):
        raise ValueError("sitemap must contain unique canonical URLs")
    if len(records) > 10_000:
        raise ValueError("IndexNow accepts at most 10,000 URLs per request")
    return records


def select_urls(records, since_days=None, today=None):
    if since_days is None:
        return [loc for loc, _ in records]
    if since_days < 0:
        raise ValueError("since-days must be zero or greater")
    cutoff = (today or date.today()) - timedelta(days=since_days)
    return [loc for loc, modified in records if modified >= cutoff]


def payload(urls, key):
    return {
        "host": HOST,
        "key": key,
        "keyLocation": KEY_URL,
        "urlList": urls,
    }


def submit(endpoint, body, timeout=30):
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    request = Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "DishwasherCareLab-IndexNow/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            response_body = response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"IndexNow returned HTTP {error.code}: {response_body[:500]}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"IndexNow request failed: {error}") from error
    if status not in {200, 202}:
        raise RuntimeError(f"IndexNow returned unexpected HTTP {status}: {response_body[:500]}")
    return status


def url_categories(urls):
    return {
        "articles": sum("/articles/" in url for url in urls),
        "tools": sum("/tools/" in url for url in urls),
        "other": sum(
            "/articles/" not in url and "/tools/" not in url for url in urls
        ),
    }


def github_summary(urls, endpoint, since_days=None, status=None):
    categories = url_categories(urls)
    mode = "all sitemap URLs" if since_days is None else f"lastmod within {since_days} days"
    result = "dry run" if status is None else f"accepted (HTTP {status})"
    return "\n".join(
        [
            "## IndexNow submission",
            "",
            f"- Result: **{result}**",
            f"- Selection: **{mode}**",
            f"- Submitted: **{len(urls)} canonical URLs**",
            (
                f"- Coverage: **{categories['articles']} articles**, "
                f"**{categories['tools']} tool URLs**, **{categories['other']} other pages**"
            ),
            f"- Endpoint: `{endpoint}`",
            "- Source of truth: `sitemap.xml`",
            "",
        ]
    )


def write_github_summary(content):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as summary_file:
        summary_file.write(content)


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--submit", action="store_true", help="send the request")
    parser.add_argument(
        "--since-days",
        type=int,
        help="include only URLs whose sitemap lastmod is within this many days",
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args(argv)

    try:
        key = read_key()
        urls = select_urls(sitemap_records(), args.since_days)
        body = payload(urls, key)
        if not urls:
            print("No recently modified canonical URLs to submit.")
            write_github_summary(github_summary(urls, args.endpoint, args.since_days))
            return 0
        if not args.submit:
            print(
                f"IndexNow dry run passed for {len(urls)} canonical URLs; "
                f"key location: {KEY_URL}"
            )
            write_github_summary(github_summary(urls, args.endpoint, args.since_days))
            return 0
        status = submit(args.endpoint, body)
        print(f"IndexNow accepted {len(urls)} canonical URLs with HTTP {status}.")
        write_github_summary(
            github_summary(urls, args.endpoint, args.since_days, status)
        )
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"IndexNow submission failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
