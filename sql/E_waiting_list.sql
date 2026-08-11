-- ============================================================
-- Module 2 / Part 4 — Waiting List Management
-- SQL Migration for pgAdmin 4 / local PostgreSQL
-- Run this once against your "Rentora" database.
-- (The waiting_list and notifications tables are already created
--  by db_init.py on startup; this file is for manual review/reset.)
-- ============================================================

-- 1. waiting_list table (safe: IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS public.waiting_list (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES public.users(id)    ON DELETE CASCADE,
    joined_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP WITH TIME ZONE,
    status      VARCHAR(50) DEFAULT 'pending'
                CHECK (status IN ('pending', 'notified', 'cancelled')),
    UNIQUE (product_id, user_id, status)
);

-- 2. notifications table (safe: IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS public.notifications (
    id       SERIAL PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    message  TEXT NOT NULL,
    sent_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_read  BOOLEAN DEFAULT FALSE
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_waiting_list_product_id ON public.waiting_list (product_id);
CREATE INDEX IF NOT EXISTS idx_waiting_list_user_id    ON public.waiting_list (user_id);
CREATE INDEX IF NOT EXISTS idx_waiting_list_status     ON public.waiting_list (status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id   ON public.notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read   ON public.notifications (is_read);

-- ============================================================
-- Helper: mark the seeded product as "rented" so the
-- waiting list button appears (product 1 seeded by db_init.py)
-- ============================================================
-- Uncomment the line below to test the waiting list UI:
-- UPDATE public.products SET status = 'rented' WHERE id = 1;

-- ============================================================
-- Verification queries
-- ============================================================
-- SELECT * FROM public.waiting_list ORDER BY joined_at;
-- SELECT * FROM public.notifications ORDER BY sent_at DESC;
