# Public retrieval API

Use this reference for the documented `api.v1.ApiService`, not the similarly named UI RPCs in `BuildBuddyService`.
See the [official public API documentation](https://www.buildbuddy.io/docs/enterprise-api/) and [common request conventions](api-common.md) for transport and credential handling.
The examples below are JSON request bodies for `POST /api/v1/<Method>` with an already-authorized API key.
Replace illustrative IDs with the selected invocation's actual values.

## GetInvocation

Fetch one invocation:

```json
{"selector":{"invocationId":"INVOCATION_ID"}}
```

Or discover permitted invocations associated with a commit:

```json
{"selector":{"commitSha":"COMMIT_SHA"}}
```

The current handler scopes the query to the authenticated group and permission checks.
When both invocation ID and commit SHA are set, both restrictions apply.
Optional `includeMetadata`, `includeArtifacts`, `includeChildInvocations`, and `includeBuildToolLogs` request additional data.
The invocation's recorded `pattern` is not an expanded target inventory.

## GetTarget

List the targets recorded in one invocation:

```json
{"selector":{"invocationId":"INVOCATION_ID"}}
```

Fetch one exact label:

```json
{"selector":{"invocationId":"INVOCATION_ID","label":"//pkg:target1"}}
```

Or select targets containing one exact tag:

```json
{"selector":{"invocationId":"INVOCATION_ID","tag":"selected"}}
```

Important implementation details at the checked revision:

- One invocation is required; there is no invocation array, label array, or Bazel target-pattern expansion.
  `//folder3/...` is compared as a literal label, not expanded.
- The optional filter precedence is `label`, then `tag`, then `targetId`, not an AND intersection.
  Set only the filter mode needed by the request.
- The current target ID is its label.
  Prefer the explicit `label` field rather than relying on older encoded-ID examples.
- Rows are built from received configured-target events and updated from completion/test-summary events.
  Build and test targets may appear, but missing events or incomplete invocations can leave targets absent.
  This is not a repository or transitive-dependency inventory.
- Results are keyed by label within the invocation, not configuration, aspect, shard, run, or attempt.
  Retain invocation ID when combining results across invocations.
- Although the proto declares `pageToken` and `nextPageToken`, the current handler ignores the request token, applies no explicit result-page limit, and emits no continuation token.
  Do not invent pagination or infer stable ordering from its map-backed result list.

For a union of exact labels and a simple recursive directory selection, enumerate each invocation and filter the returned labels locally.
For example, `//folder3:` includes the package itself and `//folder3/` includes its subpackages without matching `//folder30`.
Expand patterns with Bazel in the matching checkout only when a full expected-label set is required, including targets absent from the recorded invocations.

## GetAction

Fetch recorded action/file details for an exact target in one invocation:

```json
{"selector":{"invocationId":"INVOCATION_ID","targetLabel":"//pkg:target1"}}
```

Additional exact selectors are `targetId`, `configurationId`, and `actionId`.
Results include configuration/action identity, files, and test `shard`, `run`, and `attempt` where available.
Use these fields for recorded test-attempt details rather than treating one `GetTarget` row as one execution attempt.
This public API is distinct from UI `GetExecution` and `SearchExecution`, which return remote execution records.

## GetLog

```json
{"selector":{"invocationId":"INVOCATION_ID"}}
```

Read `log.contents`, then pass a nonempty response `nextPageToken` as the next request's `pageToken` with the same selector.
Unlike public `GetTarget`, this handler uses the token to retrieve the next log chunk.

## GetFile and GetFileRange

`GetFile` reads a URI returned in a recorded file reference:

```json
{"uri":"bytestream://CACHE_HOST/INSTANCE/blobs/DIGEST_HASH/SIZE_BYTES"}
```

Over HTTP, `/api/v1/GetFile` returns the file bytes directly; save them as an artifact rather than parsing or caching them as JSON.
The gRPC method streams `GetFileResponse` messages.

For a bounded byte range, call `/api/v1/GetFileRange`:

```json
{"uri":"bytestream://CACHE_HOST/INSTANCE/blobs/DIGEST_HASH/SIZE_BYTES","start":"0","end":"4096"}
```

`start` is inclusive and `end` is exclusive, with `end > start` and a maximum requested range of 16 MiB.
Use a range compatible with the actual file size.
The JSON response's `data` bytes field is base64-encoded.

## Source and scope

Behavior was checked against BuildBuddy revision `017562c412cbabe1a7aecb70334a90dca28cfce3`, not a particular deployed instance.
Relevant sources:

- [Public service and transport](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/proto/api/v1/service.proto).
- [Request/response schemas](https://github.com/buildbuddy-io/buildbuddy/tree/017562c412cbabe1a7aecb70334a90dca28cfce3/proto/api/v1).
- [API handlers](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/enterprise/server/api/api_server.go).
- [Target construction and selector matching](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/server/api/common/common.go#L158-L224).

This retrieval reference does not provide mutation recipes for `DeleteFile`, `Run`, `ExecuteWorkflow`, or API-key creation.
Use the specific authorized workflow for those operations.
