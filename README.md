# Guitar Marketplace MVP

This project is a Flask-based bilingual marketplace for used electric guitars in the EU.

## Local setup

1. Create and activate a virtual environment, then install the dependencies:
   `python -m venv .venv`
   `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`; set a random `SECRET_KEY`, `BASE_URL`, and `PLATFORM_COMMISSION_PERCENT` (1–100). Checkout stays disabled until a commission is configured.
3. In Stripe test mode, configure an `sk_test_` secret key and test publishable key. Connect seller onboarding requires Stripe Connect to be enabled for the platform. Set up a test webhook for `/webhooks/stripe`, subscribe to connected-account `account.updated`, `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, and `checkout.session.expired` events, and copy its test signing secret into `STRIPE_WEBHOOK_SECRET`.
4. Configure SMTP host, port 587 with STARTTLS, sender, and optional credentials for email updates. Without SMTP configuration, email delivery is logged as unavailable; in-app notices remain available to registered users.
5. Start the app with `python -m flask --app app run`. The Flask app creates the SQLite schema on first startup and adds current marketplace columns to an existing SQLite database without removing data. `migrations/001_initial.sql` is provided as a reference schema. Local listing photos are stored under the configured `UPLOAD_FOLDER` (default `uploads/`). For local debugging only, add Flask's `--debug` option.
6. Register a user, then grant moderation access from the command line with `python -m flask --app app promote-admin user@example.com`.

Run automated checks with `python -m pytest -q` and `python -m compileall app`.

## Payment and launch safety

- Only Stripe **test-mode** secret keys (`sk_test_`) are accepted; live keys and live webhook events are rejected.
- Checkout uses Stripe Connect direct charges. The configured application fee is calculated on the guitar price only; Stripe processing fees are charged to the connected seller, and the seller receives payouts on Stripe's normal schedule.
- Net seller proceeds are determined by Stripe because processing fees vary; the app does not display or store an estimate that omits those fees.
- Guest buyers receive email order updates only. Registered order participants can view order details and message each other.
- Do not enable live charges until EU tax responsibility, marketplace compliance, and live-payment operational readiness have been reviewed. Never commit `.env`, payment credentials, database files, or uploaded photos.
