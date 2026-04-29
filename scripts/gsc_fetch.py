#!/usr/bin/env python3
"""
GSC fetcher for dishwashercarehub.com

Usage:
  # create venv (optional, recommended)
  python3 -m venv ~/.hermes/profiles/adsense/venv
  source ~/.hermes/profiles/adsense/venv/bin/activate
  # install deps (if pip proxy issues, run with env -u ... as shown below)
  env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \ \
      ~/.hermes/profiles/adsense/venv/bin/python -m pip install --upgrade pip setuptools wheel && \
      env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy ~/.hermes/profiles/adsense/venv/bin/python -m pip install google-auth google-auth-httplib2 google-api-python-client

  # run
  ~/.hermes/profiles/adsense/venv/bin/python scripts/gsc_fetch.py

This script expects the service account JSON at:
  ~/.hermes/profiles/adsense/credentials/searchconsole-service-account.json

It will write outputs to:
  /Users/densefog/Agents/dishwashercarehub.com/Performance/Performance-on-Search-YYYY-MM-DD/

If the google API libs are not available, the script prints clear instructions and exits.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

KEYPATH = os.path.expanduser('~/.hermes/profiles/adsense/credentials/searchconsole-service-account.json')
OUT_BASE = Path('/Users/densefog/Agents/dishwashercarehub.com/Performance')

# helper to print install guidance
def print_install_help():
    print("\nERROR: required google client libraries not installed.\n")
    print("Run these commands in your shell (recommended to use the project's venv):\n")
    print("python3 -m venv ~/.hermes/profiles/adsense/venv")
    print("source ~/.hermes/profiles/adsense/venv/bin/activate")
    print("# If your shell/host injects proxy env vars, run the pip install commands with those envs removed:")
    print("env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \\")
    print("  ~/.hermes/profiles/adsense/venv/bin/python -m pip install --upgrade pip setuptools wheel")
    print("env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \\")
    print("  ~/.hermes/profiles/adsense/venv/bin/python -m pip install google-auth google-auth-httplib2 google-api-python-client")
    print("\nAfter that, run this script with the venv python.\n")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception as e:
    print_install_help()
    sys.exit(2)

# basic API helpers
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

if not os.path.exists(KEYPATH):
    print(f"Service account key not found at: {KEYPATH}\nPlease place the JSON key there and set permissions chmod 600.")
    sys.exit(3)

creds = service_account.Credentials.from_service_account_file(KEYPATH, scopes=SCOPES)
webmasters = build('webmasters', 'v3', credentials=creds)

# list sites the SA can see
try:
    sites = webmasters.sites().list().execute()
except HttpError as he:
    print("API error listing sites:", str(he))
    print("Make sure the service-account email has been added as a Search Console user (Settings → Users and permissions)")
    sys.exit(4)

site_entries = sites.get('siteEntry', [])
print(f"Found {len(site_entries)} site entries visible to the service account")
for s in site_entries:
    print('-', s.get('siteUrl'), s.get('permissionLevel'))

# pick our site
SITE_URL = 'https://dishwashercarehub.com'
if not any(s.get('siteUrl') == SITE_URL for s in site_entries):
    print(f"\nService account does not appear to have access to {SITE_URL}.\nPlease add the service account email as a user in Search Console.")
    sys.exit(5)

# fetch performance data via searchanalytics.query for last 28 days
end_date = datetime.utcnow().date() - timedelta(days=1)
start_date = end_date - timedelta(days=27)
req = {
    'startDate': start_date.isoformat(),
    'endDate': end_date.isoformat(),
    'dimensions': ['page','query','device','country'],
    'rowLimit': 25000,
}

try:
    resp = webmasters.searchanalytics().query(siteUrl=SITE_URL, body=req).execute()
except HttpError as he:
    print('API error fetching performance data:', str(he))
    sys.exit(6)

rows = resp.get('rows', [])
print(f"Fetched {len(rows)} rows from Search Console (date range {start_date} to {end_date})")

# prepare output dir
out_dir = OUT_BASE / f'Performance-on-Search-{datetime.utcnow().date().isoformat()}'
out_dir.mkdir(parents=True, exist_ok=True)

# write a simple CSV of page-level aggregates and queries
import csv
page_csv = out_dir / '网页.csv'
query_csv = out_dir / '查询数.csv'

# aggregate by page and query
from collections import defaultdict
page_acc = defaultdict(lambda: {'clicks':0,'impressions':0,'ctr_sum':0,'position_sum':0,'count':0})
query_acc = defaultdict(lambda: {'clicks':0,'impressions':0,'ctr_sum':0,'position_sum':0,'count':0})

for r in rows:
    keys = r.get('keys', [])
    clicks = r.get('clicks', 0)
    impr = r.get('impressions', 0)
    ctr = r.get('ctr', 0.0)
    pos = r.get('position', 0.0)
    page = keys[0] if len(keys)>0 else ''
    query = keys[1] if len(keys)>1 else ''

    if page:
        a = page_acc[page]
        a['clicks'] += clicks
        a['impressions'] += impr
        a['ctr_sum'] += ctr
        a['position_sum'] += pos
        a['count'] += 1
    if query:
        b = query_acc[query]
        b['clicks'] += clicks
        b['impressions'] += impr
        b['ctr_sum'] += ctr
        b['position_sum'] += pos
        b['count'] += 1

with open(page_csv, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['排名靠前的网页','点击次数','展示','点击率','排名'])
    for p, v in sorted(page_acc.items(), key=lambda x: x[1]['impressions'], reverse=True):
        avg_ctr = v['ctr_sum']/v['count'] if v['count'] else 0
        avg_pos = v['position_sum']/v['count'] if v['count'] else 0
        w.writerow([p, int(v['clicks']), int(v['impressions']), f"{avg_ctr:.4f}", f"{avg_pos:.2f}"])

with open(query_csv, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['热门查询','点击次数','展示','点击率','排名'])
    for q, v in sorted(query_acc.items(), key=lambda x: x[1]['impressions'], reverse=True)[:200]:
        avg_ctr = v['ctr_sum']/v['count'] if v['count'] else 0
        avg_pos = v['position_sum']/v['count'] if v['count'] else 0
        w.writerow([q, int(v['clicks']), int(v['impressions']), f"{avg_ctr:.4f}", f"{avg_pos:.2f}"])

# write a brief report
report = out_dir / 'report.txt'
with open(report, 'w', encoding='utf-8') as fh:
    fh.write(f"Search Console report for {SITE_URL}\n")
    fh.write(f"Date range: {start_date} to {end_date}\n")
    fh.write(f"Rows fetched: {len(rows)}\n\n")
    fh.write('Top 20 pages by impressions:\n')
    for p, v in sorted(page_acc.items(), key=lambda x: x[1]['impressions'], reverse=True)[:20]:
        fh.write(f"{p} — impressions={v['impressions']} clicks={v['clicks']} avg_pos={v['position_sum']/v['count'] if v['count'] else 0:.2f}\n")
    fh.write('\nTop 20 queries by impressions:\n')
    for q, v in sorted(query_acc.items(), key=lambda x: x[1]['impressions'], reverse=True)[:20]:
        fh.write(f"{q} — impressions={v['impressions']} clicks={v['clicks']} avg_pos={v['position_sum']/v['count'] if v['count'] else 0:.2f}\n")

print('\nWrote outputs to:', out_dir)
print('Files:', page_csv.name, query_csv.name, report.name)
print('Done.')
