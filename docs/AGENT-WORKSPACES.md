# Agent-driven modeling pages

The user's agent supplies reasoning, model construction and interpretation. MCP provides small, explicit operations around the same model schema, numerical engine and visible editor. Interactive pages require the remote HTTP/SSE connection; an isolated local stdio process has no shared page memory. Stdio numerical/library tools remain available.

## Workflow and lessons retained

1. Discover candidates with the compact paginated `list_models` index, then `get_model` for selected full definitions. Inspect source, units, initial conditions and flow endpoints. A familiar title or generic source link is not scientific evidence.
2. `open_workspace(model_id=...)` copies an example, or pass `model_json` authored by the user's agent. The tool returns a private `page_url` and `workspace_key`. Open the page and wait for `inspect_workspace.browser.connected` and an applied revision. A user can instead choose **Connect agent → Connect this page** and privately give those instructions to their agent.
3. Prefer `edit_workspace_elements`: one atomic list of explicit additions/field changes, by stable element ID, with `expected_revision`. All unmentioned elements, tables, units, sources and settings survive. There are no implicit deletions. Update dependent references explicitly when renaming. `update_workspace_model` is a full replacement for cases where replacing the complete private draft is intended.
4. Inspect returned validation before running. Invalid equations are visible draft diagnostics, never substituted with zero. `run_workspace` simulates the exact current revision and publishes those same results to the page; it does not perform a second stochastic run in the browser. Existing simulation bounds still apply.
5. `set_workspace_view` selects diagram, chart, analytics or inputs, optionally fits the diagram or selects an element. It cannot execute arbitrary JavaScript or navigate to an arbitrary URL. Check `browser.applied_revision`, `browser.view`, `browser.selection` and `browser.error`; a queued command alone is not proof that the page changed.
6. Compare scenarios, smaller timesteps and conservation/domain expectations using the numerical tools. State which assumptions were supplied and which sources remain unverified. Analytics is descriptive; finite output and a nearly stable tail do not establish scientific validity or equilibrium.
7. `close_workspace` or the page's **Disconnect** revokes the capability and erases the temporary session. The current page draft remains visible. **Save** is the user's separate explicit action to write a library copy.

## Concurrency and persistence

The revision is an optimistic concurrency fence, not an instruction to retry blindly. Inspect the latest state after a conflict. The page pauses remote application while a user edits a field. If both the page and agent changed the model, it offers **Keep page draft** or **Load agent draft**; it does not silently discard either side. View-only changes do not require discarding a user's draft.

These sessions are memory-only and scoped to one server process. They expire after one idle hour, have a maximum lifetime of 24 hours, and end on application restart. The current deployment uses one application worker; multiple workers/load balancers require an explicitly designed shared ephemeral store. Sessions are capped at 16, model payloads at 256 KiB, and aggregate stored serialized results at 32 MiB. Snapshot polling omits unchanged models/results. Heavy numerical runs remain subject to the engine's separate limits.

No workspace tool writes model files, SQLite model data, credentials or a user's browser storage outside its temporary session connection. Saving still uses the pre-existing shared public model store, not private account storage.

## Capability handling

Each session uses an independent random 256-bit secret; only its hash is retained server-side. IDs alone cannot authorize access. Tokens are carried in an Authorization header; the opening URL uses a fragment, which the page removes from browser history after reading. The page retains the key in sessionStorage for reload continuity, not localStorage. Responses are not cacheable. Treat the returned private URL/key like a control capability and share it only with the intended agent. It grants access to one temporary workspace, not the server or saved library.

The built-in AI draft tools are retained for compatibility and are optional. No page-driving, numerical or deterministic analytics operation requires a server-side AI provider. The agent workflow is independent of optional server-side provider credentials; those credentials are never copied from another product.

## Verification

`tests/test_workspaces.py` checks session isolation, expiry, bounded memory, exact-result publication, explicit selection, transactional preservation, stale revisions, token transport and no saved-model writes. `scripts/check_mcp.py` exercises the page tools through real HTTP/SSE clients and verifies an explicit error for page tools in isolated stdio. `scripts/check_page_workspace.py` performs a real MCP → browser → acknowledgement loop, including changed equations, retained source/units and an exact known result. Its handoff file contains a temporary secret and must not be committed.
