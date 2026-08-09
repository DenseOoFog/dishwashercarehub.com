#!/usr/bin/env python3
"""Fetch and aggregate dishwashercarehub.com Search Console performance data."""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
DEFAULT_PROPERTY = "https://dishwashercarehub.com/"
ROW_LIMIT = 25_000


def normalize_property_url(value: str) -> str:
    """Normalize only for matching; API calls still use Google's exact siteUrl."""
    value = value.strip()
    if value.startswith("sc-domain:"):
        return value.rstrip("/")
    return value.rstrip("/") + "/"


def select_property(site_entries: list[dict], requested: str) -> str | None:
    """Return the exact Search Console property string advertised by the API."""
    exact = [entry.get("siteUrl") for entry in site_entries if entry.get("siteUrl") == requested]
    if exact:
        return exact[0]
    normalized = normalize_property_url(requested)
    matches = [
        entry.get("siteUrl")
        for entry in site_entries
        if entry.get("siteUrl")
        and normalize_property_url(entry["siteUrl"]) == normalized
    ]
    return matches[0] if len(matches) == 1 else None


def aggregate_rows(rows: list[dict], key_index: int) -> dict[str, dict[str, float]]:
    """Aggregate metrics, weighting average position by impressions."""
    totals = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0, "position_weight": 0.0})
    for row in rows:
        keys = row.get("keys", [])
        if len(keys) <= key_index or not keys[key_index]:
            continue
        key = keys[key_index]
        impressions = float(row.get("impressions", 0) or 0)
        item = totals[key]
        item["clicks"] += float(row.get("clicks", 0) or 0)
        item["impressions"] += impressions
        item["position_weight"] += float(row.get("position", 0) or 0) * impressions

    result = {}
    for key, item in totals.items():
        impressions = item["impressions"]
        result[key] = {
            "clicks": item["clicks"],
            "impressions": impressions,
            "ctr": item["clicks"] / impressions if impressions else 0.0,
            "position": item["position_weight"] / impressions if impressions else 0.0,
        }
    return result


def metric_totals(aggregate: dict[str, dict[str, float]]) -> dict[str, float]:
    """Return click, impression, CTR, and impression-weighted position totals."""
    clicks = sum(item["clicks"] for item in aggregate.values())
    impressions = sum(item["impressions"] for item in aggregate.values())
    weighted_position = sum(
        item["position"] * item["impressions"] for item in aggregate.values()
    )
    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": clicks / impressions if impressions else 0.0,
        "position": weighted_position / impressions if impressions else 0.0,
    }


def compare_aggregates(current: dict, previous: dict) -> list[dict]:
    """Compare two aggregate maps while retaining newly appearing and lost keys."""
    rows = []
    for key in set(current) | set(previous):
        now = current.get(key, {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0})
        before = previous.get(key, {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0})
        rows.append({
            "key": key,
            "current": now,
            "previous": before,
            "click_delta": now["clicks"] - before["clicks"],
            "impression_delta": now["impressions"] - before["impressions"],
            "ctr_delta": now["ctr"] - before["ctr"],
            "position_delta": (
                before["position"] - now["position"]
                if now["impressions"] and before["impressions"] else None
            ),
        })
    return rows


def fetch_all_rows(webmasters, site_url: str, request: dict) -> list[dict]:
    """Page through Search Analytics results instead of truncating at 25k rows."""
    rows = []
    start_row = 0
    while True:
        page_request = dict(request, rowLimit=ROW_LIMIT, startRow=start_row)
        response = webmasters.searchanalytics().query(
            siteUrl=site_url, body=page_request
        ).execute()
        batch = response.get("rows", [])
        rows.extend(batch)
        if len(batch) < ROW_LIMIT:
            return rows
        start_row += ROW_LIMIT


def write_csv(path: Path, first_column: str, aggregate: dict, limit: int | None = None) -> None:
    ordered = sorted(
        aggregate.items(), key=lambda item: item[1]["impressions"], reverse=True
    )
    if limit is not None:
        ordered = ordered[:limit]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([first_column, "点击次数", "展示", "点击率", "排名"])
        for key, values in ordered:
            writer.writerow(
                [key, int(values["clicks"]), int(values["impressions"]),
                 f'{values["ctr"]:.4f}', f'{values["position"]:.2f}']
            )


def write_change_section(handle, heading: str, current: dict, previous: dict) -> None:
    comparisons = compare_aggregates(current, previous)
    handle.write(f"{heading} — largest impression gains:\n")
    for row in sorted(comparisons, key=lambda item: item["impression_delta"], reverse=True)[:10]:
        if row["impression_delta"] <= 0:
            break
        position = (
            f'{row["position_delta"]:+.2f}'
            if row["position_delta"] is not None else "new/no comparison"
        )
        handle.write(
            f'{row["key"]} — impressions {row["previous"]["impressions"]:.0f}→'
            f'{row["current"]["impressions"]:.0f} ({row["impression_delta"]:+.0f}); '
            f'clicks {row["previous"]["clicks"]:.0f}→{row["current"]["clicks"]:.0f}; '
            f'position improvement {position}\n'
        )
    handle.write(f"{heading} — largest impression losses:\n")
    for row in sorted(comparisons, key=lambda item: item["impression_delta"])[:10]:
        if row["impression_delta"] >= 0:
            break
        handle.write(
            f'{row["key"]} — impressions {row["previous"]["impressions"]:.0f}→'
            f'{row["current"]["impressions"]:.0f} ({row["impression_delta"]:+.0f}); '
            f'clicks {row["previous"]["clicks"]:.0f}→{row["current"]["clicks"]:.0f}\n'
        )
    handle.write("\n")


def write_report(path: Path, site_url: str, start_date, end_date, previous_start,
                 previous_end, row_count: int, previous_row_count: int,
                 page_data: dict, query_data: dict, previous_page_data: dict,
                 previous_query_data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"Search Console report for {site_url}\n")
        handle.write(f"Current range: {start_date} to {end_date}\n")
        handle.write(f"Previous range: {previous_start} to {previous_end}\n")
        handle.write(f"Rows fetched: current={row_count}, previous={previous_row_count}\n\n")
        current_total = metric_totals(page_data)
        previous_total = metric_totals(previous_page_data)
        handle.write("Site totals (current versus previous):\n")
        handle.write(
            f'Clicks: {current_total["clicks"]:.0f} vs {previous_total["clicks"]:.0f} '
            f'({current_total["clicks"] - previous_total["clicks"]:+.0f})\n'
            f'Impressions: {current_total["impressions"]:.0f} vs {previous_total["impressions"]:.0f} '
            f'({current_total["impressions"] - previous_total["impressions"]:+.0f})\n'
            f'CTR: {current_total["ctr"]:.2%} vs {previous_total["ctr"]:.2%} '
            f'({current_total["ctr"] - previous_total["ctr"]:+.2%})\n'
            f'Average position: {current_total["position"]:.2f} vs {previous_total["position"]:.2f}\n\n'
        )
        for heading, data in (("Top 20 pages by impressions", page_data),
                              ("Top 20 queries by impressions", query_data)):
            handle.write(f"{heading}:\n")
            for key, values in sorted(
                data.items(), key=lambda item: item[1]["impressions"], reverse=True
            )[:20]:
                handle.write(
                    f'{key} — impressions={values["impressions"]:.0f} '
                    f'clicks={values["clicks"]:.0f} ctr={values["ctr"]:.2%} '
                    f'avg_pos={values["position"]:.2f}\n'
                )
            handle.write("\n")
        write_change_section(handle, "Pages", page_data, previous_page_data)
        write_change_section(handle, "Queries", query_data, previous_query_data)


def print_install_help() -> None:
    print("ERROR: required Google client libraries are not installed.")
    print("Install google-auth, google-auth-httplib2, and google-api-python-client, then rerun.")


def main() -> int:
    keypath = Path(os.path.expanduser(os.environ.get(
        "GSC_CREDENTIALS_FILE",
        "~/.hermes/profiles/adsense/credentials/searchconsole-service-account.json",
    )))
    output_base = Path(os.environ.get(
        "GSC_OUTPUT_DIR", Path(__file__).resolve().parents[1] / "Performance"
    ))
    requested_property = os.environ.get("GSC_SITE_URL", DEFAULT_PROPERTY)

    if not keypath.exists() or keypath.stat().st_size == 0:
        print(f"Search Console credential file is missing or empty: {keypath}")
        return 3
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        print_install_help()
        return 2

    credentials = service_account.Credentials.from_service_account_file(keypath, scopes=SCOPES)
    webmasters = build("webmasters", "v3", credentials=credentials)
    try:
        site_entries = webmasters.sites().list().execute().get("siteEntry", [])
    except HttpError as error:
        print("API error listing sites:", error)
        print("Add the service-account email in Search Console Users and permissions.")
        return 4

    site_url = select_property(site_entries, requested_property)
    if not site_url:
        visible = ", ".join(entry.get("siteUrl", "") for entry in site_entries) or "none"
        print(f"No unique Search Console property matched {requested_property}. Visible: {visible}")
        return 5
    print(f"Using Search Console property: {site_url}")

    pacific_today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    end_date = pacific_today - timedelta(days=1)
    start_date = end_date - timedelta(days=27)
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=27)
    request_base = {
        "dimensions": ["page", "query", "device", "country"],
        "aggregationType": "auto",
    }
    try:
        rows = fetch_all_rows(webmasters, site_url, dict(
            request_base, startDate=start_date.isoformat(), endDate=end_date.isoformat()
        ))
        previous_rows = fetch_all_rows(webmasters, site_url, dict(
            request_base, startDate=previous_start.isoformat(), endDate=previous_end.isoformat()
        ))
    except HttpError as error:
        print("API error fetching performance data:", error)
        return 6

    page_data = aggregate_rows(rows, 0)
    query_data = aggregate_rows(rows, 1)
    previous_page_data = aggregate_rows(previous_rows, 0)
    previous_query_data = aggregate_rows(previous_rows, 1)
    output_dir = output_base / f"Performance-on-Search-{pacific_today.isoformat()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    page_csv, query_csv, report = (
        output_dir / "网页.csv", output_dir / "查询数.csv", output_dir / "report.txt"
    )
    write_csv(page_csv, "排名靠前的网页", page_data)
    write_csv(query_csv, "热门查询", query_data, limit=200)
    write_report(
        report, site_url, start_date, end_date, previous_start, previous_end,
        len(rows), len(previous_rows), page_data, query_data,
        previous_page_data, previous_query_data,
    )
    print(
        f"Fetched current={len(rows)} rows ({start_date} to {end_date}); "
        f"previous={len(previous_rows)} rows ({previous_start} to {previous_end})"
    )
    print("Wrote:", page_csv, query_csv, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
