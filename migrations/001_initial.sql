CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    stripe_connect_account_id VARCHAR(255),
    seller_onboarded BOOLEAN DEFAULT 0,
    country_code VARCHAR(2),
    is_suspended BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    brand VARCHAR(80) NOT NULL,
    model VARCHAR(100) NOT NULL,
    condition VARCHAR(40) NOT NULL,
    price_cents INTEGER NOT NULL,
    shipping_fee_cents INTEGER DEFAULT 0,
    fulfillment VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_hidden BOOLEAN DEFAULT 0,
    reserved_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    photo_paths TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    buyer_id INTEGER REFERENCES users(id),
    seller_id INTEGER NOT NULL REFERENCES users(id),
    guest_email VARCHAR(150),
    status VARCHAR(40) DEFAULT 'reserved',
    total_cents INTEGER NOT NULL,
    shipping_fee_cents INTEGER DEFAULT 0,
    fulfillment_method VARCHAR(20),
    commission_cents INTEGER DEFAULT 0,
    checkout_session_id VARCHAR(255),
    payment_event_id VARCHAR(255) UNIQUE,
    shipping_details TEXT,
    reserved_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    sender_id INTEGER NOT NULL REFERENCES users(id),
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    reason TEXT NOT NULL,
    status VARCHAR(40) DEFAULT 'queued',
    admin_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
