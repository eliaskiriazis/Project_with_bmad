---
title: 'Premium Marketplace Visual Refresh'
type: 'feature'
ticket: ''
created: '2026-10-06'
status: 'built'
baseline_revision: 'f75312ecdf6cdf63d7341bf2891dfac3a17e240a'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The marketplace should feel like a cohesive premium storefront, including its homepage, demo guitar imagery, and account entry points. Login and registration currently inherit general styles rather than a deliberate branded experience, and the demo imagery should read more like clean product photography.

**Approach:** Refine the existing editorial homepage into a consistent premium visual system, present demo guitars in a clean white product-image stage, and give login and registration a matching, polished layout. Use only user-provided images with permission or appropriately licensed assets with accurate attribution.

**Decision:** Use the user's forthcoming authorized white-background product photos for demo listings; do not source Thomann photos.

## Boundaries & Constraints

**Always:** Preserve English and Greek content, homepage search and query parameters, real and demo listing destinations, image credits, demo-only disclosures, browse-only behavior, form fields and validation, CSRF protection, redirect safety, keyboard focus, responsive layouts, and reduced-motion support. Keep the same visual language across the named surfaces.

**Never:** Copy, rehost, or hotlink Thomann product photography without explicit permission or a license permitting this use. Do not change authentication, listing inventory, checkout, or unrelated page behavior. Do not imply demo photos verify a guitar's identity, condition, ownership, or availability.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Visitor browses in either language | Homepage or authentication page | Premium responsive layout with translated copy and existing actions | No missing or untranslated new labels |
| Demo photo is shown | Approved image source and attribution available | Image appears in a clean white stage; demo status and public credit remain clear | Do not use an image with unverified rights or missing credit |
| Authentication form is submitted | Valid or invalid existing form data | Existing registration/login results, validation and redirects are unchanged | Existing CSRF and form error handling remain visible |
| Narrow screen or keyboard use | Mobile viewport or keyboard-only input | No horizontal overflow; controls and focus remain visible and operable | Reflow without clipping or hiding actions |

</frozen-after-approval>

## Code Map

- `app/templates/home.html` -- Homepage hero, search, demo/live cards, photo sources, credits; retain existing routes and data.
- `app/templates/base.html` -- Shared navigation, language controls, flash messages, stylesheet and scripts; preserve auth and language actions.
- `app/templates/login.html`, `app/templates/register.html` -- Authentication form markup; preserve fields, CSRF tokens, errors and destinations while adding the premium presentation.
- `app/static/css/style.css` -- Shared palette and responsive homepage styles; add scoped auth and product-image presentation without regressing other pages.
- `app/i18n.py` -- English/Greek strings for any new visible or accessible copy.
- `app/static/images/demos/`, `app/static/images/demos/ATTRIBUTION.md` -- Existing local demo and hero images and license records; update only for approved, rights-cleared replacements.
- `app/auth.py`, `app/listings.py`, `app/__init__.py` -- Existing auth/home/detail routes and search behavior to leave unchanged.
- `tests/test_app.py` -- Existing homepage/search/demo and auth/CSRF coverage; extend for premium page structure, translations and responsive/accessibility styling.

## Tasks & Acceptance

**Execution:**
- [ ] `app/templates/home.html`, `app/static/css/style.css` -- Refine the homepage and demo image stage into a cohesive premium storefront without changing search, card destinations or disclosures.
- [ ] `app/templates/login.html`, `app/templates/register.html`, `app/static/css/style.css` -- Add matching premium auth layouts, keeping form structure and error states usable at mobile and desktop widths.
- [ ] `app/i18n.py` -- Translate any new visible/accessibility copy in English and Greek.
- [ ] `app/static/images/demos/`, `app/static/images/demos/ATTRIBUTION.md` -- Use supplied authorized photos or retain existing licensed assets; document each changed asset accurately.
- [ ] `tests/test_app.py` -- Cover both language variants, responsive/auth styling markers, image credits, search and existing auth safeguards.

**Acceptance Criteria:**
- Given an English- or Greek-speaking visitor, when they open the homepage or either auth page, then the named surfaces share a polished premium identity and all new copy is translated.
- Given a visitor searches or opens a demo/live card, when results or details appear, then all existing filters, destinations, credits, demo disclosures and browse-only safeguards remain intact.
- Given a visitor submits login or registration, when input is valid or invalid, then existing validation, CSRF protection, error feedback and safe redirects behave as before.
- Given any named page at a narrow or wide viewport, when navigated by pointer or keyboard, then content reflows without horizontal overflow and controls retain visible focus.
- Given no Thomann permission or suitable license, when demo imagery is updated, then no Thomann asset is used.

## Implementation Notes

## Plan Change Log

## Review Triage Log

- **false** — `app/static/css/style.css`: the reported later `.home-page .search-form` override does not declare `grid-template-columns`; the existing `@media (max-width: 980px)` and `@media (max-width: 640px)` rules therefore remain effective for the homepage.

## Design Notes

Keep the homepage editorial rather than turning it into a generic template. Use generous spacing, restrained warm accents, clear hierarchy, and a consistent image frame. On auth pages, pair a concise brand/story panel with an uncluttered form; prioritize form completion and maintain contrast, visible focus, and legible validation states.

## Verification

**Commands:**
- `python -m pytest -q tests/test_app.py` -- expected: all homepage, image-credit, browse-only, and authentication integration tests pass.
- `python -m compileall app tests` -- expected: all application and test modules compile.

**Manual checks (if no CLI):**
- Check the homepage, login, and registration in English and Greek at desktop and mobile widths; verify image crops, image credits, search, form errors, keyboard focus, reduced motion, and absence of horizontal overflow.
