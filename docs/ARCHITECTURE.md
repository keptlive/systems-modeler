# Architecture and numerical contract

The FastAPI application serves the existing D3 editor and REST API. The companion library's source is `sites/library/index.html`. Browsers list compact metadata through `/api/models/catalog`, then fetch complete definitions only for details/import. The legacy `/api/models` full-list response remains available. The catalog invalidates on file names, sizes and nanosecond modification times; it does not replace the model store.

JSON model files are the model store. Saves use atomic replacement. Lookup tables and settings survive storage and local browser saves. Production `models.db` is preserved; this release does not migrate or overwrite it. Existing server-side model CRUD remains a shared public store; it is not a private per-user account system. Browser saved-model listings are local to the browser. Saving a library template creates a copy rather than updating the shared template.

REST simulations and MCP use the same integration entry point. Every run reports errors for unknown references, invalid equations and non-finite results. Euler and RK4 are explicit choices. The default grid includes the start and stop, with a shorter final interval when needed. Every recorded flow/algebraic value corresponds to the recorded stock state and time. Validation checks structure and computation, not scientific correctness.

Numerical resource bounds are 500 elements, 10,000 integration intervals and 1,000,000 element intervals. Model discovery and export remain available for models whose default runs exceed these bounds. Increase dt or narrow the time range explicitly to simulate them. Stateful and random functions require Euler until a verified RK4 state implementation is available.

MCP exposes Streamable HTTP and legacy SSE through the same FastMCP instance and shared lifecycle. Transport host/origin checks include the actual public domains while retaining DNS rebinding protection. The stdio entry point is `python -m app.mcp_server`. Numerical tools never write model files or invoke AI. AI drafting/modification use the existing configured provider, return drafts, and do not save them.

The transport SDK is deliberately pinned to the deployed/tested 1.26.0 API. `requirements-lock.txt` records the local verification environment. A future SDK major upgrade must rerun the real protocol checks; changing package versions alone is not modernization.

## Private agent/page sessions

HTTP/SSE MCP clients and the browser share capability-scoped, expiring in-memory workspaces. Small typed edits preserve unmentioned inputs; complete draft replacement is explicit. Every mutation checks a revision. The browser reports applied revisions and actual visible view, and concurrent model edits require a visible choice. One exact simulation result is shared with the page, avoiding duplicate stochastic runs. No workspace operation saves to the library or requires a server AI account. See AGENT-WORKSPACES.md for the protocol, limits and single-worker boundary.

## Scientific and import boundaries

Legacy library entries include generated examples with incomplete references and unverified source claims. Neither finite output nor a generic source link proves fidelity to a published model. The audit records exact model/source hashes and distinguishes full default runs from short smoke checks. Investigate failed examples before editing their equations. Never turn an error into zero or clamp a stock merely to make a test pass; signed stocks can be intentional.

XMILE support covers scalar stocks, flows, auxiliaries, initial equations, Euler/RK4 settings and graphical functions. Arrays/nested models are rejected explicitly. Imported graphical functions use XMILE's interpolation type; older JSON tables retain their historical extrapolation default. See the independent engine review for tested state semantics and limitations.

Standards used for verification: [OASIS XMILE 1.0](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html), especially simulation specifications and graphical functions; [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
