-- =====================================================================
-- Rentora — full database schema
--
-- This file did NOT exist in the repository. The backend has no
-- models.py / Alembic migrations / db_init.py — every router talks to
-- the database with raw SQL (SQLAlchemy `text()`), assuming the tables
-- already exist on a shared Supabase Postgres instance. This script
-- was reverse-engineered by reading every `INSERT`/`SELECT`/`UPDATE`
-- statement across backend/app/routers/*.py and backend/app/utils/*.py
-- (plus the historical sql/*.sql and db_init.py that used to exist in
-- git history, whose table names had already drifted from current
-- code) to reconstruct a schema the current backend actually expects.
--
-- IDs are UUIDs (gen_random_uuid()) because every ID field is typed
-- `string` end-to-end (Pydantic `str`, Angular `string`, `str(user["id"])`
-- casts) — never treated as an integer.
--
-- Run once against an empty database:
--   psql -U postgres -d rentora_new_db -f sql/schema.sql
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

-- ---------------------------------------------------------------------
-- categories
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) UNIQUE NOT NULL,
    description TEXT
);

-- ---------------------------------------------------------------------
-- profiles  (application users — customer / seller / admin /
-- warehouse_staff / cargo_manager). Auth is custom (FastAPI + JWT),
-- not Supabase Auth, so this is a plain table, not auth.users.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name     VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(50) NOT NULL DEFAULT 'customer'
                  CHECK (role IN ('customer', 'seller', 'admin', 'warehouse_staff', 'cargo_manager')),
    phone_number  VARCHAR(50),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- products
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.products (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                    VARCHAR(255) NOT NULL,
    brand                    VARCHAR(255),
    description              TEXT,
    category_id              UUID REFERENCES public.categories(id) ON DELETE SET NULL,
    rental_price_per_day     NUMERIC(10, 2) NOT NULL,
    security_deposit         NUMERIC(10, 2) NOT NULL,
    condition                VARCHAR(50) DEFAULT 'good',
    status                   VARCHAR(50) NOT NULL DEFAULT 'available'
                             CHECK (status IN ('available', 'booked', 'maintenance', 'unavailable')),
    average_rating           NUMERIC(3, 2) DEFAULT 0.00,
    review_count             INTEGER DEFAULT 0,
    images                   TEXT[] DEFAULT '{}',
    technical_specifications JSONB DEFAULT '{}'::jsonb,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON public.products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_status      ON public.products (status);

-- ---------------------------------------------------------------------
-- product_availability  (maintenance / manual unavailability windows,
-- separate from bookings)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.product_availability (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    status     VARCHAR(50) NOT NULL CHECK (status IN ('maintenance', 'unavailable'))
);

CREATE INDEX IF NOT EXISTS idx_product_availability_product_id ON public.product_availability (product_id);

-- ---------------------------------------------------------------------
-- bookings
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.bookings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id        UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    customer_id       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    total_rental_fee  NUMERIC(10, 2) NOT NULL,
    tax               NUMERIC(10, 2) NOT NULL,
    security_deposit  NUMERIC(10, 2) NOT NULL,
    total_amount      NUMERIC(10, 2) NOT NULL,
    status            VARCHAR(50) NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'confirmed', 'active', 'late', 'completed', 'cancelled')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bookings_product_id  ON public.bookings (product_id);
CREATE INDEX IF NOT EXISTS idx_bookings_customer_id ON public.bookings (customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status      ON public.bookings (status);

-- ---------------------------------------------------------------------
-- payments  (mock payment ledger: rental fee, escrowed deposit,
-- refunds, late fees, damage penalties)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.payments (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id             UUID NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
    amount                 NUMERIC(10, 2) NOT NULL,
    type                   VARCHAR(50) NOT NULL
                           CHECK (type IN ('rental_fee', 'security_deposit', 'refund', 'late_fee', 'damage_penalty')),
    status                 VARCHAR(50) NOT NULL
                           CHECK (status IN ('completed', 'escrow', 'refunded')),
    transaction_reference  VARCHAR(255),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON public.payments (booking_id);

-- ---------------------------------------------------------------------
-- reviews
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reviews (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    booking_id  UUID UNIQUE NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reviews_product_id  ON public.reviews (product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_customer_id ON public.reviews (customer_id);

CREATE OR REPLACE FUNCTION public.fn_reviews_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reviews_set_updated_at ON public.reviews;
CREATE TRIGGER trg_reviews_set_updated_at
BEFORE UPDATE ON public.reviews
FOR EACH ROW EXECUTE FUNCTION public.fn_reviews_set_updated_at();

-- ---------------------------------------------------------------------
-- waiting_lists
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.waiting_lists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status      VARCHAR(50) NOT NULL DEFAULT 'waiting'
                CHECK (status IN ('waiting', 'notified')),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waiting_lists_product_id ON public.waiting_lists (product_id);
CREATE INDEX IF NOT EXISTS idx_waiting_lists_status     ON public.waiting_lists (status);

-- ---------------------------------------------------------------------
-- notifications
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.notifications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title      VARCHAR(255) NOT NULL,
    message    TEXT NOT NULL,
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read  ON public.notifications (is_read);

-- ---------------------------------------------------------------------
-- import_requests  ("Import on Demand")
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.import_requests (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id                     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_name                    VARCHAR(255) NOT NULL,
    product_description             TEXT,
    preferred_rental_duration_days  INTEGER NOT NULL,
    estimated_budget                NUMERIC(10, 2) NOT NULL,
    additional_requirements         TEXT,
    status                          VARCHAR(50) NOT NULL DEFAULT 'pending'
                                    CHECK (status IN ('pending', 'approved', 'rejected', 'more_info_needed', 'completed')),
    admin_notes                     TEXT,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_import_requests_customer_id ON public.import_requests (customer_id);
CREATE INDEX IF NOT EXISTS idx_import_requests_status      ON public.import_requests (status);

-- ---------------------------------------------------------------------
-- cargo_shipments
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.cargo_shipments (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_request_id  UUID NOT NULL REFERENCES public.import_requests(id) ON DELETE CASCADE,
    status              VARCHAR(50) NOT NULL DEFAULT 'purchased'
                        CHECK (status IN ('purchased', 'in_transit', 'customs_cleared', 'arrived')),
    tracking_notes      TEXT,
    cargo_manager_id    UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cargo_shipments_import_request_id ON public.cargo_shipments (import_request_id);

CREATE OR REPLACE FUNCTION public.fn_cargo_shipments_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cargo_shipments_set_updated_at ON public.cargo_shipments;
CREATE TRIGGER trg_cargo_shipments_set_updated_at
BEFORE UPDATE ON public.cargo_shipments
FOR EACH ROW EXECUTE FUNCTION public.fn_cargo_shipments_set_updated_at();

-- ---------------------------------------------------------------------
-- returns_and_inspections
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.returns_and_inspections (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id             UUID UNIQUE NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
    warehouse_staff_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE SET NULL,
    return_date            DATE NOT NULL,
    condition_on_return    VARCHAR(50) NOT NULL
                           CHECK (condition_on_return IN ('new', 'excellent', 'good', 'fair', 'damaged')),
    needs_maintenance      BOOLEAN NOT NULL DEFAULT FALSE,
    damage_description     TEXT,
    damage_penalty_amount  NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    late_fee_amount        NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_returns_and_inspections_booking_id ON public.returns_and_inspections (booking_id);

-- ---------------------------------------------------------------------
-- demand_analytics  (search terms logged for the admin demand dashboard)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.demand_analytics (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_term   VARCHAR(255) NOT NULL,
    was_available BOOLEAN NOT NULL,
    searched_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_demand_analytics_search_term ON public.demand_analytics (search_term);

-- ---------------------------------------------------------------------
-- wishlists
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.wishlists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_id  UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (customer_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_wishlists_customer_id ON public.wishlists (customer_id);

-- =====================================================================
-- Optional seed data — comment out if you don't want it.
-- Registration (/api/auth/register) only allows role customer/seller,
-- so an admin/staff account has to be seeded manually to test those
-- endpoints. Passwords are stored in PLAIN TEXT because
-- backend/app/routers/auth.py compares them as plain text on login
-- (see the "no hashing" comment in that file) — this matches current
-- app behavior, not a schema requirement.
-- =====================================================================
INSERT INTO public.categories (name, description) VALUES
    ('Drones', 'Camera and cinema drones'),
    ('Cameras', 'DSLR, mirrorless and cinema cameras'),
    ('Audio Gear', 'Microphones, recorders and mixers')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.profiles (full_name, email, password_hash, role) VALUES
    ('Admin User',      'admin@rentora.com',      'admin123',      'admin'),
    ('Warehouse Staff',  'warehouse@rentora.com',   'warehouse123',  'warehouse_staff'),
    ('Cargo Manager',    'cargo@rentora.com',       'cargo123',      'cargo_manager'),
    ('Test Customer',    'customer@rentora.com',    'customer123',   'customer')
ON CONFLICT (email) DO NOTHING;
