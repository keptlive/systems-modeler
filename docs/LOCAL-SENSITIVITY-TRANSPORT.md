# Local sensitivity HTTP and MCP transports

Additive read-only exposure of the independently reviewed [core contract](LOCAL-SENSITIVITY.md). Existing simulation, feedback, analysis, workspace, tuner, import/export and MCP routes/tools remain intact. No user interface, model application/save or deployment is included.

## HTTP

POST /api/sensitivity/local with UTF-8 JSON, at most2097152bytes total including all options:

```json
{
  "model": {
    "id": "example",
    "stocks": [{"id":"x","name":"Population","initial_value":3}],
    "flows": [{"id":"f","name":"Growth","equation":"rate*Population","to_stock":"x"}],
    "variables": [{"id":"p","name":"rate","equation":"0.4"}],
    "time_settings":{"start":0,"end":2,"dt":0.02,"integration_method":"rk4"}
  },
  "parameters": [{"id":"p","step":0.002}],
  "output_stock_id": "x",
  "timeout_seconds": 10,
  "max_work_units": 2000000
}
```

Provide exactly one model object or saved model_id. Existing partial time_settings overrides are optional and applied to a copy. parameters contains1–8 unique existing constant variable IDs and finite positive absolute steps. A stock ID is mandatory; names are not selectors. timeout_seconds is finite positive and at most30; max_work_units is a strict integer from1 to2000000. Extra root/parameter fields, booleans/string numeric steps and nonfinite JSON reject. Core admission rejects unsupported model/grammar features rather than approximating or dropping them.

The body is streamed with a byte limit before JSON parsing, independent of Content-Length. Invalid/nonfinite JSON, bounded-node/depth source preflight and strict DTO validation precede execution. Model metadata/source input also receives the reviewed core pre-dump limits. Saved model lookup preserves the existing storage semantics and does not write.

Successful transport delivery returns HTTP200 with the core report unchanged. Its status may be complete, partial_failure, baseline_failed, deadline_exceeded, cancelled or worker_failed: clients must inspect it. Failed rows have no derivative; interrupted reports have no apparently valid partial rows. Reports contain sample coordinates/outputs, raw derivative/elasticity diagnostics, selected settings, conservative reservations, successful engine work and hashes/contract provenance. See core docs for the exact numerical/resource meanings. A well-formed report is not scientific calibration or a global importance index.

Admission errors return422; missing saved model404; oversized transport body413; occupied shared slot429; unavailable secure quota or worker startup503. Error JSON is `{"detail":"bounded message","failure":{"code":"typed_code","message":"bounded message"}}`. Codes include invalid_request, invalid_selector, invalid_step, unsupported_model, capacity, model_not_found, sensitivity_busy, quota_unavailable and worker_unavailable. Do not treat a busy response as an experiment failure or silently run outside the quota.

After body consumption, the HTTP disconnect watcher sets the core cancellation Event. The worker is terminated/joined before the experiment slot releases. Async handler cancellation is also caught, signals the Event and shields cleanup before reraising cancellation. The watcher is cancelled/joined after completion. No server-side run continues merely because a client stopped waiting.

## MCP

The additive read-only tool is analyze_model_sensitivity:

```json
{
  "model_json": {"...":"same model object as above"},
  "parameters": [{"id":"p","step":0.002}],
  "output_stock_id": "x",
  "timeout_seconds": 10,
  "max_work_units": 2000000
}
```

Exactly one model_json object/JSON string or model_id; optional time_settings uses the same patch semantics. Model plus options are subject to the same combined2MiB tool-level gate and source-node/depth bounds. MCP SDK schema validation also bounds parameter count/IDs/numeric controls. As with other tools, the SDK transport has already parsed its tool envelope before dispatch; a future front-proxy global request limit should bound that outer envelope too. The tool never calls an AI provider.

Reports use the same core fields/statuses as HTTP. Admission, busy and infrastructure errors are flagged ToolError with the same detail/failure JSON. Tool annotations retain readOnlyHint=true, destructiveHint=false, openWorldHint=false. SDK task cancellation retains the shared quota until the core thread/child has finished cleanup. Streamable HTTP, legacy SSE and stdio registrations remain available.

Generated defaults such as missing model/element IDs can differ between independent submissions; to compare exact model hashes across transports, submit a full snapshot with stable IDs. Timestamp fields are excluded from the normalized core model hash.

## Deployment-wide process quota

Both transports call the same service and hold a POSIX flock for the whole admitted core operation, including cancellation cleanup. Default directory:

`/tmp/stockandflow-sensitivity-<effective UID>`

It deliberately contains no PID or request-specific namespace. All HTTP workers, MCP workers and stdio processes running as the same service user on the same host/filesystem therefore share one slot. Busy acquisition is nonblocking and immediately rejects429 / sensitivity_busy. There is no unbounded work queue. The core's narrower per-process thread semaphore remains an additional guard.

An operator can set SYSTEMS_MODELER_SENSITIVITY_QUOTA_DIR to a common absolute directory (at most512characters) across all server processes. Provision its parent; the service can create only the final directory. Every path component is traversed using directory descriptors/O_NOFOLLOW. The final directory must be owned by the effective service UID with exact0700 mode. The fixed slot.lock must be a service-owned single-link regular file with exact0600 mode and O_NOFOLLOW/O_CLOEXEC. Newly created directory/lock modes are set explicitly; existing insecure permissions, symlinks, hardlinks and inaccessible configuration fail closed with503. No automatic insecure fallback or permission repair occurs.

**Never unlink, replace or rotate slot.lock or its directory while any service process is running.** Keeping one persistent inode is necessary for flock mutual exclusion. Kernel descriptor closure releases a lock after process death. Worker spawn does not inherit the lock descriptor across exec. The parent retains it until child termination/join. Cleanup never removes the quota inode and never uses recursive deletion.

This is a genuine cross-process slot on a shared local POSIX filesystem, not a cross-host distributed semaphore. If multiple hosts/containers form one deployment, mount the same lock filesystem with reliable flock semantics and run under the same service UID, or add a separately reviewed distributed admission service. Differing quota directories/UIDs/namespaces create separate pools; that is an operator configuration error if one combined slot is required. Tests prove independent processes contend on the shared path; they do not certify arbitrary network-filesystem lock semantics.

The quota does not alter the core's total-work, source, AST, output, process deadline or memory bounds. It does not serialize existing unrelated simulation endpoints. Deployment must supply its existing outer webserver request limits and host process/resource controls. No new saved model or library/database data is written.

## Verification

tests/test_sensitivity_transport.py covers real FastAPI requests and MCP registration/dispatch, a real stdio SDK handshake/tool invocation, saved-model/partial-setting resolution, HTTP/MCP numerical parity, byte/nonfinite/selector errors, explicit baseline/deadline failures, active client disconnect, async cancellation cleanup, and existing route/tool preservation. Separate OS processes prove HTTP and MCP both see an occupied slot and that process termination releases it. Symlink/hardlink/mode/parent traversal and persistent-inode probes verify fail-closed behavior. Storage create/update paths are trapped.

Combined scoped verification before review:
`pytest -q tests/test_sensitivity_transport.py tests/test_engine_mcp.py tests/test_local_sensitivity.py`:
111 passed in8.81s, one preexisting Pydantic MCP lifespan forward-reference warning.

Independent transport/resource review is required before deployment or UI integration. No deployment was performed.


## Strict submitted-model semantics

Transport review found that the general Model validator ignores unknown keys, which could discard submitted event/initializer semantics before narrow sensitivity admission. Raw submitted models now receive recursive declared-schema key checks before Model validation: Model, stock/flow/variable, position, complete time settings and source-document objects reject unknown keys. Declared arbitrary dictionaries such as source-document diagnostic maps retain their contents and remain byte/node/depth bounded. TimeSettingsPatch already forbids unknown fields. Existing simulation/import validators are unchanged.

HTTP and MCP regression cases submit unknown root/stock/flow/variable/position/time-settings semantic keys and require typed422/tool errors rather than apparently valid derivatives. Additional checks preserve arbitrary declared diagnostics and reject unknown source-document schema fields. Saved Model selectors retain existing storage resolution; no active data migration or rewriting occurs.
