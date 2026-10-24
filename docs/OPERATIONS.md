# Preservation and release contract

Keep deployment-specific host identities, secret locations and private receipts outside public source control. Revalidate the actual host/service before changing it.

The editor, library, saved-model listings, JSON/XMILE imports and exports, settings, diagrams, chart types, analytics, AI/feedback options, mobile panels and legacy MCP SSE URLs remain supported. Library saves create a copy rather than overwriting templates.

Back up the exact code and scoped web configuration before release. Compare model/data hashes before and after. Deploy only reviewed runtime files; never overlay the checkout's models/, models.db, .env or Git metadata over production. Preserve any production-only models and existing source changes. Run staged imports/numerical checks using the target environment, and use a bounded readiness check after a scoped application restart. Static-only updates do not require restarting the application. Verify HTTPS API, real MCP clients, visible page actions and related services afterward. Roll back scoped code/config only, in reverse release order; never restore stale user data.

The public deployment currently uses one application worker for ephemeral workspace memory. Sessions require HTTP/SSE, expire after one idle hour or restart, and are never saved implicitly. Multiple workers need a shared ephemeral store design.

See TESTING.md for checks, UI-QA.md for platform coverage limitations, MODEL-INVESTIGATION.md for unresolved definitions and AGENT-WORKSPACES.md for the page protocol.
