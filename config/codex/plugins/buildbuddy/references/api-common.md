# Common API request conventions

Use these conventions for the skill-local request examples linked from the [API index](api-reference.md).
Examples are request templates, not authorization to retrieve credentials, call a customer deployment, run an action, or mutate data.
Confirm the authorized deployment and existing credential scope before making requests.

## Shell setup

Run in Bash on the machine making the requests.
Use an already-authorized `BUILDBUDDY_API_KEY`, or the selected repository's existing `buildbuddy.api-key` configuration.
Do not print the key or run with shell tracing enabled.

```bash
BASE_URL=${BASE_URL:-https://app.buildbuddy.io}
API_KEY=${BUILDBUDDY_API_KEY:-$(git config --local buildbuddy.api-key)}
GROUP_ID='REPLACE_WITH_AUTHORIZED_GROUP_ID'
TZ_OFFSET_MINUTES=${TZ_OFFSET_MINUTES:-0}
OUT_DIR=${OUT_DIR:-$(mktemp -d -t bb-api.XXXXXX)}
mkdir -p "$OUT_DIR"

if [[ -z "$API_KEY" ]]; then
  echo 'No BuildBuddy API key is configured for this request.' >&2
fi
```

If no authorized credential exists, stop the request and report that prerequisite rather than probing another account or privileged key.
Use the group that owns the requested data; an authenticated user may belong to several groups.
`requestContext.groupId` selects context only where supported and does not bypass group or invocation permissions.
`GetUser` can return `NotFound` for an org API key; an authorized `GetGroup` lookup by organization slug can resolve the group ID when needed.

## Request and response files

UI RPC examples use `POST "$BASE_URL/rpc/BuildBuddyService/<Method>"`, `Content-Type: application/json`, and the `x-buildbuddy-api-key` header.
Public API examples use `/api/v1/<Method>` and their own schemas.
Protobuf JSON uses lowerCamelCase fields; timestamp fields accept RFC3339 strings.
Do not confuse a target pattern recorded on an invocation with an API's target-label matching semantics.

Use `curl --fail-with-body --silent --show-error` so HTTP failures do not become successful cached responses.
For a request assembled from variable inputs, write JSON with `jq` or a JSON library and pass `--data-binary @request.json`; do not interpolate untrusted text into shell code.

The existing examples use `bb_json NAME COMMAND...` to save JSON responses:

```bash
bb_json() {
  local name="$1"; shift
  local path="$OUT_DIR/$name.json"
  local tmp command_status
  if [[ -s "$path" && -z "${BB_FORCE:-}" ]] &&
      jq -e 'type == "object"' "$path" >/dev/null 2>&1; then
    cat "$path"
    return
  fi
  tmp=$(mktemp "$OUT_DIR/.${name}.XXXXXX") || return
  if "$@" > "$tmp"; then
    if ! jq -e 'type == "object"' "$tmp" >/dev/null 2>&1; then
      echo 'API response was not a JSON object; not cached.' >&2
      rm -f "$tmp"
      return 1
    fi
    mv "$tmp" "$path" || { rm -f "$tmp"; return 1; }
    cat "$path"
  else
    command_status=$?
    rm -f "$tmp"
    return "$command_status"
  fi
}
```

Choose a simple filename-safe name unique to the method, request filters, invocation, and page within this investigation.
The helper does not derive a cache key from the request.
Use separate names for old/new invocations or pages, and set `BB_FORCE=1` or remove the saved response when intentionally refreshing the same request.
Only successful JSON-object responses replace a cache file; `GetFile` returns raw bytes over HTTP and must not use this helper.

## Query limits and paging

- Keep time windows and requested result counts bounded to the investigation.
- Follow the API's actual response token with the same query when it implements pagination.
  Field presence in a proto does not prove that its handler uses it.
- For streamed logs, files, or tree responses, use that API's streaming/chunk semantics rather than a generic JSON-page loop.
- Recorded execution, build-event, and tracked-test datasets have different coverage.
  State which one supports a conclusion, and distinguish source inspection from deployed/runtime verification.
- Store response files and downloaded artifacts in the investigation directory; redact credentials and private identifiers before sharing them.
