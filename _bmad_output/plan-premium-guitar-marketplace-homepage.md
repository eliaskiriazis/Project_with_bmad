---
title: 'Premium Guitar Marketplace Homepage'
type: 'feature'
ticket: ''
created: '2026-10-05'
status: 'built'
baseline_revision: 'NO_VCS'
route: 'oneshot'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Guitar Marketplace homepage needs a more polished, premium presentation and a small set of guitar listings that makes the browsing experience feel populated.

**Approach:** Refresh the homepage and listing cards with a dark, high-contrast editorial style, add six curated demo guitars across Ibanez, Jackson, ESP, and similar brands with appropriately licensed photos, and link each card to the existing listing detail flow. Clearly identify the listings as demos and make them browse-only.

</frozen-after-approval>

## Implementation Notes

The requested Quick Flow fits a single cohesive, low-layer UI/content change; demo listings must not be mistaken for available inventory or enter checkout.

- Kept the six curated demos as static browse content rather than database listings so they cannot be reserved, purchased, or mixed into seller inventory; their detail pages reuse the existing listing-detail template.
- Applied the existing search fields to demo content and retained persisted listing search; added English/Greek labels and a public image-credit link.
- Refreshed the homepage with a responsive dark editorial layout. Added local Wikimedia Commons thumbnails with creator/license/source provenance in `app/static/images/demos/ATTRIBUTION.md`.
- Normalized English and Greek “shipping or pickup” display text to the stored fulfillment value for demo and persisted-listing search.
- Added red/green tests for the six demo cards, bilingual labels, filtered search, shared detail presentation, attribution access, and browse-only behavior.
- Implementation touched `app/demo_listings.py`, `app/listings.py`, `app/i18n.py`, `app/templates/home.html`, `app/templates/listing_detail.html`, `app/static/css/style.css`, `app/static/images/demos/`, and `tests/test_app.py`.

## Review Triage Log

- **medium — patched:** The fulfillment filter did not match its displayed “Shipping or pickup” label. Verified the mismatch, normalized English/Greek display values for demo and persisted listings, and added regression assertions; the full suite passes.

## Verification

**Commands:**
- `python -m pytest -q` -- expected: all existing and added tests pass, including homepage language/search behavior and demo listing visibility/browse-only behavior.
- `python -m compileall app tests` -- expected: application and tests compile successfully.

**Manual checks (if no CLI):**
- Check the homepage at desktop and mobile widths, confirm all six image-backed demo listings and their labels render in English and Greek, and verify card links open detail pages without enabling checkout.
