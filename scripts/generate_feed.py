#!/usr/bin/env python3
"""Generate a deterministic Atom 1.0 feed from published article metadata."""

from html.parser import HTMLParser
from pathlib import Path
import argparse
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "feed.xml"
ATOM = "http://www.w3.org/2005/Atom"
SITE_URL = "https://dishwashercarehub.com/"
FEED_URL = f"{SITE_URL}feed.xml"


class ArticleMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = None
        self.description = None
        self.json_ld = []
        self._json_buffer = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link" and "canonical" in values.get("rel", "").lower():
            self.canonical = values.get("href")
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content")
        if tag == "script" and values.get("type") == "application/ld+json":
            self._json_buffer = []

    def handle_data(self, data):
        if self._json_buffer is not None:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer))
            self._json_buffer = None


def article_metadata(path):
    parser = ArticleMetadataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    article = None
    for payload in parser.json_ld:
        parsed = json.loads(payload)
        candidates = parsed.get("@graph", []) if isinstance(parsed, dict) else []
        if isinstance(parsed, dict):
            candidates = [parsed, *candidates]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") in {
                "Article",
                "BlogPosting",
                "TechArticle",
            }:
                article = candidate
                break
        if article:
            break
    required = {
        "canonical": parser.canonical,
        "description": parser.description,
        "headline": article.get("headline") if article else None,
        "datePublished": article.get("datePublished") if article else None,
        "dateModified": article.get("dateModified") if article else None,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"{path.relative_to(ROOT)} missing feed metadata: {missing}")
    return required


def atom_timestamp(day):
    return f"{day}T00:00:00Z"


def build_feed():
    articles = [
        article_metadata(path)
        for path in sorted((ROOT / "articles").glob("*/index.html"))
    ]
    articles.sort(key=lambda item: (item["datePublished"], item["canonical"]), reverse=True)
    if not articles:
        raise ValueError("no published articles found")

    ET.register_namespace("", ATOM)
    feed = ET.Element(f"{{{ATOM}}}feed", {"{http://www.w3.org/XML/1998/namespace}lang": "en"})
    ET.SubElement(feed, f"{{{ATOM}}}title").text = "Dishwasher Care Lab — New and Updated Guides"
    ET.SubElement(feed, f"{{{ATOM}}}subtitle").text = (
        "Maintenance-first dishwasher troubleshooting, cleaning, and household decision guides."
    )
    ET.SubElement(feed, f"{{{ATOM}}}id").text = FEED_URL
    ET.SubElement(feed, f"{{{ATOM}}}updated").text = atom_timestamp(
        max(item["dateModified"] for item in articles)
    )
    ET.SubElement(
        feed,
        f"{{{ATOM}}}link",
        {"rel": "self", "type": "application/atom+xml", "href": FEED_URL},
    )
    ET.SubElement(
        feed,
        f"{{{ATOM}}}link",
        {"rel": "alternate", "type": "text/html", "href": SITE_URL},
    )
    author = ET.SubElement(feed, f"{{{ATOM}}}author")
    ET.SubElement(author, f"{{{ATOM}}}name").text = "Dishwasher Care Lab editorial team"
    ET.SubElement(author, f"{{{ATOM}}}uri").text = f"{SITE_URL}about/"
    ET.SubElement(feed, f"{{{ATOM}}}rights").text = "Copyright Dishwasher Care Lab"
    ET.SubElement(feed, f"{{{ATOM}}}generator").text = "Dishwasher Care Lab feed generator"

    for item in articles:
        entry = ET.SubElement(feed, f"{{{ATOM}}}entry")
        ET.SubElement(entry, f"{{{ATOM}}}title").text = item["headline"]
        ET.SubElement(entry, f"{{{ATOM}}}id").text = item["canonical"]
        ET.SubElement(
            entry,
            f"{{{ATOM}}}link",
            {"rel": "alternate", "type": "text/html", "href": item["canonical"]},
        )
        ET.SubElement(entry, f"{{{ATOM}}}published").text = atom_timestamp(
            item["datePublished"]
        )
        ET.SubElement(entry, f"{{{ATOM}}}updated").text = atom_timestamp(
            item["dateModified"]
        )
        ET.SubElement(entry, f"{{{ATOM}}}summary", {"type": "text"}).text = item[
            "description"
        ]

    ET.indent(feed, space="  ")
    return ET.tostring(feed, encoding="utf-8", xml_declaration=True) + b"\n"


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "--check", action="store_true", help="fail if feed.xml is not current"
    )
    args = argument_parser.parse_args()
    try:
        generated = build_feed()
    except (ValueError, json.JSONDecodeError) as error:
        print(f"Feed generation failed: {error}")
        return 1
    if args.check:
        current = OUTPUT.read_bytes() if OUTPUT.exists() else b""
        if current != generated:
            print("feed.xml is stale; run python scripts/generate_feed.py")
            return 1
        print("feed.xml matches all published article metadata.")
        return 0
    OUTPUT.write_bytes(generated)
    print(f"Generated feed.xml with {generated.count(b'<entry>')} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
