# Use your own OpenRouter key

Open **AI settings** from the editor. Paste an OpenRouter API key, select **Use key**, then **Test connection**. The status says configured before testing; only a successful completion response counts as a verified connection. Testing uses a small free-model request and counts toward your provider limits.

The available choice is **OpenRouter Free — automatic free model** (`openrouter/free`). OpenRouter selects from available free models, so the actual model can change between requests. This app does not switch to a paid model or silently fall back to server AI after your personal key fails. Free requests can be rate limited, unavailable, slow, or produce invalid model output. Review generated models and check their scientific assumptions before use. See the official [Free Models Router](https://openrouter.ai/openrouter/free) and [rate limits documentation](https://openrouter.ai/docs/api-reference/limits) for current availability and account limits.

Your key supports generation, modification, simulation analysis and questions. Personal-key refinement uses the modification API with your feedback and simulation context, then shows the proposed model in the existing review/apply control. Equilibrium search and data fitting remain numerical tools and do not receive your key. Connect agent through MCP continues to work separately.

By default, your key stays only in this tab's JavaScript memory until reload. **Remember key on this browser** explicitly opts into local storage; use it only on a trusted device. Closing the settings dialog clears its password field but keeps the configured key active. **Clear / disconnect** removes the active key and its remembered copy, restoring the app's default server AI configuration when available. Other already-open tabs keep their own in-memory state until cleared or reloaded.

For supported AI requests, the browser sends the key in an HTTP header to this app's server, which forwards it to OpenRouter. It is not put in URLs, model files, exports, workspaces, logs, or server storage. Your prompts, current model, and relevant simulation context are sent to the selected AI provider. Browser extensions and scripts running on this origin can access browser storage, so remembering a key has the same trust requirements as other browser-stored credentials.

## Verification

The checked-in tests use mocked provider responses and test memory-default credentials, explicit storage opt-in, clearing, exact same-origin header scope, free-only model selection, successful versus failed connection status, and both refinement paths. Backend tests mock HTTP provider responses, including errors and malformed results. These tests do not establish live provider availability. A live free-router connection and full generate/modify/analyze run require an operator-supplied key; do not treat configuration status or mocked tests as that verification.
