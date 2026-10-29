#!/usr/bin/env bash
# One command: your own QM at https://<label>.orgo.dev on a dedicated Orgo computer.
#
#   export ORGO_API_KEY=sk_live_...        # orgo.ai > Settings > API keys
#   bash launch.sh acme-qm                 # -> https://acme-qm.orgo.dev (or acme-qm-xxxx if taken)
#   bash launch.sh                         # -> https://qm-xxxx.orgo.dev
#
# Options (env):
#   QM_TEMPLATE      template ref        (default: default/qm@0.1.7, i.e. published to your account;
#                                        use system/qm once Orgo lists it as a curated template)
#   ORGO_WORKSPACE   workspace id        (default: your first workspace)
#   ENDS_IN_HOURS    auto-stop after N h (default: never)
#
# Needs: bash, curl, python3. Your key stays on your machine; it is never sent to the computer.
set -euo pipefail

rand4() { python3 -c 'import secrets;print(secrets.token_hex(2))'; }
label="${1:-qm-$(rand4)}"   # no name given -> qm-xxxx
[[ "$label" =~ ^[a-z0-9][a-z0-9-]{1,40}[a-z0-9]$ ]] || { echo "usage: ORGO_API_KEY=... $0 <label>   (lowercase letters, digits, dashes)"; exit 1; }
cname="qm-${label#qm-}"   # computer name
: "${ORGO_API_KEY:?set ORGO_API_KEY (orgo.ai > Settings > API keys)}"
API=https://www.orgo.ai/api
TEMPLATE="${QM_TEMPLATE:-default/qm@0.1.7}"

api() { # method path [json]
  local out code
  out=$(curl -sS -w '\n%{http_code}' -X "$1" "$API$2" -H "Authorization: Bearer $ORGO_API_KEY" \
        -H "Content-Type: application/json" ${3:+-d "$3"}) || return 1
  code=${out##*$'\n'}; out=${out%$'\n'*}
  if [[ "$code" -ge 400 ]]; then echo "Orgo API $1 $2 -> $code: $out" >&2; return 1; fi
  printf '%s' "$out"
}
json() { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"; }
on_box() { # command [timeout]
  api POST "/computers/$cid/bash" "$(python3 -c 'import json,sys;print(json.dumps({"command":sys.argv[1],"timeout":int(sys.argv[2])}))' "$1" "${2:-60}")" \
    | json 'd.get("output","")'
}

ws="${ORGO_WORKSPACE:-$(api GET /workspaces | json 'd["workspaces"][0]["id"]')}"
echo "→ workspace $ws"

body=$(python3 -c 'import json,sys
b={"workspace_id":sys.argv[1],"name":sys.argv[2],"template_ref":sys.argv[3]}
if sys.argv[4]: b["ends_in_hours"]=int(sys.argv[4])
print(json.dumps(b))' "$ws" "$cname" "$TEMPLATE" "${ENDS_IN_HOURS:-}")
cid=$(api POST /computers "$body" | json 'd["id"]')
echo "→ computer $cname ($cid) launched from $TEMPLATE"

# orgo.dev names are global across Orgo accounts. If the name is taken, add a short random
# suffix and try again (acme-qm -> acme-qm-7f3a).
url=""
for try in "$label" "$label-$(rand4)" "$label-$(rand4)"; do
  if out=$(api POST "/computers/$cid/public-urls" "{\"port\":18081,\"label\":\"$try\"}"); then
    url=$(printf '%s' "$out" | json 'd.get("url") or "https://"+(d.get("hostname") or d.get("domain"))'); break
  fi
  echo "→ $try.orgo.dev unavailable; trying another name"
done
[ -n "$url" ] || { echo "Couldn't get an orgo.dev URL (each account gets 10 free names). The computer ($cid) is running; free a name or delete it in the dashboard."; exit 1; }
echo "→ public URL $url → port 18081"

echo -n "→ starting QM (first launch pulls images, ~3 min) "
for _ in $(seq 1 60); do
  if on_box 'grep -q "^== qm-start done" /var/log/qm-start.log 2>/dev/null && echo READY' 20 | grep -q READY; then echo " up"; break; fi
  echo -n "."; sleep 10
done

echo "→ switching QM to $url"
on_box "/usr/local/bin/qm-public $url >/dev/null 2>&1; grep -E '^QM is up' /var/log/qm-start.log | tail -1" 300 | grep -q "$url" \
  || { echo "QM didn't come up at $url. Check /var/log/qm-start.log on the computer, then run: qm-public $url"; exit 1; }
link=$(on_box '/usr/local/bin/qm-open 2>/dev/null | grep -E "^https://" | tail -1' 120)

cat <<EOF

QM is live: $url

Admin sign-in (one-time, expires in 5 minutes; paste the whole thing):
$link

Next:
  1. Admin > Onboarding: add a model key (Anthropic, OpenAI or OpenRouter).
  2. For teammates, run 'qm-email' in the computer's QM terminal (Resend).
  New admin link anytime: 'qm-open' in that terminal.
  Desktop: https://www.orgo.ai/desktops (computer $cname)
EOF
