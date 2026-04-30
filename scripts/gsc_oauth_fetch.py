#!/usr/bin/env python3
"""
OAuth-based GSC fetcher (user-consent flow)

Usage:
  # from project root, using the existing venv we created earlier
  env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \
    ~/.hermes/profiles/adsense/venv/bin/python -m pip install google-auth-oauthlib
  ~/.hermes/profiles/adsense/venv/bin/python scripts/gsc_oauth_fetch.py

It expects an OAuth client secrets JSON (desktop app) at:
  ~/.hermes/profiles/adsense/credentials/oauth_client_secrets.json

On first run it opens a browser for you to approve access and saves the token to:
  ~/.hermes/profiles/adsense/credentials/oauth_token.json

Outputs are written to the Performance/ directory alongside the repo (same as the service-account script).
"""
import os, sys, json, csv
from pathlib import Path
from datetime import datetime, timedelta

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception as e:
    print("Required libraries not installed. Run:")
    print("env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \\")
    print("  ~/.hermes/profiles/adsense/venv/bin/python -m pip install google-auth-oauthlib")
    sys.exit(2)

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
SECRETS = os.path.expanduser('~/.hermes/profiles/adsense/credentials/oauth_client_secrets.json')
TOKEN_PATH = os.path.expanduser('~/.hermes/profiles/adsense/credentials/oauth_token.json')
OUT_BASE = Path('/Users/densefog/Agents/dishwashercarehub.com/Performance')
SITE_URL = 'https://dishwashercarehub.com/'

if not os.path.exists(SECRETS):
    print(f"OAuth client secrets not found at {SECRETS}")
    print("Create an OAuth 2.0 Client ID (Desktop) in Google Cloud Console and download JSON. Save it to the path above.")
    print("Steps summary:")
    print(" 1) Console: https://console.developers.google.com/apis/credentials?project=dishwashercarehub-analytics")
    print(" 2) Create Credentials → OAuth Client ID → Application type: Desktop app → Download JSON")
    print(" 3) Save file as: ~/.hermes/profiles/adsense/credentials/oauth_client_secrets.json")
    sys.exit(3)

creds = None
# Run installed app flow if token missing
if os.path.exists(TOKEN_PATH):
    try:
        with open(TOKEN_PATH, 'r') as f:
            tok = json.load(f)
        # Construct Credentials from token requires google.oauth2.credentials.Credentials
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_info(tok, SCOPES)
    except Exception:
        creds = None

if not creds or not creds.valid:
    flow = InstalledAppFlow.from_client_secrets_file(SECRETS, SCOPES)
    creds = flow.run_local_server(port=0)
    # save token
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())
    print(f"Saved OAuth token to {TOKEN_PATH}")

# Build webmasters
try:
    webmasters = build('webmasters', 'v3', credentials=creds)
except Exception as e:
    print('Error building webmasters client:', e)
    sys.exit(4)

# Check site access
try:
    sites = webmasters.sites().list().execute()
except HttpError as he:
    print('API error listing sites:', he)
    sys.exit(5)

site_entries = sites.get('siteEntry', [])
print(f"Found {len(site_entries)} site entries visible to the authorized account")
for s in site_entries:
    print('-', s.get('siteUrl'), s.get('permissionLevel'))

if not any(s.get('siteUrl') == SITE_URL for s in site_entries):
    print(f"\nAuthorized account does not have access to {SITE_URL}. Add your Google account as a user in Search Console for that property and retry.")
    sys.exit(6)

# fetch last 28 days
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
    print('API error fetching performance data:', he)
    sys.exit(7)

rows = resp.get('rows', [])
print(f"Fetched {len(rows)} rows from Search Console (date range {start_date} to {end_date})")

# aggregate
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

out_dir = OUT_BASE / f'Performance-on-Search-{datetime.utcnow().date().isoformat()}'
out_dir.mkdir(parents=True, exist_ok=True)
page_csv = out_dir / '网页.csv'
query_csv = out_dir / '查询数.csv'
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
