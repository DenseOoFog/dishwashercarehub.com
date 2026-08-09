#!/usr/bin/env python3
"""Fail CI when generated site files contain known corruption or broken local links."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from datetime import date
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(ROOT.glob("**/*.html"))
FORBIDDEN_PUBLISHED_FILES = sorted(
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and any(
        path.name.endswith(suffix)
        for suffix in (".bak", ".bak2", ".orig", ".rej", ".tmp", "~")
    )
)
ADSENSE_SCRIPT_URL = (
    "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?"
    "client=ca-pub-9156049827002127"
)
ADS_TXT_RECORD = "google.com, pub-9156049827002127, DIRECT, f08c47fec0942fa0"
ORGANIZATION_ID = "https://dishwashercarehub.com/#organization"
WEBSITE_ID = "https://dishwashercarehub.com/#website"
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
    "unsafe universal dishwasher cleaning recipe": re.compile(
        r"two cups of white vinegar|hottest empty cycle|hottest cycle available",
        re.IGNORECASE,
    ),
    "unsafe live temperature check": re.compile(
        r"opening the door mid-wash|open(?:ing)? (?:a|the) (?:running )?dishwasher "
        r"to (?:feel|check) (?:the )?water",
        re.IGNORECASE,
    ),
    "unsupported universal water-heater adjustment": re.compile(
        r"adjust (?:your|the) (?:home )?water heater|"
        r"keep water temperature between 120 and 140 degrees",
        re.IGNORECASE,
    ),
    "unsupported fixed detergent dose": re.compile(
        r"about one tablespoon per load",
        re.IGNORECASE,
    ),
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchor_links = []
        self.canonical = None
        self.feed_links = []
        self.images = []
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
        if tag == "img":
            self.images.append(values)
        if tag == "a" and values.get("href"):
            self.anchor_links.append(values["href"])
        if tag == "link" and "canonical" in values.get("rel", "").lower():
            self.canonical = values.get("href")
        if (
            tag == "link"
            and "alternate" in values.get("rel", "").lower()
            and values.get("type", "").lower() == "application/atom+xml"
            and values.get("href")
        ):
            self.feed_links.append(values["href"])
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


errors = [
    f"{path.relative_to(ROOT)}: backup or editor-temporary file must not be published"
    for path in FORBIDDEN_PUBLISHED_FILES
]
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
    for image in parser.images:
        image_source = image.get("src", "<missing src>")
        if not image.get("alt", "").strip():
            errors.append(f"{path.relative_to(ROOT)}: image has missing or empty alt {image_source}")
        for dimension in ("width", "height"):
            value = image.get(dimension, "")
            if not value.isdigit() or int(value) <= 0:
                errors.append(
                    f"{path.relative_to(ROOT)}: image has invalid {dimension} {image_source}"
                )
        if image.get("loading") not in {"lazy", "eager"}:
            errors.append(f"{path.relative_to(ROOT)}: image has no loading strategy {image_source}")
        if image.get("decoding") != "async":
            errors.append(f"{path.relative_to(ROOT)}: image does not use async decoding {image_source}")
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
            "feed_links": parser.feed_links,
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
    if path == ROOT / "index.html":
        organization_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "Organization"
        ]
        website_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "WebSite"
        ]
        if len(organization_objects) != 1:
            errors.append("index.html: expected one Organization JSON-LD object")
        elif organization_objects[0] != {
            "@type": "Organization",
            "@id": ORGANIZATION_ID,
            "name": "Dishwasher Care Lab",
            "url": "https://dishwashercarehub.com/",
            "email": "pqiswin1@gmail.com",
        }:
            errors.append("index.html: Organization identity is incomplete or inconsistent")
        if len(website_objects) != 1:
            errors.append("index.html: expected one WebSite JSON-LD object")
        elif website_objects[0].get("publisher") != {"@id": ORGANIZATION_ID} or (
            website_objects[0].get("@id") != WEBSITE_ID
            or website_objects[0].get("url") != "https://dishwashercarehub.com/"
            or website_objects[0].get("name") != "Dishwasher Care Lab"
        ):
            errors.append("index.html: WebSite identity does not reference the publisher")
    if path == ROOT / "about" / "index.html":
        about_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "AboutPage"
        ]
        if len(about_objects) != 1:
            errors.append("about/index.html: expected one AboutPage JSON-LD object")
        elif (
            about_objects[0].get("url") != "https://dishwashercarehub.com/about/"
            or about_objects[0].get("mainEntity") != {"@id": ORGANIZATION_ID}
            or about_objects[0].get("isPartOf") != {"@id": WEBSITE_ID}
        ):
            errors.append("about/index.html: AboutPage does not reference the site identity")
    if path.parent.parent.name == "tools":
        application_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "WebApplication"
        ]
        if len(application_objects) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one WebApplication JSON-LD object"
            )
        else:
            application = application_objects[0]
            expected_url = parser.canonical.rstrip("/") + "/" if parser.canonical else ""
            required_values = {
                "url": expected_url,
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Any",
                "isAccessibleForFree": True,
                "provider": {"@id": ORGANIZATION_ID},
            }
            for key, expected in required_values.items():
                if application.get(key) != expected:
                    errors.append(
                        f"{path.relative_to(ROOT)}: WebApplication {key} is missing or inconsistent"
                    )
            if not application.get("name") or not application.get("description"):
                errors.append(
                    f"{path.relative_to(ROOT)}: WebApplication requires name and description"
                )
        breadcrumb_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "BreadcrumbList"
        ]
        if len(breadcrumb_objects) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one BreadcrumbList JSON-LD object"
            )
        elif len(application_objects) == 1:
            expected_items = [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": "https://dishwashercarehub.com/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "All Tools",
                    "item": "https://dishwashercarehub.com/tools/",
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": application_objects[0].get("name"),
                    "item": parser.canonical.rstrip("/") + "/" if parser.canonical else "",
                },
            ]
            if breadcrumb_objects[0].get("itemListElement") != expected_items:
                errors.append(
                    f"{path.relative_to(ROOT)}: breadcrumb hierarchy is incomplete or inconsistent"
                )
        article_links = {
            urlparse(urljoin(parser.canonical, link)).path
            for link in parser.anchor_links
            if parser.canonical
        }
        if not any(link.startswith("/articles/") for link in article_links):
            errors.append(
                f"{path.relative_to(ROOT)}: tool has no contextual link to an article"
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
        article_navigation = {
            urlparse(urljoin(parser.canonical, link)).path
            for link in parser.anchor_links
        }
        if "/tools/" not in article_navigation:
            errors.append(
                f"{path.relative_to(ROOT)}: article navigation has no All Tools link"
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
        if len(meta_matches) == 1:
            canonical_url = parser.canonical.rstrip("/") + "/"
            page_records[canonical_url]["article_published"] = meta_matches[0][0]
            page_records[canonical_url]["article_modified"] = meta_matches[0][1]
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
        faq_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "FAQPage"
        ]
        if len(faq_objects) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one FAQPage JSON-LD object"
            )
        else:
            questions = faq_objects[0].get("mainEntity")
            if not isinstance(questions, list) or len(questions) < 3:
                errors.append(
                    f"{path.relative_to(ROOT)}: FAQPage requires at least three questions"
                )
            else:
                for question in questions:
                    answer = question.get("acceptedAnswer", {}) if isinstance(question, dict) else {}
                    if (
                        not isinstance(question, dict)
                        or question.get("@type") != "Question"
                        or not str(question.get("name", "")).strip()
                        or not isinstance(answer, dict)
                        or answer.get("@type") != "Answer"
                        or not str(answer.get("text", "")).strip()
                        or str(answer.get("text", "")).strip()[-1:] not in ".!?"
                    ):
                        errors.append(
                            f"{path.relative_to(ROOT)}: FAQPage has an incomplete question or answer"
                        )
                        break
        breadcrumb_objects = [
            item for item in structured_objects
            if isinstance(item, dict) and item.get("@type") == "BreadcrumbList"
        ]
        if len(breadcrumb_objects) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: expected one BreadcrumbList JSON-LD object"
            )
        else:
            breadcrumb_items = breadcrumb_objects[0].get("itemListElement")
            expected_prefix = [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": "https://dishwashercarehub.com/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Articles",
                    "item": "https://dishwashercarehub.com/#latest-guides",
                },
            ]
            expected_url = parser.canonical.rstrip("/") + "/" if parser.canonical else ""
            if (
                not isinstance(breadcrumb_items, list)
                or len(breadcrumb_items) != 3
                or breadcrumb_items[:2] != expected_prefix
                or not isinstance(breadcrumb_items[2], dict)
                or breadcrumb_items[2].get("@type") != "ListItem"
                or breadcrumb_items[2].get("position") != 3
                or not str(breadcrumb_items[2].get("name", "")).strip()
                or breadcrumb_items[2].get("item") != expected_url
            ):
                errors.append(
                    f"{path.relative_to(ROOT)}: article breadcrumb hierarchy is incomplete or inconsistent"
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
    if record["feed_links"] != ["https://dishwashercarehub.com/feed.xml"]:
        errors.append(
            f"{path.relative_to(ROOT)}: expected one canonical Atom feed discovery link"
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

tool_canonical_urls = {
    canonical_url
    for canonical_url, record in page_records.items()
    if record["path"].parent.parent.name == "tools"
}
for hub_url in ("https://dishwashercarehub.com/", "https://dishwashercarehub.com/tools/"):
    hub_record = page_records.get(hub_url)
    hub_targets = {
        urlparse(urljoin(hub_url, link))._replace(fragment="").geturl().rstrip("/") + "/"
        for link in hub_record["links"]
    } if hub_record else set()
    for missing_tool in sorted(tool_canonical_urls - hub_targets):
        errors.append(
            f"{hub_record['path'].relative_to(ROOT) if hub_record else hub_url}: "
            f"missing direct tool link {missing_tool}"
        )

sitemap_path = ROOT / "sitemap.xml"
try:
    sitemap_root = ET.parse(sitemap_path).getroot()
    sitemap_namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    sitemap_urls = set()
    sitemap_lastmods = {}
    for url_element in sitemap_root.findall(f"{sitemap_namespace}url"):
        loc_elements = url_element.findall(f"{sitemap_namespace}loc")
        lastmod_elements = url_element.findall(f"{sitemap_namespace}lastmod")
        if len(loc_elements) != 1 or not loc_elements[0].text:
            errors.append("sitemap.xml: each URL requires exactly one non-empty loc")
            continue
        sitemap_url = loc_elements[0].text.strip().rstrip("/") + "/"
        if sitemap_url in sitemap_urls:
            errors.append(f"sitemap.xml: duplicate URL {sitemap_url}")
        sitemap_urls.add(sitemap_url)
        if len(lastmod_elements) != 1 or not lastmod_elements[0].text:
            errors.append(f"sitemap.xml: {sitemap_url} requires exactly one lastmod")
            continue
        lastmod_text = lastmod_elements[0].text.strip()
        try:
            lastmod_date = date.fromisoformat(lastmod_text)
            if lastmod_text != lastmod_date.isoformat():
                raise ValueError
            if lastmod_date > date.today():
                errors.append(f"sitemap.xml: future lastmod for {sitemap_url}")
        except ValueError:
            errors.append(
                f"sitemap.xml: invalid YYYY-MM-DD lastmod for {sitemap_url}"
            )
        sitemap_lastmods[sitemap_url] = lastmod_text
    for url in sorted(canonical_pages - sitemap_urls):
        errors.append(f"sitemap.xml: missing canonical page {url}")
    for url in sorted(sitemap_urls - canonical_pages):
        errors.append(f"sitemap.xml: URL has no canonical index page {url}")
    for canonical_url, record in page_records.items():
        article_modified = record.get("article_modified")
        if article_modified and sitemap_lastmods.get(canonical_url) != article_modified:
            errors.append(
                f"sitemap.xml: {canonical_url} lastmod does not match article update date"
            )
except (ET.ParseError, OSError) as error:
    errors.append(f"sitemap.xml: invalid or unreadable XML ({error})")

robots_path = ROOT / "robots.txt"
try:
    robots_lines = [
        line.strip()
        for line in robots_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    expected_sitemap_directive = "Sitemap: https://dishwashercarehub.com/sitemap.xml"
    if robots_lines.count(expected_sitemap_directive) != 1:
        errors.append("robots.txt: expected one absolute sitemap directive")
    expected_feed_directive = "Sitemap: https://dishwashercarehub.com/feed.xml"
    if robots_lines.count(expected_feed_directive) != 1:
        errors.append("robots.txt: expected one absolute Atom feed directive")
    blocking_rules = [
        line for line in robots_lines if line.lower().startswith("disallow:")
        and line.split(":", 1)[1].strip()
    ]
    if blocking_rules:
        errors.append(f"robots.txt: unexpected crawl blocking rules {blocking_rules}")
except OSError as error:
    errors.append(f"robots.txt: unreadable ({error})")

feed_path = ROOT / "feed.xml"
try:
    feed_root = ET.parse(feed_path).getroot()
    atom_namespace = "{http://www.w3.org/2005/Atom}"
    if feed_root.tag != f"{atom_namespace}feed":
        errors.append("feed.xml: root element is not Atom 1.0 feed")
    feed_id = feed_root.findtext(f"{atom_namespace}id", "").strip()
    feed_title = feed_root.findtext(f"{atom_namespace}title", "").strip()
    feed_updated = feed_root.findtext(f"{atom_namespace}updated", "").strip()
    if feed_id != "https://dishwashercarehub.com/feed.xml":
        errors.append("feed.xml: feed id does not match canonical feed URL")
    if not feed_title or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00Z", feed_updated):
        errors.append("feed.xml: missing title or RFC 3339 updated timestamp")
    feed_self_links = [
        link.get("href")
        for link in feed_root.findall(f"{atom_namespace}link")
        if link.get("rel") == "self" and link.get("type") == "application/atom+xml"
    ]
    if feed_self_links != ["https://dishwashercarehub.com/feed.xml"]:
        errors.append("feed.xml: expected one canonical self link")
    feed_entries = feed_root.findall(f"{atom_namespace}entry")
    feed_entry_ids = []
    for entry in feed_entries:
        entry_id = entry.findtext(f"{atom_namespace}id", "").strip()
        feed_entry_ids.append(entry_id)
        record = page_records.get(entry_id.rstrip("/") + "/")
        if not record or "article_published" not in record:
            errors.append(f"feed.xml: entry is not a published article {entry_id}")
            continue
        expected_published = f"{record['article_published']}T00:00:00Z"
        expected_modified = f"{record['article_modified']}T00:00:00Z"
        if entry.findtext(f"{atom_namespace}published", "").strip() != expected_published:
            errors.append(f"feed.xml: publication date mismatch for {entry_id}")
        if entry.findtext(f"{atom_namespace}updated", "").strip() != expected_modified:
            errors.append(f"feed.xml: update date mismatch for {entry_id}")
        if not entry.findtext(f"{atom_namespace}title", "").strip():
            errors.append(f"feed.xml: missing title for {entry_id}")
        if not entry.findtext(f"{atom_namespace}summary", "").strip():
            errors.append(f"feed.xml: missing summary for {entry_id}")
    article_urls = {
        canonical_url
        for canonical_url, record in page_records.items()
        if "article_published" in record
    }
    if set(feed_entry_ids) != article_urls or len(feed_entry_ids) != len(article_urls):
        errors.append("feed.xml: entries do not exactly match published articles")
except (ET.ParseError, OSError) as error:
    errors.append(f"feed.xml: invalid or unreadable Atom XML ({error})")

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
    redirects = vercel_config.get("redirects", [])
    redirect_sources = [redirect.get("source") for redirect in redirects]
    if len(redirect_sources) != len(set(redirect_sources)):
        errors.append("vercel.json: duplicate redirect source")
    redirect_source_set = set(redirect_sources)
    for redirect in redirects:
        source = redirect.get("source", "")
        destination = redirect.get("destination", "")
        if not source.startswith("/") or not destination.startswith("/"):
            errors.append("vercel.json: redirects must use root-relative paths")
            continue
        if redirect.get("permanent") is not True:
            errors.append(f"vercel.json: historical redirect is not permanent {source}")
        source_url = f"https://dishwashercarehub.com{source.rstrip('/')}/"
        destination_url = f"https://dishwashercarehub.com{destination.rstrip('/')}/"
        if source_url in canonical_pages:
            errors.append(f"vercel.json: redirect source is also a canonical page {source}")
        if destination_url not in canonical_pages:
            errors.append(f"vercel.json: redirect destination is not canonical {destination}")
        if destination in redirect_source_set:
            errors.append(f"vercel.json: redirect chain begins at {source}")
    expected_historical_redirect = (
        "/articles/dishwasher-dishes-still-wet-after-heated-dry/"
    )
    if redirect_sources.count(expected_historical_redirect) != 1:
        errors.append(
            "vercel.json: missing historical redirect for removed drying article"
        )
except (json.JSONDecodeError, OSError) as error:
    errors.append(f"vercel.json: invalid or unreadable JSON ({error})")

privacy_text = (ROOT / "privacy" / "index.html").read_text(encoding="utf-8")
required_privacy_disclosures = {
    "Google partner data-use link": "https://policies.google.com/technologies/partner-sites",
    "Google advertising settings": "https://adssettings.google.com/",
    "third-party advertising opt-out": "https://optout.aboutads.info/",
    "certified CMP disclosure": "Google-certified consent management platform",
    "US state opt-out disclosure": "Do Not Sell or Share My Personal Information",
    "Global Privacy Platform disclosure": "Global Privacy Platform",
    "privacy contact": "mailto:pqiswin1@gmail.com",
    "children's privacy disclosure": "not directed to children under 13",
}
for label, required_text in required_privacy_disclosures.items():
    if required_text not in privacy_text:
        errors.append(f"privacy/index.html: missing {label}")

ads_txt_lines = [
    line.strip()
    for line in (ROOT / "ads.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if ads_txt_lines != [ADS_TXT_RECORD]:
    errors.append("ads.txt: publisher declaration is missing, duplicated, or malformed")

not_found_path = ROOT / "404.html"
not_found_text = not_found_path.read_text(encoding="utf-8")
not_found_parser = LinkParser()
not_found_parser.feed(not_found_text)
if 'data-error-page="404"' not in not_found_text:
    errors.append("404.html: missing branded error-page marker")
if not re.search(
    r'<meta name="robots" content="[^"]*noindex[^"]*">',
    not_found_text,
    re.IGNORECASE,
):
    errors.append("404.html: missing noindex robots directive")
if not_found_parser.canonical:
    errors.append("404.html: error pages must not declare a canonical URL")
if ADSENSE_SCRIPT_URL in not_found_text:
    errors.append("404.html: error pages must not load AdSense")
for required_path in (
    "/",
    "/tools/",
    "/tools/dishwasher-guide-finder/",
    "/contact/",
):
    if required_path not in not_found_parser.anchor_links:
        errors.append(f"404.html: missing recovery link {required_path}")

guide_finder_path = ROOT / "tools" / "dishwasher-guide-finder" / "index.html"
guide_finder_text = guide_finder_path.read_text(encoding="utf-8")
guide_finder_parser = LinkParser()
guide_finder_parser.feed(guide_finder_text)
guide_finder_article_links = {
    urljoin("https://dishwashercarehub.com/tools/dishwasher-guide-finder/", link)
    .split("#", 1)[0]
    .rstrip("/")
    + "/"
    for link in guide_finder_parser.anchor_links
    if "/articles/" in urljoin(
        "https://dishwashercarehub.com/tools/dishwasher-guide-finder/", link
    )
}
article_canonicals = {
    canonical_url
    for canonical_url, record in page_records.items()
    if record["path"].parent.parent.name == "articles"
}
if guide_finder_article_links != article_canonicals:
    missing = sorted(article_canonicals - guide_finder_article_links)
    extra = sorted(guide_finder_article_links - article_canonicals)
    errors.append(
        "tools/dishwasher-guide-finder/index.html: guide coverage differs from "
        f"published articles (missing={missing}, extra={extra})"
    )
if guide_finder_text.count("data-guide-card") != len(article_canonicals):
    errors.append(
        "tools/dishwasher-guide-finder/index.html: expected one searchable card per article"
    )
if "../../assets/guide-finder.js" not in guide_finder_text:
    errors.append(
        "tools/dishwasher-guide-finder/index.html: search behavior script is missing"
    )

tool_pages = {
    canonical_url
    for canonical_url, record in page_records.items()
    if record["path"].parent.parent.name == "tools"
}
tools_hub_text = (ROOT / "tools" / "index.html").read_text(encoding="utf-8")
for tool_url in sorted(tool_pages):
    tool_path = urlparse(tool_url).path
    if tool_path not in tools_hub_text:
        errors.append(f"tools/index.html: missing tool listing for {tool_url}")
homepage_text = (ROOT / "index.html").read_text(encoding="utf-8")
expected_tool_stat = (
    f"<strong>{len(tool_pages)}</strong><span>free interactive tools</span>"
)
if expected_tool_stat not in homepage_text:
    errors.append(
        f"index.html: homepage tool count does not match {len(tool_pages)} published tools"
    )

if errors:
    print("Site validation failed:")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)

print(f"Validated {len(HTML_FILES)} HTML files: no known corruption or broken local links.")
