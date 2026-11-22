# WP-15C — Control Center Shell Implementation Record

**Status:** PARTIAL IMPLEMENTATION — PR validation pending. This is not WP-15 completion or owner usability acceptance.  
**Work package:** WP-15C  
**Parent:** [Modern Unified Control Center](MODERN_UNIFIED_CONTROL_CENTER.md)  
**Existing UI inventory:** [WP15A_UI_INVENTORY.md](WP15A_UI_INVENTORY.md)  
**Navigation draft:** [WP-15B Navigation & User Journeys](WP-15B_NAVIGATION_USER_JOURNEYS.md)

## Implemented in this increment

- Added a responsive, semantic Control Center shell at `/control-center` on the existing CAD Generator loopback HTTP host.
- Preserved the existing CAD Generator root route `/` and all current CAD API routes.
- Added local static assets:
  - `src/universal_platform/engineering/static/control_center.html`
  - `src/universal_platform/engineering/static/control_center.css`
  - `src/universal_platform/engineering/static/control_center.js`
- Added a navigation foundation with active Overview, a link to the existing CAD Generator workbench, and explicitly disabled Planned entries for areas without verified UI/API integrations.
- Added mobile navigation, visible keyboard focus, skip link, reduced-motion handling and in-memory theme switching.
- Added an authenticated CAD API health check using the existing `GET /health` contract. The UI labels this specifically as CAD Generator health, not platform-wide health.
- The bearer token is held only in page memory, sent in an Authorization header, and never placed in local/session storage, cookies or URLs.
- Static assets continue to use the existing loopback request validation and restrictive response security headers. The shell does not iframe the CAD workbench or weaken frame/CSP protections.
- Added API-host tests for route delivery, headers, capability truth, root-route preservation and shell asset behavior.
- Added CI JavaScript syntax validation for `control_center.js`.

## Explicitly not implemented

- No platform-wide health aggregator, project/workspace persistence, global job API, module/tool/function catalogue API, settings schema service, diagnostics aggregator or global audit query API.
- No cross-origin connection, fixed port, public bind, external dependency, telemetry or paid service.
- No fake metrics, fake job rows, executable placeholder actions or claims of physical device control.
- No iframe integration. CAD Generator remains a separately opened specialist workbench at the existing root route.
- WP-15B information architecture remains a DRAFT pending owner review; this shell is a reversible technical foundation and does not freeze proposed navigation labels.
- No screen-reader usability study, formal WCAG 2.2 AA conformance, Firefox/WebKit/mobile-device acceptance or owner usability acceptance is claimed.

## Validation plan

1. Exact-head CI must pass workflow sanity, Python tests, repository quality and Windows process-supervisor checks.
2. Tests must verify `/control-center`, CSS/JS assets, restrictive headers, unauthenticated static delivery on loopback, authenticated CAD health and unchanged `/` CAD workbench.
3. Browser E2E should cover desktop/mobile navigation, keyboard access, theme switching, token-required state, successful CAD health check, unauthorized and unavailable service states.
4. Post-merge CI must pass on the exact merge commit.
5. Owner should test the local shell and confirm the IA before additional WP-15D–J screens are treated as accepted product behavior.

## Evidence semantics

Use PASS, FAIL, SKIPPED and UNKNOWN only for completed evidence outcomes. Pending checks are not PASS. WP-15 remains PARTIAL until all required screens, API contracts, accessibility, security, end-to-end and owner acceptance gates are complete.
