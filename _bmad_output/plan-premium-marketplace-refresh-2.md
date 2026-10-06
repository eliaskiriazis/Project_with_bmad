---
title: 'Premium Guitar Marketplace Homepage Refresh'
type: 'feature'
ticket: ''
created: '2026-10-06'
status: 'built'
baseline_revision: '12ea0e856c02248a013a9c6ef8927feaffd915f3'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The marketplace homepage needs a more premium, current visual presentation and stronger guitar imagery to make browsing feel curated and trustworthy.

**Approach:** Redesign the homepage as an image-led, editorial storefront with a clearer hero, elevated product cards, and polished responsive navigation and search. Keep the marketplace's existing bilingual content, browse-only demo safeguards, image attribution, real listing search, and detail-page flows intact.

**Decision:** Use appropriately licensed guitar imagery rather than Thomann product photos; retain the existing credited Commons images or replace them only with assets whose licenses permit this use.

## Boundaries & Constraints

**Always:** Keep all user-facing homepage content available in English and Greek. Preserve working search parameters, listing/detail links, demo-only labels, existing listing behavior, keyboard focus visibility, responsive behavior, and accurate creator/license attribution for every demo image.

**Never:** Copy, rehost, or hotlink Thomann images without confirmed permission or a license allowing this use. Do not alter checkout, listing inventory, account flows, or unrelated page designs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Homepage in either language | Visitor opens `/` or selects Greek | Editorial hero, search, demo and real listings render in the selected language | No untranslated new labels |
| Filtered search | Visitor submits any existing homepage filter | Matching cards and empty state retain the refreshed presentation | No filter is lost or misrepresented |
| Photo rights unresolved | No permission/license is confirmed for Thomann images | Do not use Thomann assets; use approved licensed alternatives after user decision | Record accurate source and license details |
| Narrow viewport or keyboard navigation | Mobile-width screen or keyboard-only input | Layout reflows without overflow; links, inputs, and buttons remain perceivable and operable | No clipped controls or missing focus indication |

</frozen-after-approval>

## Code Map

- `app/templates/home.html` -- Homepage hero, search controls, demo/live listing cards, and image-credit link; preserve template data and routes while changing presentation.
- `app/templates/base.html` -- Shared header and page shell; make only homepage-needed navigation refinements and preserve auth/language actions.
- `app/static/css/style.css` -- Current visual system and responsive rules; establish the refreshed homepage styles without regressing other marketplace pages.
- `app/i18n.py` -- English/Greek translation map for any new visible text.
- `app/static/images/demos/` and `ATTRIBUTION.md` -- Current six local CC-licensed photos and source/author/license records; update only with images whose rights permit the use.
- `tests/test_app.py` -- Homepage bilingual, search, demo-card, attribution, and browse-only integration coverage.
- `README.md` -- Local run and test commands for validation; update only if image sourcing policy needs documenting.

## Tasks & Acceptance

**Execution:**
- [x] `app/templates/home.html`, `app/templates/base.html` -- Reshape the homepage into a polished, image-led storefront while retaining existing destinations, forms, CSRF behavior, labels, and listing data.
- [x] `app/static/css/style.css` -- Implement the cohesive premium visual system and mobile/tablet/desktop layouts; scope changes to the homepage except for any intentional, necessary shared-shell refinement.
- [x] `app/i18n.py` -- Add English and Greek translations for new homepage text and accessible labels.
- [x] `app/static/images/demos/`, `app/static/images/demos/ATTRIBUTION.md` -- Add or replace demo imagery only after source/license approval; retain creator, source, and license credit.
- [x] `tests/test_app.py` -- Verify refreshed homepage markup, bilingual labels, accessible interactions, image credits, search results/empty state, and existing browse-only behavior.

**Acceptance Criteria:**
- Given an English- or Greek-language visitor, when they open the homepage, then the refreshed hero, search, listings, and actions are clear and all new text is translated.
- Given a visitor filters listings or finds no matches, when results render, then existing search behavior is unchanged and the result/empty state uses the refreshed responsive layout.
- Given a demo guitar card, when it is displayed or opened, then it retains its demo-only disclosure, valid image credit, and existing browse-only detail flow.
- Given any viewport from mobile to desktop, when the homepage is viewed, then content reflows without horizontal overflow and controls remain keyboard-accessible with visible focus.
- Given no confirmed rights for Thomann product images, when the page is built, then no Thomann image is copied, rehosted, or hotlinked.

## Implementation Notes

Added a licensed, locally served Commons close-up as the editorial hero image and recorded creator, source, and CC BY 2.0 terms in the attribution table. Restyled the homepage shell, image-led hero, search panel, and responsive listing cards; added translated accessible labels, lazy-loaded listing photos, and linked live-listing images to their existing detail routes. Kept the existing demo product images and browse-only behavior; did not use Thomann assets because usage permission was not confirmed. Verified 30 tests pass, application/test compilation succeeds, and browser checks show the hero photo loads, mobile width has no horizontal overflow, and keyboard focus is visible.

## Plan Change Log

## Review Triage Log

Quick review -- 0 high, 0 medium, 0 low, 0 false, 0 maybe-false; no actionable findings returned.

## Design Notes

Use a restrained, premium editorial hierarchy: strong image composition, confident typography, generous spacing, and consistent warm accent details. Treat the guitar photography as the focal point, but preserve real prices/condition and distinguish demo content from live listings. Keep the search easy to reach rather than hiding it behind a decorative hero. Avoid introducing an external asset or font dependency without a demonstrated need.

## Verification

**Commands:**
- `py -m pytest -q` -- expected: all existing and added application tests pass.
- `py -m compileall app tests` -- expected: application and test modules compile.

**Manual checks (if no CLI):**
- View the homepage in both languages at desktop and mobile widths; verify hero and photo crop, search/form usability, live/demo cards, focus visibility, and image-credit destination.
