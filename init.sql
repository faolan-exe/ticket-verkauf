CREATE TABLE IF NOT EXISTS settings (
    key   VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO settings (key, value) VALUES
    ('ticket_price',        '60'),
    ('total_tickets',       '57'),
    ('registration_open',   'false'),
    ('fcfs_block_enabled',  'true'),
    ('paypal_name',         ''),
    ('paypal_email',        ''),
    ('bank_owner',          ''),
    ('bank_iban',           ''),
    ('bank_bic',            ''),
    ('bank_reference',      'Abbiball Ticket')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS registrations (
    id               SERIAL PRIMARY KEY,
    registrant_name  VARCHAR(255) NOT NULL,
    email            VARCHAR(255) NOT NULL,
    desired_table      SMALLINT,
    total_tickets      SMALLINT NOT NULL,
    payment_confirmed  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    ip_address         INET
);

CREATE INDEX IF NOT EXISTS idx_registrations_created_at ON registrations (created_at);

CREATE TABLE IF NOT EXISTS persons (
    id               SERIAL PRIMARY KEY,
    registration_id  INTEGER NOT NULL REFERENCES registrations (id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    is_over_18       BOOLEAN NOT NULL,
    food_preference  VARCHAR(20) NOT NULL CHECK (food_preference IN ('meat', 'vegetarian')),
    is_registrant    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_persons_reg ON persons (registration_id);
