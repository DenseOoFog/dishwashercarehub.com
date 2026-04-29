#!/bin/bash
set -euo pipefail
KEYPATH="$HOME/.hermes/profiles/adsense/credentials/searchconsole-service-account.json"
OUT_BASE="/Users/densefog/Agents/dishwashercarehub.com/Performance"
SITE_URL_ENCODED=$(python3 - <<PY
from urllib.parse import quote_plus
print(quote_plus('https://dishwashercarehub.com'))
PY
)

if [ ! -f "$KEYPATH" ]; then
  echo "Service account key not found at $KEYPATH" >&2
  exit 2
fi

# extract client_email and private_key
CLIENT_EMAIL=$(python3 - <<PY
import json
j=json.load(open('$KEYPATH'))
print(j['client_email'])
PY
)

python3 - <<PY > /tmp/key.pem
import json
j=json.load(open('$KEYPATH'))
print(j['private_key'])
PY

chmod 600 /tmp/key.pem

# build JWT
HEADER='{"alg":"RS256","typ":"JWT"}'
now=$(python3 - <<PY
import time
print(int(time.time()))
PY
)
exp=$((now+3600))
CLAIM=$(python3 - <<PY
import json, time
payload={
  'iss': '$CLIENT_EMAIL',
  'scope': 'https://www.googleapis.com/auth/webmasters.readonly',
  'aud': 'https://oauth2.googleapis.com/token',
  'exp': $exp,
  'iat': $now
}
print(json.dumps(payload, separators=(',',':')))
PY
)

b64url() {
  python3 - <<PY
import sys,base64
s=sys.stdin.read().encode('utf-8')
print(base64.urlsafe_b64encode(s).decode('utf-8').rstrip('='))
PY
}

header_b64=$(printf "%s" "$HEADER" | b64url)
claim_b64=$(printf "%s" "$CLAIM" | b64url)

TO_SIGN="$header_b64.$claim_b64"
# sign with openssl
sig=$(printf "%s" "$TO_SIGN" | openssl dgst -sha256 -sign /tmp/key.pem | openssl base64 -A | tr '+/' '-_' | tr -d '=')
JWT="$TO_SIGN.$sig"

# request access token
TOKEN_JSON=$(mktemp)
curl -s -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=$JWT" > "$TOKEN_JSON"

ACCESS_TOKEN=$(python3 - <<PY
import json
j=json.load(open('$TOKEN_JSON'))
print(j.get('access_token',''))
PY
)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Failed to get access token. Response:" >&2
  cat "$TOKEN_JSON" >&2
  exit 5
fi

# list sites
SITES_JSON=$(mktemp)
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://www.googleapis.com/webmasters/v3/sites" > "$SITES_JSON"

# show sites
echo "Sites visible to service account:"
python3 - <<PY
import json
j=json.load(open('$SITES_JSON'))
for s in j.get('siteEntry',[]):
    print(s.get('siteUrl'), s.get('permissionLevel'))
PY

# check access to our site
python3 - <<PY
import json,sys
j=json.load(open('$SITES_JSON'))
if not any(s.get('siteUrl')=='https://dishwashercarehub.com' for s in j.get('siteEntry',[])):
    print('Service account does not have access to https://dishwashercarehub.com', file=sys.stderr)
    sys.exit(10)
print('Service account confirmed for https://dishwashercarehub.com')
PY

# compute dates (last 28 days: end=yesterday, start=end-27)
DATES=$(python3 - <<PY
from datetime import datetime, timedelta
end=datetime.utcnow().date()-timedelta(days=1)
start=end-timedelta(days=27)
print(start.isoformat(), end.isoformat())
PY
)
START=$(echo $DATES | awk '{print $1}')
END=$(echo $DATES | awk '{print $2}')

REQ_JSON=$(mktemp)
cat > $REQ_JSON <<EOF
{"startDate":"$START","endDate":"$END","dimensions":["page","query","device","country"],"rowLimit":25000}
EOF

# call searchanalytics.query
OUT_DIR="$OUT_BASE/Performance-on-Search-$(date +%F)"
mkdir -p "$OUT_DIR"
RESPONSE_JSON="$OUT_DIR/searchanalytics.json"

curl -s -X POST "https://www.googleapis.com/webmasters/v3/sites/https://dishwashercarehub.com/searchAnalytics/query" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @${REQ_JSON} > "$RESPONSE_JSON"

# convert rows to CSVs using python (no external deps)
python3 - <<PY
import json,csv
r=json.load(open('$RESPONSE_JSON'))
rows=r.get('rows',[])
from collections import defaultdict
page_acc=defaultdict(lambda:{'clicks':0,'impressions':0,'ctr_sum':0,'pos_sum':0,'count':0})
query_acc=defaultdict(lambda:{'clicks':0,'impressions':0,'ctr_sum':0,'pos_sum':0,'count':0})
for row in rows:
    keys=row.get('keys',[])
    clicks=row.get('clicks',0)
    impr=row.get('impressions',0)
    ctr=row.get('ctr',0.0)
    pos=row.get('position',0.0)
    page=keys[0] if len(keys)>0 else ''
    query=keys[1] if len(keys)>1 else ''
    if page:
        a=page_acc[page]
        a['clicks']+=clicks
        a['impressions']+=impr
        a['ctr_sum']+=ctr
        a['pos_sum']+=pos
        a['count']+=1
    if query:
        b=query_acc[query]
        b['clicks']+=clicks
        b['impressions']+=impr
        b['ctr_sum']+=ctr
        b['pos_sum']+=pos
        b['count']+=1

with open('$OUT_DIR/网页.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh)
    w.writerow(['排名靠前的网页','点击次数','展示','点击率','排名'])
    for p,v in sorted(page_acc.items(), key=lambda x:x[1]['impressions'], reverse=True):
        avg_ctr=v['ctr_sum']/v['count'] if v['count'] else 0
        avg_pos=v['pos_sum']/v['count'] if v['count'] else 0
        w.writerow([p,int(v['clicks']),int(v['impressions']),f"{avg_ctr:.4f}",f"{avg_pos:.2f}"])

with open('$OUT_DIR/查询数.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh)
    w.writerow(['热门查询','点击次数','展示','点击率','排名'])
    for q,v in sorted(query_acc.items(), key=lambda x:x[1]['impressions'], reverse=True)[:200]:
        avg_ctr=v['ctr_sum']/v['count'] if v['count'] else 0
        avg_pos=v['pos_sum']/v['count'] if v['count'] else 0
        w.writerow([q,int(v['clicks']),int(v['impressions']),f"{avg_ctr:.4f}",f"{avg_pos:.2f}"])

with open('$OUT_DIR/report.txt','w',encoding='utf-8') as fh:
    fh.write(f"Search Console report for https://dishwashercarehub.com\nDate range: $START to $END\nRows fetched: {len(rows)}\n\n")
    fh.write('Top 20 pages by impressions:\n')
    for p,v in sorted(page_acc.items(), key=lambda x:x[1]['impressions'], reverse=True)[:20]:
        fh.write(f"{p} — impressions={v['impressions']} clicks={v['clicks']} avg_pos={v['pos_sum']/v['count'] if v['count'] else 0:.2f}\n")
    fh.write('\nTop 20 queries by impressions:\n')
    for q,v in sorted(query_acc.items(), key=lambda x:x[1]['impressions'], reverse=True)[:20]:
        fh.write(f"{q} — impressions={v['impressions']} clicks={v['clicks']} avg_pos={v['pos_sum']/v['count'] if v['count'] else 0:.2f}\n")

print('Wrote outputs to', '$OUT_DIR')
PY

# clean up
rm -f /tmp/key.pem

exit 0
