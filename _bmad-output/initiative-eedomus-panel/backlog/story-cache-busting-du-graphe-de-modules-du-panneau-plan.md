---
title: "Cache-busting du graphe de modules du panneau"
type: 'bugfix'
ticket: 118
created: 2026-11-01
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: []
review_loop_iteration: 0
context: []
baseline_revision: '1e9a67aa7baf307164d856e5f6951e7682fe65ad'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** AD-17 cache-busts only the entry URL (`eedomus-panel.js?v=<manifest version>`). The 6 module specifiers imported by the entry are served by the static path with no version param, so a deploy that adds/removes an export serves a fresh entry against stale cached modules — the live 0.15.4 `shared.js doesn't provide an export named: 'menuButtonHtml'` SyntaxError. The static path serves with no cache headers, which is not "no cache" (browsers cache heuristically), and the workaround (menu-button helpers duplicated in the entry) must not become permanent pattern.

**Approach:** Serve the entry through a `HomeAssistantView` (pattern: `EedomusApiProxyView` in `api_proxy.py`) registered BEFORE `async_register_static_paths` (aiohttp matches in registration order, exact-match view wins over the static prefix). The view serves `www/eedomus-panel.js` with its relative import specifiers rewritten at serve time: `from './panel/X.js'` → `from './panel/X.js?v=<version>'`, version from the existing `_panel_module_version()` (same source as AD-17). The `?v=` param then propagates transitively through the whole module graph: a module fetched with `?v=V` resolves its own relative specifiers against its URL, which carries the query (RFC 3986). Repo files stay untouched (plain specifiers), so the node harness and direct module loads are unaffected.

</frozen-after-approval>

## Implementation Notes

Oneshot rationale: ~120–150 lines concentrated in `custom_components/eedomus/panel.py` (+ ~80 test lines extending `tests/unit/test_panel.py`, which already has the `make_hass` fixture), single-file mechanism, no cross-layer coupling.

Key decisions:
- View: `PanelEntryView(HomeAssistantView)` in `panel.py`, `requires_auth = False`, `url = "/local/eedomus/eedomus-panel.js"`, `name = "eedomus:panel-entry"`. `GET` returns `web.Response` with `content_type="text/javascript"`, body = entry file read from disk with import specifiers rewritten. Verified: HA appends views and static resources to the same aiohttp `UrlDispatcher` (first match wins, nothing re-orders), and per-view auth leaves the exposure identical to today's static serving.
- Rewrite: pure function `_rewrite_panel_imports(source: str, version: str) -> str`, regex `from '(\./[^']+\.js)'` → `from '$1?v=<version>'`. Only static `from '...'` specifiers; the entry has exactly 6 imports, all this form (verified), including multi-line blocks. Compile the regex once at module level.
- Registration order in `async_setup_panel`: `hass.http.register_view(...)` BEFORE `await hass.http.async_register_static_paths(...)`. The static path keeps serving everything else (`panel/*.js` etc.) — those still get busted transitively via the entry's `?v=` (relative specifiers inherit the base query, RFC 3986 §5.2.3).
- Read the entry file from disk at request time (not at registration) so a code-mode reload/deploy serves current content — via `hass.async_add_executor_job` (blocking I/O must not run on the event loop; HA's own static-resource builder does the same).
- Add `Cache-Control: no-cache` on the entry response: the entry URL itself carries `?v=` but its URL path is fixed, so kill heuristic staleness explicitly.
- Do NOT touch: the menu-button helpers living in the entry (0.15.4 workaround, separate cleanup), the node harness, existing specifiers in repo files.

Review findings applied (subagent pass, 2026-11-01): routing-order, transitive propagation, auth, and regex-scope claims verified against HA 2026.x source and the repo; three amendments integrated above (executor-job read, Cache-Control, test hardening below).

Corrections during build (quick lens, 2026-11-01):
- The plan's "transitive propagation" claim was FALSE: RFC 3986 drops the base query when a relative reference has a path, verified empirically (`new URL('./shared.js', '…?v=0.15.4')` → no query). First-hop-only rewriting left second-hop modules on stale heuristically-cached URLs and split `shared.js` into two module instances.
- Fix: the view now serves EVERY panel JS file (entry via `url`, modules via `extra_urls = ["/local/eedomus/panel/{filename}"]`), each with its own specifiers rewritten; the static path remains as a non-JS fallback. Same registration-order mechanism, same rewrite function.
- Guard hardening: `except (OSError, ValueError)` (UnicodeDecodeError on a corrupted file), `FileNotFoundError` → 404 for well-shaped but missing names (found by the new traversal test).
- Test hardening: the coverage guard uses a deliberately broader scanner (double quotes, side-effect imports) over the entry and every served module, replacing the tautological line-count check; new tests cover second-hop module serving, non-module paths, and the 500 paths.

## Review Triage Log

Quick lens pass, 2026-11-01 (6 findings: 3 high, 3 medium — all patched in place):
- HIGH — "transitive ?v= propagation" claim false (RFC 3986 §5.2.2: relative reference with a path takes R.query, base query dropped). Evidence: `new URL('./shared.js','…/panel/coherence.js?v=0.15.4').href` → no query. Root cause of the next two findings. Patched: view serves all www JS files, each rewritten.
- HIGH — second-hop modules (`coherence.js` → `./shared.js`, `./coherence-helpers.js`, etc.) stayed on unversioned heuristically-cached URLs; the original bug class survived. Same root cause. Patched with the view extension.
- HIGH — dual-instance split: entry would import `shared.js?v=V` while modules import `shared.js` — two ES module records for one file. Same root cause. Patched with the view extension (single versioned URL space).
- MEDIUM — coverage test tautological (line count used the same single-quote form as the rewrite regex). Patched: broader independent scanner over entry + all served modules.
- MEDIUM — second hop untested / docstrings overstated. Patched: `test_get_serves_versioned_panel_modules` + docstring fixes.
- MEDIUM — `UnicodeDecodeError` (ValueError) bypassed the 500 guard. Patched: `except (OSError, ValueError)`.
- Found during patch verification (self): well-shaped missing filename (`panel/eedomus-panel.js`) returned 500 instead of 404. Patched: `FileNotFoundError` → 404.

Known caveat for the human: the frozen Intent's last sentence ("The ?v= param then propagates transitively...") states the disproven mechanism; the implemented approach (rewrite every served file) achieves the same acceptance criterion but that frozen sentence is factually wrong and was left untouched pending renegotiation.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` — 470 existing + new tests pass, extending `tests/unit/test_panel.py` (existing `make_hass` fixture). New tests assert:
  - view route returns 200, `text/javascript`, `Cache-Control: no-cache`, and body specifiers contain `?v=<manifest version>`;
  - the repo entry file on disk is unmodified (no `?v=` in `www/eedomus-panel.js`);
  - `_rewrite_panel_imports` handles multi-line import blocks and leaves non-import strings intact;
  - registration order: `register_view` called before `async_register_static_paths`;
  - idempotency guard: a second `async_setup_panel` does not re-register the view (existing `_PANEL_REGISTERED_KEY` test extended).
- `node tests/js/test-coherence.js` — all green (repo files untouched).
- `bash scripts/hooks/pre-push` — exit 0 (black 26.10.1 / isort 9.0.2 clean).
