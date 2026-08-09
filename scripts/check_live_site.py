#!/usr/bin/env python3
"""Monitor the deployed site's crawlability, monetization declaration, and URL health."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import sys
import ssl
import time
import xml.etree.ElementTree as ET

BASE_URL = "https://dishwashercarehub.com"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
ADSENSE_SCRIPT_URL = (
    "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?"
    "client=ca-pub-9156049827002127"
)
EXPECTED_ADS_TXT = "google.com, pub-9156049827002127, DIRECT, f08c47fec0942fa0"
USER_AGENT = "DishwasherCareLab-LiveMonitor/1.0 (+https://dishwashercarehub.com/contact/)"


def tls_context():
    """Use the platform trust store, with certifi as a verified local fallback."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


TLS_CONTEXT = tls_context()


@dataclass
class Response:
    requested_url: str
    final_url: str
    status: int
    headers: object
    body: str


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.robots_values = []
        self.adsense_scripts = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link" and "canonical" in values.get("rel", "").lower():
            if values.get("href"):
                self.canonicals.append(values["href"])
        if tag == "meta" and values.get("name", "").lower() == "robots":
            self.robots_values.append(values.get("content", "").lower())
        if tag == "script" and values.get("src") == ADSENSE_SCRIPT_URL:
            self.adsense_scripts += 1


def fetch(url, attempts=2, timeout=20):
    last_error = None
    for attempt in range(attempts):
        request = Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        )
        try:
            with urlopen(request, timeout=timeout, context=TLS_CONTEXT) as response:
                body = response.read().decode("utf-8", errors="replace")
                result = Response(
                    requested_url=url,
                    final_url=response.geturl(),
                    status=response.status,
                    headers=response.headers,
                    body=body,
                )
                if result.status < 500 or attempt == attempts - 1:
                    return result
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            result = Response(
                requested_url=url,
                final_url=error.geturl(),
                status=error.code,
                headers=error.headers,
                body=body,
            )
            if error.code < 500 or attempt == attempts - 1:
                return result
        except (URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt == attempts - 1:
                raise RuntimeError(f"request failed for {url}: {error}") from error
        time.sleep(1)
    raise RuntimeError(f"request failed for {url}: {last_error}")


def validate_html_page(response, expected_url):
    errors = []
    if response.status != 200:
        return [f"{expected_url}: expected HTTP 200, got {response.status}"]
    if response.final_url.rstrip("/") + "/" != expected_url.rstrip("/") + "/":
        errors.append(f"{expected_url}: redirected to {response.final_url}")
    content_type = response.headers.get("Content-Type", "").lower()
    if not content_type.startswith("text/html"):
        errors.append(f"{expected_url}: expected HTML content type, got {content_type!r}")
    parser = PageParser()
    parser.feed(response.body)
    if parser.canonicals != [expected_url]:
        errors.append(
            f"{expected_url}: expected one matching canonical, got {parser.canonicals}"
        )
    if parser.adsense_scripts != 1:
        errors.append(
            f"{expected_url}: expected one AdSense publisher script, got {parser.adsense_scripts}"
        )
    if any("noindex" in value for value in parser.robots_values):
        errors.append(f"{expected_url}: page unexpectedly contains noindex")
    return errors


def sitemap_urls(response):
    if response.status != 200:
        raise RuntimeError(f"sitemap returned HTTP {response.status}")
    content_type = response.headers.get("Content-Type", "").lower()
    if "xml" not in content_type:
        raise RuntimeError(f"sitemap returned unexpected content type {content_type!r}")
    try:
        root = ET.fromstring(response.body)
    except ET.ParseError as error:
        raise RuntimeError(f"sitemap XML is invalid: {error}") from error
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls = []
    for url_element in root.findall(f"{namespace}url"):
        loc = url_element.find(f"{namespace}loc")
        lastmod = url_element.find(f"{namespace}lastmod")
        if loc is None or not loc.text or lastmod is None or not lastmod.text:
            raise RuntimeError("every sitemap URL must have loc and lastmod")
        urls.append(loc.text.strip())
    if not urls:
        raise RuntimeError("sitemap contains no URLs")
    if len(urls) != len(set(urls)):
        raise RuntimeError("sitemap contains duplicate URLs")
    if any(not url.startswith(f"{BASE_URL}/") for url in urls):
        raise RuntimeError("sitemap contains a URL outside the canonical domain")
    return urls


def main():
    errors = []

    try:
        sitemap_response = fetch(SITEMAP_URL)
        urls = sitemap_urls(sitemap_response)
    except RuntimeError as error:
        print(f"Live site monitor failed:\n- {error}")
        return 1

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                errors.extend(validate_html_page(future.result(), url))
            except RuntimeError as error:
                errors.append(str(error))

    home = fetch(f"{BASE_URL}/")
    required_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    }
    for name, expected in required_headers.items():
        if home.headers.get(name) != expected:
            errors.append(
                f"homepage: missing or incorrect {name} header (got {home.headers.get(name)!r})"
            )
    if not home.headers.get("Strict-Transport-Security", "").startswith("max-age="):
        errors.append("homepage: Strict-Transport-Security header is missing")

    robots = fetch(f"{BASE_URL}/robots.txt")
    if robots.status != 200 or f"Sitemap: {SITEMAP_URL}" not in robots.body:
        errors.append("robots.txt is unavailable or does not declare the canonical sitemap")
    if any(
        line.lower().startswith("disallow:") and line.split(":", 1)[1].strip()
        for line in robots.body.splitlines()
    ):
        errors.append("robots.txt unexpectedly blocks crawling")

    ads_txt = fetch(f"{BASE_URL}/ads.txt")
    ads_lines = [line.strip() for line in ads_txt.body.splitlines() if line.strip()]
    if ads_txt.status != 200 or ads_lines != [EXPECTED_ADS_TXT]:
        errors.append("ads.txt is unavailable, duplicated, or does not match the publisher ID")

    missing = fetch(f"{BASE_URL}/definitely-not-a-real-page-monitor-check/")
    if missing.status != 404:
        errors.append(f"unknown URL should return HTTP 404, got {missing.status}")
    if not missing.headers.get("Content-Type", "").lower().startswith("text/html"):
        errors.append("unknown URL should return the custom HTML 404 page")
    if 'data-error-page="404"' not in missing.body:
        errors.append("unknown URL did not return the branded 404 recovery page")
    missing_parser = PageParser()
    missing_parser.feed(missing.body)
    if not any("noindex" in value for value in missing_parser.robots_values):
        errors.append("custom 404 page must contain a noindex robots directive")
    if missing_parser.canonicals:
        errors.append("custom 404 page must not declare a canonical URL")
    if missing_parser.adsense_scripts:
        errors.append("custom 404 page must not load the AdSense publisher script")

    if errors:
        print("Live site monitor failed:")
        print("\n".join(f"- {error}" for error in sorted(errors)))
        return 1
    print(
        f"Live site healthy: {len(urls)} canonical pages returned HTML 200 with "
        "matching canonicals and AdSense; robots, sitemap, ads.txt, security headers, "
        "and HTTP 404 behavior passed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
