# v2.5 — Authenticated API access for agents

Decision recorded: 7 October 2026. Status: in progress. `jira api` and `--spec` discovery are implemented on the v2.5 branch with local tests and live acceptance; release work remains. Neither is available in v2.1.0. The prerequisite [v2 release gates](../v2-upgrade/acceptance.md#stable-promotion) are complete; the initial v2.0.0 release is published and verified; v2.1 adds the short command and public distribution.

## Goal and boundaries

Let a user or agent call a Jira Cloud REST endpoint through the CLI's selected identity without embedding an API token in the command, prompt, or generated script. New compatible endpoints should be callable without adding a Python wrapper for each operation.

Use a small authenticated HTTP layer with curl-like arguments, reusing the existing profile selection, scoped-token gateway, credential storage, timeout, redaction, and uncertain-write handling. Spawning curl with a credential-bearing argument would undermine the goal. The executable is `jira` from v2.1, with `jira-cli-toolkit` and `jsup` compatibility throughout v2.x.

Keep the human-friendly commands for common workflows and project-specific field discovery. Prefer generic API coverage over adding a dedicated command for every endpoint. A useful guided workflow can still justify a convenience command.

This reduces endpoint-wrapper maintenance; it does not eliminate maintenance of authentication, transport, API discovery, security, packaging, or documentation. An API payload or auth change can still require adjustments. A model's remembered API knowledge is not a substitute for current documentation and project metadata.

Keeping credentials out of the invocation reduces accidental exposure. It does not isolate a token from an agent allowed to read credential files, access the OS store, run arbitrary programs as the same user, or modify the CLI. Strong isolation needs an enforced tool boundary or a credential broker under a separate security identity. Do not claim that the local command alone provides that boundary. An authorized agent can also exercise the permissions of the configured Jira account; hiding the token does not restrict those permissions.

## Proposed command contract

Examples are design targets:

```sh
# Read using a saved identity; no token in the command.
jira api /rest/api/3/myself --profile work
jira api /rest/api/3/issue/BUG-703 --profile work

# Inspect an operation before constructing its payload; no Jira auth required.
jira api /rest/api/3/issue -X POST --spec
jira api /rest/api/3/issue -X POST --spec > issue-create-spec.json

# Make a request with a JSON file, or JSON received on stdin.
jira api /rest/api/3/issue -X POST --data @issue.json --profile work
jira api /rest/api/3/search/jql -X POST --data @- --profile work

# Supply query parameters explicitly; the CLI performs URL encoding.
jira api /rest/api/3/project/search --query maxResults=20 --profile work

# Multipart APIs also need a generic input path.
jira api /rest/api/3/issue/BUG-703/attachments -X POST --form file=@proof.txt --header X-Atlassian-Token:no-check --profile work

# Refresh public API discovery metadata separately from executable updates.
jira api spec refresh
```

GET is the default; POST/PUT/PATCH/DELETE/HEAD/OPTIONS are explicit. Data does not silently change the method. `-d` aliases `--data`. Endpoint specs are selected by path and method, including concrete paths matched to templates. An explicit mutation invocation is authorization for that request: generic API calls must not introduce an unconditional confirmation dialog that prevents scripted use. Account permissions, upstream validation, and any enforced agent policy still apply.

Requests target relative Jira API paths on the selected trusted site or its scoped-token gateway. Caller-supplied absolute URLs, alternate hosts, auth/header overrides, and credential-bearing redirect forwarding are rejected. Query values use `--query`; request paths and data remain separate. API discovery fetches approved public sources without attaching Jira credentials.

Successful JSON responses retain their upstream shape, including arrays/scalars. Empty responses, response status/headers, non-JSON responses and binary output need explicit documented behavior. Errors use stable exit codes and a redacted error object on stderr so stdout remains suitable for piping raw responses. Auth failure never triggers credential switching or automatic replay of a mutation. The transport must not assume that every endpoint returns a JSON object or list.

Start with one request/one response. Do not promise automatic pagination of arbitrary endpoints: Jira uses several pagination protocols. Keep it explicit, and continue using existing paginated convenience commands when useful.

## Delivery checklist

### Finish v2 first

- [x] Record the user's decision to prioritize authenticated API access and spec discovery in v2.5.
- [x] Complete interactive macOS native credential-store acceptance and record the user's successful migration/live status evidence in the v2 roadmap.
- [x] Complete v2 review/merge, stable version preparation, regression/build checks, and stable GitHub publication/latest-update verification.

### Shared request layer and API command

- [x] Define parser grammar for `api PATH`, explicit methods, repeated query parameters, JSON data/file/stdin, raw bodies, multipart fields/files, response metadata and output files; keep discovery subcommands unambiguous.
- [x] Reuse the existing identity resolver and trusted API base, including scoped-token cloud-ID routing. Do not introduce another auth or credential configuration mechanism.
- [x] Add a shared request/response path that supports raw bodies, scalar/array JSON, empty responses and non-JSON content without breaking existing grouped/legacy command contracts.
- [x] Validate relative paths and trusted origins; reject URL/host/auth/cookie/proxy overrides, control characters and ambiguous path forms. Disable credential-bearing redirects and raw curl argument passthrough.
- [x] Support permitted custom headers for API-specific needs while retaining control over authentication, host, content framing and transport settings.
- [x] Implement data parsing and bounded file/stdin reads without shell evaluation. Preserve supplied JSON rather than inventing or discarding endpoint fields.
- [x] Support generic raw/multipart request bodies with explicit content types and bounded uploads, including Jira's required attachment header, without writing another endpoint wrapper.
- [x] Define stdout/stderr, status/headers, JSON/error/exit-code and binary-download contracts; keep secrets out of diagnostics, traces and process arguments.
- [x] Preserve bounded safe-read retry/rate-limit handling. Unknown writes are not replayed; raw POST search is not assumed safe merely because some search operations are read-only.
- [x] Keep headless behavior deterministic when credential-store access requires OS approval; document onboarding once and agent invocation thereafter.
- [x] Confirm that a previously unwrapped endpoint and an unknown-to-the-cached-spec path can be called without adding endpoint-specific Python code.

Implementation notes: `jsup/api.py` validates and sends the request; `Jira._send` in `jsup/client.py` is the shared transport (timeouts, redirect refusal, safe-read retries, unknown-write reporting) under both `jira api` and the existing commands. `PATH` values that are not `/rest/...` paths, including `spec`, are reserved for discovery subcommands. Headless onboarding is documented in [the usage guide](../../usage.md#setting-up-an-agent-or-script-once).

Live read acceptance, 8 October 2026, `work` profile on investorsindia.atlassian.net, run without a terminal (keychain read silently, no dialog): `myself`, `serverInfo`, project BUG, board 1523 and its configuration and active sprint, POST `search/jql` from inline and stdin JSON, project search with repeated `--query`, project statuses (top-level array returned unchanged), `--include` (cookies redacted), HEAD, a 404 as a structured stderr error, and a dot-segment path rejected before sending. An 11.7 MB attachment downloaded with `--output` matched its declared size, and a second save refused to overwrite. No output file contained the token or a derived form. Write acceptance used a reversible issue property on BUG-703 (PUT 201, read back, DELETE 204, then 404) instead of creating issues, comments or attachments, so no one was notified. Fixes from this run: the attachment-content redirect error now suggests `--query redirect=false` and drops the signed token from the reported location, and `--output` destinations are checked before the request is sent.

### API discovery and freshness

- [x] Verify the official OpenAPI sources/formats for Jira platform, Software and Service Management; document covered API families and unsupported sources explicitly.
- [x] Add `--spec` lookup by path/method, including template matching and bounded resolution of schema references within approved documents.
- [x] Expose parameters, request/response schemas, documented permissions/scopes, operation ID and source metadata without claiming all project-specific validators are represented.
- [x] Cache validated documents with source, fetch time, version/hash and conditional-request metadata; support explicit refresh, clear stale/offline behavior and bounded downloads/parsing.
- [x] Make specs/help available without resolving secrets or calling an authenticated Jira endpoint. Never fetch arbitrary reference URLs with Jira credentials.
- [x] Keep schema discovery advisory for raw requests. A missing/stale spec must not prevent a valid new API call; spec errors must not fabricate an operation definition.
- [x] Document that issue fields, transitions, scopes, licenses and project permissions can require separate runtime discovery even when an OpenAPI operation exists.

Discovery notes, 8 October 2026: the official documents are OpenAPI 3.0.1 at developer.atlassian.com — platform (423 paths, `/rest/api/3`, plus Connect and Forge paths), Software (78 paths: `/rest/agile/1.0` and the DevOps `/rest/*` families) and Service Management (50 paths, `/rest/servicedeskapi`). All references are local `#/components/...`. The CDN returns an ETag only for uncompressed responses, so refreshes request `Accept-Encoding: identity` to make conditional checks work. 63 literal platform paths also match a template (for example `/attachment/meta` and `/attachment/{id}`), so literal segments take precedence. Live: lookups for createIssue, getIssue (concrete key), getAttachmentMeta, getAllSprints and getCustomerRequests returned the expected operations, and a second refresh answered 304 for all three documents.

### Verification, docs and release

- [x] Test verbs, query encoding, inline/file/stdin JSON, raw/multipart uploads, scalar/array/empty/non-JSON responses, metadata, binary output and errors with local deterministic fixtures.
- [x] Test origin/path/header restrictions, credential redaction (including derived auth values), malicious spec references, malformed/stale specs and absence of credentials from child-process arguments/logs.
- [x] Test profile isolation, scoped routing, permission denial, rate limits, unknown mutation outcomes and strict noninteractive behavior; do not regress existing commands.
- [x] Test cached/refresh/offline operation discovery and a newly introduced endpoint without a CLI-code change.
- [x] Run authorized live read acceptance in BUG. Obtain a disposable issue/cleanup arrangement before adding new write acceptance; do not create more issues under the already-used two-issue test budget.
- [x] Add README and help examples for agents, scripts, request construction, spec discovery, project metadata, trust boundaries and troubleshooting. Mark when a capability is actually shipped.
- [x] Document the difference between secret-free invocation and enforced secret isolation; show least-privilege Jira access and an external tool-policy/broker option when stronger isolation is required.
- [ ] Run full regressions, wheel/sdist and installed smoke checks before milestone pushes; verify the CI/native matrix, published manifest and real updater on a v2.5 candidate.
- [ ] Validate the compatibility path from stable v2, then publish a tested v2.5 release through the same GitHub pipeline and verify stable selection.

## Completion criteria

- [ ] An agent can inspect a current endpoint spec and make an authenticated call without putting a token in its invocation or prompt.
- [ ] A compatible endpoint absent from the convenience commands works without an endpoint wrapper or CLI upgrade.
- [ ] HTTP failures and unknown write outcomes are explicit; normal requests do not silently change auth identities, destinations, payloads or pagination.
- [ ] Existing human workflows remain compatible; documented discovery freshness and security boundaries match verified behavior.

## References

- [Jira Cloud platform REST v3 and OpenAPI reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira Software REST reference](https://developer.atlassian.com/cloud/jira/software/rest/intro/)
- [Jira Service Management REST reference](https://developer.atlassian.com/cloud/jira/service-desk/rest/intro/)
- [Jira Cloud authentication for personal API-token calls](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/)

The provided Notion screenshot is inspiration for the interface. It demonstrates request and spec commands; it does not establish Notion's credential isolation, underlying implementation, spec freshness, or maintenance cost.
