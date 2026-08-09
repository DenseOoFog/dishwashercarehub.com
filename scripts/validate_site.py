#!/usr/bin/env python3
"""Fail CI when generated site files contain known corruption or broken local links."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(ROOT.glob("**/*.html"))
ADSENSE_SCRIPT_URL = (
    "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?"
    "client=ca-pub-9156049827002127"
)
BAD_PATTERNS = {
    "repeated line-number prefixes": re.compile(r"^\s*(?:\d+\|\s*){2,}", re.MULTILINE),
    "literal output truncation": re.compile(r"\[truncated\]", re.IGNORECASE),
    "injected Chinese template text": re.compile(r"解决方法和步骤"),
    "published writing instruction": re.compile(
        r"\bExplain dishwasher .+? in plain language|"
        r"\bKeep the advice bounded to user-safe",
        re.IGNORECASE,
    ),
    "generic placeholder FAQ": re.compile(
        r"How often should I handle dishwasher .+?\?",
        re.IGNORECASE,
    ),
    "generic placeholder reference": re.compile(
        r"<li>\s*(?:manufacturer documentation|appliance care guidance|"
        r"routine household maintenance guidance|product label directions)\s*</li>",
        re.IGNORECASE,
    ),
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
        self.title_parts = []
        self.meta_description = None
        self.social_meta = defaultdict(list)
        self.json_ld = []
        self._json_buffer = None
        self._in_title = False

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
        if tag == "title":
            self._in_title = True
        if (
            tag == "meta"
            and values.get("name", "").lower() == "description"
            and values.get("content")
        ):
            self.meta_description = values["content"].strip()
        if tag == "meta" and values.get("content"):
            property_name = values.get("property", "").lower()
            meta_name = values.get("name", "").lower()
            social_name = property_name or (
                meta_name if meta_name.startswith("twitter:") else ""
            )
            if social_name:
                self.social_meta[social_name].append(values["content"].strip())
        if tag == "script" and values.get("type") == "application/ld+json":
            self._json_buffer = []

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._json_buffer is not None:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
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
canonical_pages = set()
page_records = {}
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
        adsense_count = text.count(ADSENSE_SCRIPT_URL)
        if adsense_count != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one AdSense script, found {adsense_count}"
            )
        head_markup = text.split("</head>", 1)[0]
        if ADSENSE_SCRIPT_URL not in head_markup:
            errors.append(
                f"{path.relative_to(ROOT)}: AdSense script is not inside head"
            )
        if "footer-ads-loader" in text:
            errors.append(
                f"{path.relative_to(ROOT)}: obsolete deferred AdSense loader remains"
            )
    for label, pattern in BAD_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)}: {label}")
    if "fonts.googleapis.com" in text or "fonts.gstatic.com" in text:
        errors.append(
            f"{path.relative_to(ROOT)}: render-blocking third-party font dependency"
        )
    parser = LinkParser()
    parser.feed(text)
    if path.name == "index.html" and parser.canonical:
        canonical_url = parser.canonical.rstrip("/") + "/"
        canonical_pages.add(canonical_url)
        if canonical_url in page_records:
            errors.append(
                f"{path.relative_to(ROOT)}: duplicate canonical also used by "
                f"{page_records[canonical_url]['path'].relative_to(ROOT)}"
            )
        page_records[canonical_url] = {
            "path": path,
            "title": "".join(parser.title_parts).strip(),
            "description": parser.meta_description or "",
            "links": parser.anchor_links,
            "social_meta": parser.social_meta,
        }
    if path.parent.parent.name == "articles" and parser.canonical:
        canonical = parser.canonical.rstrip("/")
        for link in parser.anchor_links:
            if urljoin(parser.canonical, link).rstrip("/") == canonical:
                errors.append(f"{path.relative_to(ROOT)}: self-referential article link {link}")
    structured_objects = []
    for index, payload in enumerate(parser.json_ld, start=1):
        try:
            parsed_payload = json.loads(payload)
            if isinstance(parsed_payload, dict) and isinstance(
                parsed_payload.get("@graph"), list
            ):
                structured_objects.extend(parsed_payload["@graph"])
            else:
                structured_objects.append(parsed_payload)
        except json.JSONDecodeError as error:
            errors.append(
                f"{path.relative_to(ROOT)}: invalid JSON-LD block {index} "
                f"at line {error.lineno}, column {error.colno}"
            )
    if path.parent.parent.name == "articles":
        external_sources = []
        for link in parser.anchor_links:
            parsed_link = urlparse(link)
            if (
                parsed_link.scheme == "https"
                and parsed_link.netloc
                and parsed_link.netloc != "dishwashercarehub.com"
            ):
                external_sources.append(link)
        if not external_sources:
            errors.append(
                f"{path.relative_to(ROOT)}: article has no HTTPS external source link"
            )
        if not re.search(
            r"<h2>(?:Sources and scope notes|References and fact-check notes)</h2>",
            text,
        ):
            errors.append(
                f"{path.relative_to(ROOT)}: article has no visible source section"
            )
        meta_matches = re.findall(
            r'<p class="article-meta">Published <time datetime="(\d{4}-\d{2}-\d{2})">'
            r'.+?</time> · Updated <time datetime="(\d{4}-\d{2}-\d{2})">'
            r'.+?</time> · By <a href="/about/">Dishwasher Care Lab editorial team</a></p>',
            text,
        )
        if len(meta_matches) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one complete visible article byline"
            )
        elif parser.social_meta.get("article:published_time") != [meta_matches[0][0]]:
            errors.append(
                f"{path.relative_to(ROOT)}: article:published_time must match the visible date"
            )
        if len(meta_matches) == 1 and parser.social_meta.get(
            "article:modified_time"
        ) != [meta_matches[0][1]]:
            errors.append(
                f"{path.relative_to(ROOT)}: article:modified_time must match the visible date"
            )
        article_objects = [
            item
            for item in structured_objects
            if isinstance(item, dict)
            and item.get("@type") in {"Article", "BlogPosting", "TechArticle"}
        ]
        if len(article_objects) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one Article JSON-LD object"
            )
        elif len(meta_matches) == 1:
            published, modified = meta_matches[0]
            article_object = article_objects[0]
            if article_object.get("datePublished") != published:
                errors.append(
                    f"{path.relative_to(ROOT)}: visible and structured publication dates differ"
                )
            if article_object.get("dateModified") != modified:
                errors.append(
                    f"{path.relative_to(ROOT)}: visible and structured update dates differ"
                )
            if published > modified:
                errors.append(
                    f"{path.relative_to(ROOT)}: publication date is after update date"
                )
            expected_author = {
                "@type": "Organization",
                "name": "Dishwasher Care Lab",
                "url": "https://dishwashercarehub.com/about/",
            }
            if article_object.get("author") != expected_author:
                errors.append(
                    f"{path.relative_to(ROOT)}: structured author does not match visible byline"
                )
    for link in parser.links:
        target = local_target(path, link)
        if target and not target.exists():
            errors.append(f"{path.relative_to(ROOT)}: broken local link {link}")

for field in ("title", "description"):
    values = defaultdict(list)
    for canonical_url, record in page_records.items():
        if not record[field]:
            errors.append(
                f"{record['path'].relative_to(ROOT)}: missing {field}"
            )
        else:
            values[record[field]].append(record["path"])
    for value, paths in values.items():
        if len(paths) > 1:
            joined_paths = ", ".join(str(path.relative_to(ROOT)) for path in paths)
            errors.append(f"duplicate {field} across pages: {value!r} ({joined_paths})")

for canonical_url, record in page_records.items():
    path = record["path"]
    social_meta = record["social_meta"]
    is_article = path.parent.parent.name == "articles"
    expected_social_meta = {
        "og:type": "article" if is_article else "website",
        "og:site_name": "Dishwasher Care Lab",
        "og:title": record["title"],
        "og:description": record["description"],
        "og:url": canonical_url,
        "twitter:card": "summary",
        "twitter:title": record["title"],
        "twitter:description": record["description"],
    }
    for name, expected in expected_social_meta.items():
        if social_meta.get(name) != [expected]:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one {name} matching page metadata"
            )

incoming_links = defaultdict(set)
for source_url, record in page_records.items():
    for link in record["links"]:
        resolved = urlparse(urljoin(source_url, link))
        if resolved.scheme not in {"http", "https"} or not resolved.netloc:
            continue
        target_url = f"{resolved.scheme}://{resolved.netloc}{resolved.path.rstrip('/')}/"
        if target_url in page_records and target_url != source_url:
            incoming_links[target_url].add(source_url)
for canonical_url, record in page_records.items():
    if canonical_url == "https://dishwashercarehub.com/":
        continue
    if not incoming_links[canonical_url]:
        errors.append(
            f"{record['path'].relative_to(ROOT)}: orphaned canonical page has no internal link"
        )

sitemap_path = ROOT / "sitemap.xml"
try:
    sitemap_root = ET.parse(sitemap_path).getroot()
    sitemap_urls = {
        element.text.strip().rstrip("/") + "/"
        for element in sitemap_root.findall(
            "{http://www.sitemaps.org/schemas/sitemap/0.9}url/"
            "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
        )
        if element.text and element.text.strip()
    }
    for url in sorted(canonical_pages - sitemap_urls):
        errors.append(f"sitemap.xml: missing canonical page {url}")
    for url in sorted(sitemap_urls - canonical_pages):
        errors.append(f"sitemap.xml: URL has no canonical index page {url}")
except (ET.ParseError, OSError) as error:
    errors.append(f"sitemap.xml: invalid or unreadable XML ({error})")

vercel_path = ROOT / "vercel.json"
required_security_headers = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}
try:
    vercel_config = json.loads(vercel_path.read_text(encoding="utf-8"))
    configured_headers = {}
    for rule in vercel_config.get("headers", []):
        if rule.get("source") != "/(.*)":
            continue
        configured_headers.update(
            {
                header.get("key", "").lower(): header.get("value", "")
                for header in rule.get("headers", [])
            }
        )
    for key, expected in required_security_headers.items():
        if configured_headers.get(key) != expected:
            errors.append(
                f"vercel.json: missing or incorrect security header {key}={expected}"
            )
except (json.JSONDecodeError, OSError) as error:
    errors.append(f"vercel.json: invalid or unreadable JSON ({error})")

privacy_text = (ROOT / "privacy" / "index.html").read_text(encoding="utf-8")
required_privacy_disclosures = {
    "Google partner data-use link": "https://policies.google.com/technologies/partner-sites",
    "Google advertising settings": "https://adssettings.google.com/",
    "third-party advertising opt-out": "https://optout.aboutads.info/",
    "certified CMP disclosure": "Google-certified consent management platform",
    "privacy contact": "mailto:pqiswin1@gmail.com",
}
for label, required_text in required_privacy_disclosures.items():
    if required_text not in privacy_text:
        errors.append(f"privacy/index.html: missing {label}")

ads_txt_lines = [
    line.strip()
    for line in (ROOT / "ads.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
expected_ads_txt = "google.com, pub-9156049827002127, DIRECT, f08c47fec0942fa0"
if ads_txt_lines != [expected_ads_txt]:
    errors.append("ads.txt: publisher declaration is missing, duplicated, or malformed")

if errors:
    print("Site validation failed:")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)

print(f"Validated {len(HTML_FILES)} HTML files: no known corruption or broken local links.")
