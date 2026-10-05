#!/usr/bin/env bash
# Fastlane MCP connectivity probe — run this on a machine with network access
# to the Fastlane API. It answers the questions the setup guide marks as
# unconfirmed: which endpoint path responds, which auth header is accepted,
# and whether the account's plan allows MCP access at all.
#
# The API key is read from the environment only. It is never printed, never
# written to a file, and never sent anywhere except the host you point at.
#
# Usage:
#   export FASTLANE_API_KEY='fsln_...'
#   ./scripts/fastlane-mcp-probe.sh
#
# Optional overrides (all have defaults, nothing is hard-coded):
#   FASTLANE_BASE   base URL           (default https://api.usefastlane.ai)
#   FASTLANE_PATHS  space-separated candidate paths to try
#   FASTLANE_HEADERS space-separated header styles: bearer x-api-key apikey
#   FASTLANE_TIMEOUT per-request timeout in seconds (default 20)

set -u

BASE="${FASTLANE_BASE:-https://api.usefastlane.ai}"
PATHS="${FASTLANE_PATHS:-/mcp /api/v1/mcp /mcp/v1}"
HEADER_STYLES="${FASTLANE_HEADERS:-bearer x-api-key apikey}"
TIMEOUT="${FASTLANE_TIMEOUT:-20}"

if [ -z "${FASTLANE_API_KEY:-}" ]; then
  echo "FASTLANE_API_KEY is not set. Export it first; this script never stores it." >&2
  exit 2
fi

header_args() {
  case "$1" in
    bearer)    printf '%s\0%s\0' -H "Authorization: Bearer ${FASTLANE_API_KEY}" ;;
    x-api-key) printf '%s\0%s\0' -H "X-API-Key: ${FASTLANE_API_KEY}" ;;
    apikey)    printf '%s\0%s\0' -H "Api-Key: ${FASTLANE_API_KEY}" ;;
    *)         return 1 ;;
  esac
}

# A minimal MCP handshake. Nothing is created, scheduled or published by it.
INIT_BODY='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"fastlane-probe","version":"1"}}}'

probe() {
  local url="$1" style="$2" body_file status
  body_file="$(mktemp)"
  local -a hargs=()
  while IFS= read -r -d '' arg; do hargs+=("$arg"); done < <(header_args "$style")

  status="$(curl -sS -o "$body_file" -w '%{http_code}' \
    --max-time "$TIMEOUT" -X POST "$url" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    "${hargs[@]}" \
    -d "$INIT_BODY" 2>"$body_file.err")" || status="conn-fail"

  printf '%-34s %-10s %s\n' "$url" "$style" "$status"

  case "$status" in
    200|202)
      echo "  -> accepted. First 400 bytes of the response:"
      head -c 400 "$body_file" | sed 's/^/     /'
      echo
      echo "  USE THIS: url=$url  header-style=$style"
      ;;
    401|403)
      echo "  -> rejected. 401 usually means the wrong header style or key;"
      echo "     403 usually means the plan does not include API/MCP access."
      head -c 300 "$body_file" | sed 's/^/     /'; echo
      ;;
    404|405)
      echo "  -> wrong path for this account; try the next candidate."
      ;;
    conn-fail)
      echo "  -> could not connect (network policy, DNS, or TLS)."
      head -c 200 "$body_file.err" | sed 's/^/     /'; echo
      ;;
  esac
  rm -f "$body_file" "$body_file.err"
}

echo "Probing Fastlane MCP. Base: $BASE"
echo "Read-only handshake; no content is created, scheduled or published."
echo
printf '%-34s %-10s %s\n' "URL" "HEADER" "STATUS"
for p in $PATHS; do
  for style in $HEADER_STYLES; do
    probe "${BASE}${p}" "$style"
  done
done

cat <<'NOTE'

Reading the table:
  200/202 on one row  -> that url + header style is your working configuration.
  401 on every row    -> the key is wrong, or none of these header styles is right.
  403 on every row    -> the key is valid but the plan does not grant API/MCP access.
  404/405 everywhere  -> the MCP path differs; take it from Settings -> API.
  conn-fail           -> the network blocked it, not Fastlane.

Report the table (not the key) and the guide can be finalised from it.
NOTE
