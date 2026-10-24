# Independent local sensitivity transport review

Review scope: HTTP/MCP adapters and process-shared quota, independent of the core mathematical review. UI implementation is authored by this reviewer and requires a separate reviewer; this document does not approve the UI.

## Admission finding corrected

The initial frozen transport converted submitted dictionaries through existing permissive Model schemas before core admission. An independent probe supplied top-level `events` and stock-level `events`; both disappeared without rejection. A narrow pure-autonomous sensitivity report must reject unknown semantic fields rather than report derivatives for silently changed input. The final implementation recursively checks declared Pydantic schema fields before conversion, retaining arbitrary contents only inside declared plain metadata maps. Independent repeated probes now reject root, stock and full time-settings events with typed invalid_request errors and precise locations. Nine added regressions cover HTTP/MCP schema locations, retained source diagnostics, unknown source-document fields and the already strict settings patch.

## Final approval

**Approve the exact transport snapshots below.** Independently reran the final32transport tests together with77core tests and the actual-JS UI check:110passed10.55s. One existing Pydantic settings forward-reference warning remains. No further mandatory transport findings. This approval is specific to the reviewed bounded scalar core contract and shared POSIX host/filesystem quota; it does not independently approve the UI.

| File | SHA256 |
|---|---|
| app/main.py | `662c8a1b11dcfe75d9ec14f1172c6f714246c38d593832a481263e2493a8a18d` |
| app/mcp_server.py | `881d0f5017a3324f6f335fefcfd5727c8ca179bf657d8f74f6f728e22a9f3d42` |
| app/sensitivity_transport.py | `d7620943d016e0d1fa8deaa1ab294a01a8106eca92b410e740c1ebe39ff53571` |
| tests/test_sensitivity_transport.py | `4b7b64b8ab711e0bca391873e28e2a6a51f2c3d8879e14a3b081449a621896cb` |
| docs/LOCAL-SENSITIVITY-TRANSPORT.md | `c8681a6075f7369e444abf222202448c5dba2e0e983a9c4f7dad1d4a10f848ca` |

## Verified behavior

Read the complete adapter and MCP entry point. Independently reran all23 transport tests, then together with the focused UI test:24 passed. Tests exercise actual FastAPI and MCP SDK requests, byte limits, strict parameter values, typed failures, worker cancellation/disconnection cleanup, independent-process shared flock contention and crash release, and unsafe quota path/inode rejection. The quota retains its inode and descriptor through worker cleanup, so cancellation does not create a second execution slot while the first child remains alive. Secure directory walking rejects symlinks; the lock requires private ownership/mode, a regular inode and one link. Configuration must identify the same filesystem path across service processes; this is a host/filesystem quota, not a distributed cluster quota.

HTTP body bytes are bounded before JSON decoding, caller-owned MCP objects pass the core bounded walker before serialization, and selectors require exactly one model source. No model storage writes or simulation-result assignment occur in the adapter. Existing core admission, per-run deadline and aggregate work reservations remain authoritative. Cancellation waits for the child cleanup task before releasing the shared slot. A client abort requests cancellation; it is not an acknowledgement of completed cleanup.
