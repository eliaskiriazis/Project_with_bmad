---
title: 'Guitar Marketplace MVP'
type: 'feature'
ticket: ''
created: '2026-10-05'
status: 'built'
baseline_revision: 'NO_VCS'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Buyers and sellers need a focused place to list, discover, and transact used electric guitars across the EU.

**Approach:** Build a bilingual Greek/English Flask marketplace using server-rendered HTML/CSS/JavaScript, SQLite, and Stripe Connect test mode for EUR checkout and seller payouts. Support guest checkout, listing search, order updates, messaging for registered users, and basic report moderation.

**Decision:** Seller and registered-buyer accounts use email/password authentication; guest checkout remains available.

**Decision:** Store listing photos in a configurable local upload directory for the MVP; validate file types and sizes, generate safe filenames, and exclude uploads from version control.

**Decision:** Keep checkout in Stripe test mode until EU tax responsibility and applicable rules have been confirmed; the MVP must not imply that its test checkout is live-trading compliant.

**Decision:** Stripe processing fees are deducted from seller proceeds; buyers see the item price and any fixed shipping fee, not a separate provider-fee surcharge.

**Decision:** Pay sellers out on their Stripe Connect account's normal payout schedule after successful payment; do not hold funds until order completion.

**Decision:** Require a valid commission percentage in configuration before enabling checkout; do not silently assume a default rate.

**Decision:** Calculate platform commission on the guitar price only; do not charge commission on shipping.

## Boundaries & Constraints

**Always:** Keep payment credentials outside source control; validate prices, ownership, and order state on the server; verify payment completion via trusted provider events; prevent buyers from purchasing their own listings; make errors visible and do not mark an order paid based only on a browser redirect. Test mode only until live-payment readiness is explicitly addressed.

**Never:** Enable live charges, implement custom card handling, add auctions, reviews, full refunds/disputes, courier-rate integrations, or multi-currency in this MVP.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid checkout | Available listing, buyer email, fulfillment choice | EUR checkout includes item and fixed shipping; verified payment creates paid order | Show retry error if checkout creation fails |
| Competing checkout | Listing reserved by another active session | Reject second checkout; release reservation on expiry/failure or mark sold on verified payment | Do not trust browser redirects; alert on provider/order conflicts |
| Listing report | Signed-in user submits listing and reason | Admin queue receives report; admin can hide listing or suspend seller | Reject invalid or unauthorized actions visibly |
| Guest order access | Guest provides checkout email | Email order updates; no in-app message access | Never expose order by guessable ID alone |

</frozen-after-approval>

## Code Map

- No marketplace application source, test suite, or spec artifact was present in the project workspace; this is a greenfield implementation.
- `_bmad_output/` -- BMad planning-artifact location; currently contains no prior project specification.

## Tasks & Acceptance

**Execution:**
- [x] `requirements.txt`, `config.py`, `app/__init__.py`, `app/extensions.py` -- create Flask app factory, SQLite configuration, and test/development settings; keep secrets in environment configuration.
- [x] `app/models.py`, `app/auth.py`, `app/listings.py`, `app/orders.py`, `app/messaging.py`, `app/notifications.py`, `app/admin.py` -- implement accounts, listings/search and validated local photos, orders, messaging/in-app notices, reports and admin actions with authorization and transaction safety.
- [x] `app/payments.py`, `app/webhooks.py` -- implement Connect onboarding, test-mode EUR checkout, verified/idempotent events, fixed shipping, configurable item-price commission, seller-paid provider fees and scheduled payouts; reject checkout if onboarding or `PLATFORM_COMMISSION_PERCENT` is missing.
- [x] `app/templates/`, `app/static/css/`, `app/static/js/`, `app/i18n.py` -- create responsive Greek/English browse, listing, checkout, order, inbox and moderation pages; retain language choice.
- [x] `migrations/`, `tests/` -- manage schema changes and test validation/search, authorization, payment verification/idempotency, reservation expiry, order transitions and moderation.
- [x] `README.md`, `.env.example`, `.gitignore` -- document local setup, SMTP, Connect test onboarding/webhooks, migrations and secret handling; exclude credentials and uploads.

**Acceptance Criteria:**
- Given a visitor, when they browse or filter by keyword, brand, price, condition or fulfillment, then available listings appear in Greek or English.
- Given a seller publishes a guitar, when required details are submitted, then title, description, brand/model, EUR price, condition, photos and fulfillment options are required; shipping includes a fixed fee.
- Given an available listing and eligible buyer, when checkout starts, then server-calculated EUR totals enter Stripe test mode and only a verified event marks the order paid.
- Given Connect onboarding or commission configuration is incomplete, when checkout is attempted, then it is blocked; otherwise commission applies only to guitar price and seller proceeds bear provider fees.
- Given two buyers start checkout, when one reserves a listing, then the other cannot pay until reservation expiry or sale completion.
- Given an order event or message, when it is delivered, then email and authorized in-app inbox access follow guest/member rules.
- Given registered order participants, when they message or update fulfillment, then access is restricted and statuses follow paid → shipped/ready for pickup → completed.
- Given a listing report, when an admin reviews it, then they can hide the listing or suspend its seller; unauthorized actions fail.
- Given invalid input, unavailable stock or duplicate/failed payment events, when processed, then no duplicate or false sale is recorded and a visible error or safe recovery is provided.

## Implementation Notes

Implemented all planned application layers and added CSRF protection, signed test-mode Stripe webhook verification, Connect onboarding, atomic listing reservation, checkout fee/address validation, bilingual templates, SMTP email notices, moderation and role-restricted order transitions. Review corrections include test-mode checkout disclosure, electric-guitar confirmation, stale-reservation protection, failed-payment notifications, input limits, and an additive upgrade for existing SQLite files. Final local verification: `py -m pytest -q` (27 passed), `py -m compileall app tests`, `py -m flask --app app routes`, an HTTP 200 home-page smoke test, and VS Code Problems (no errors). Real Stripe and SMTP credentials were not configured, so provider operations and delivery were not end-to-end tested. The project has no Git repository; baseline is `NO_VCS`.

## Plan Change Log

## Review Triage Log
- blind-hunter — `config.py` enabled Flask debug mode by default — **medium / patch**. Disabled the debugger by default and documented explicit local-only `--debug`.
- blind-hunter — expired checkout could clear a newer listing reservation — **medium / patch**. Release the listing only when its reservation timestamp still matches the expiring order; regression test covers a newer reservation.
- blind-hunter — late verified payment after reservation expiry returns 409 — **false**. The webhook logs a critical manual-reconciliation alert and rejects the stale order rather than marking a potentially conflicting sale paid; this is the documented safe conflict path and refunds are out of scope.
- blind-hunter — asynchronous payment failures were ignored — **medium / patch**. Handle `checkout.session.async_payment_failed`, release only that order's reservation, notify/email the buyer, and document/verify the event.
- blind-hunter — guest buyers cannot mark orders completed — **false**. The approved guest flow is email updates only, with no in-app order access; state-transition acceptance is explicitly for registered participants.
- blind-hunter — multipart limit was below the combined permitted photo sizes — **medium / patch**. Raised request limit to accommodate eight 5 MiB photos plus multipart overhead and added a configuration assertion.
- blind-hunter — search loads every matching listing — **low / rejected**. Unbounded results are a future scale concern, not a defect likely to meet everyday MVP use; pagination would add a user-facing workflow not required here.
- blind-hunter — reports accepted unbounded text and repeated pending reports — **medium / patch**. Added a server-side 2,000-character bound and one queued report per user/listing; tests verify duplicate suppression.
- blind-hunter — monetary input lacked a Checkout-supported ceiling — **medium / patch**. Bounded amounts and combined Checkout total to the provider's supported limit; tests cover item and item-plus-shipping overflow.
- blind-hunter — simultaneous duplicate registrations could race at the unique constraint — **low / rejected**. The failure requires concurrent registration of the same address and is not an everyday MVP defect; normal duplicate submissions are handled.
- edge-case-hunter — stale report could reference a missing listing during moderation — **false**. Listing deletion is not exposed by this application, and reports are created only against an existing listing; no reachable route produces the described stale reference.
- edge-case-hunter — seller lookup could fail for a stale report/listing reference — **false**. The same unreachable stale-reference precondition applies; no listing/user deletion path exists.
- edge-case-hunter — a message recipient could be missing — **false**. Only the two existing order participants can reach this route, and the application exposes no account-deletion flow that could remove the recipient.
- verification-gap — seller suspension lacked an integration test — **low / patch**. Added a route-level test asserting suspension, listing deactivation/hiding, report resolution, and rejected seller login.
- intent-alignment — checkout UI did not disclose test-only payments — **medium / patch**. Added an English/Greek notice stating that no real payments are processed and live payments are disabled.
- intent-alignment — listing form did not distinguish used electric guitars — **medium / patch**. Added a required seller confirmation and server-side validation for the approved product category.
- intent-alignment — stored seller proceeds omitted variable Stripe processing fees — **low / patch**. Removed the misleading proceeds estimate; Stripe calculates actual fees on the connected seller account, and the README clarifies that the app does not display a net estimate.
- intent-alignment — tests do not exercise real provider payouts — **low / rejected**. Stripe test credentials/provider access are not configured; payout timing is handled by Connect's normal schedule, while application tests intentionally mock provider calls.

## Design Notes

Use a Flask factory and server-rendered pages. Store money as integer euro cents; calculate totals server-side, reserve inventory during active checkout, and process webhooks idempotently. Connect direct charges with an application fee let sellers bear processing fees and receive normal payouts. Never store card data. SQLite/local uploads are MVP-only; production concurrency and shared storage need review.

## Verification

**Commands:**
- `python -m pytest` -- expected: all unit and workflow tests pass, including payment webhook and authorization edge cases.
- `python -m compileall app` -- expected: application modules compile successfully.
- `python -m flask --app app run` -- expected: local application starts with development configuration and without live payment credentials.

**Manual checks (if no CLI):**
- Exercise listing creation/search in both languages, test-mode checkout and webhook completion, guest email updates, participant-only messaging, order status transitions, and admin report actions.
