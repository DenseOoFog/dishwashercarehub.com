#!/usr/bin/env bash
set -euo pipefail

# Minimal helper for admins: checks for the service-account JSON and prints
# the curl-based fetch instructions. This is a safety-first placeholder —
# the full, robust curl flow is fragile across shells and proxies. Use the
# Python fetcher (scripts/gsc_fetch.py) when possible.

KEYPATH="$HOME/.hermes/profiles/adsense/credentials/searchconsole-service-account.json"
OUT_BASE="/Users/densefog/Agents/dishwashercarehub.com/Performance"
SITE_URL='https://dishwashercarehub.com'

if [ ! -f "$KEYPATH" ]; then
  echo "ERROR: Service account key not found at: $KEYPATH"
  echo "Please place the Search Console service account JSON there with chmod 600 and re-run this script."
  echo
  echo "If you prefer the Python fetcher (recommended), follow these steps to create a venv and install deps (clears common proxy env vars):"
  echo "  python3 -m venv ~/.hermes/profiles/adsense/venv"
  echo "  source ~/.hermes/profiles/adsense/venv/bin/activate"
  echo "  env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \\" \
  echo "    ~/.hermes/profiles/adsense/venv/bin/python -m pip install --upgrade pip setuptools wheel"
  echo "  env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \\" \
  echo "    ~/.hermes/profiles/adsense/venv/bin/python -m pip install google-auth google-auth-httplib2 google-api-python-client"
  echo
  echo "Once the key is present you can run either scripts/gsc_fetch.py (recommended) or this curl-based approach (advanced)."
  exit 2
fi

# Key exists — show next steps for advanced users (manual curl JWT flow). Do NOT attempt to run automatically here because
# signing the JWT in portable shells can be brittle. Provide self-contained commands the user can copy/paste.

echo "Service account key found at: $KEYPATH"
echo
cat <<'EOF'
Advanced: curl-based JWT flow (copy-paste and adapt; requires openssl + jq + base64 + curl)

1) Extract fields from key JSON:

  SERVICE_EMAIL=$(python3 -c "import json,sys;print(json.load(open('$KEYPATH'))['client_email'])")
  PRIVKEY=$(python3 -c "import json,sys;print(json.load(open('$KEYPATH'))['private_key'])")

2) Create JWT header & claimset (example uses files):

  cat >header.json <<H
  {"alg":"RS256","typ":"JWT"}
H
  now=$(date +%s)
  exp=$((now+3600))
  cat >claim.json <<C
  {
    "iss": "${SERVICE_EMAIL}",
    "scope": "https://www.googleapis.com/auth/webmasters.readonly",
    "aud": "https://oauth2.googleapis.com/token",
    "exp": ${exp},
    "iat": ${now}
  }
C

3) Base64url-encode and sign with openssl

  base64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
  HEADER_B64=$(cat header.json | tr -d '\n' | openssl base64 -A | tr '+/' '-_' | tr -d '=')
  CLAIM_B64=$(cat claim.json | tr -d '\n' | openssl base64 -A | tr '+/' '-_' | tr -d '=')
  echo "${HEADER_B64}.${CLAIM_B64}" >tosign

  # write the private key to a temp file and sign
  python3 - <<PY
import json,sys,tempfile
k=json.load(open('$KEYPATH'))['private_key']
fn=tempfile.NamedTemporaryFile(delete=False)
fn.write(k.encode())
fn.flush()
print(fn.name)
PY
  # The above prints the temp filename; replace <TMPKEY> with it and run:
  # openssl dgst -sha256 -sign <TMPKEY> -binary tosign | base64url

4) Exchange assertion for access token:

  curl -s -X POST https://oauth2.googleapis.com/token \
    -d grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer \
    -d assertion=<SIGNED_JWT>

5) Use access_token to call Search Console API:

  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"startDate":"2026-01-01","endDate":"2026-01-28","dimensions":["page","query"],"rowLimit":25000}' \
    "https://www.googleapis.com/webmasters/v3/sites/${SITE_URL}/searchAnalytics/query" > response.json

Notes:
- The above requires careful quoting and a writable temp file for the private key. If you want, I can attempt the full automated curl flow here once you place the service-account JSON; but it is more reliable to run the Python fetcher in a venv.
EOF

exit 0
