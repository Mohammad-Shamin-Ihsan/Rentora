-- =====================================================================
-- Module 1, Part 4: Ratings & Reviews
-- Migration C: clean up duplicates
--
-- Your `reviews` table already had its own constraints and a recompute
-- trigger before Migration A ran (created under different names than
-- Migration A guessed). Migration A didn't recognize them, so it added
-- a second, redundant copy of everything. This migration removes OUR
-- duplicates and keeps the ORIGINAL ones (they do the exact same job).
--
-- Safe to run once. Also safe to re-run — every DROP uses IF EXISTS.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Drop our duplicate constraints, keep the originals
--    (reviews_one_per_booking, reviews_rating_check,
--     reviews_booking_id_fkey, reviews_user_id_fkey,
--     reviews_product_id_fkey — all pre-existing, all kept as-is)
-- ---------------------------------------------------------------------
alter table public.reviews drop constraint if exists uq_reviews_one_per_booking;
alter table public.reviews drop constraint if exists ck_reviews_rating_range;
alter table public.reviews drop constraint if exists fk_reviews_booking;
alter table public.reviews drop constraint if exists fk_reviews_user;
alter table public.reviews drop constraint if exists fk_reviews_product;

-- ---------------------------------------------------------------------
-- 2. Drop our 3 separate recompute triggers — the original
--    trg_recompute_product_rating already covers insert+update+delete
--    in a single trigger, which is actually the tidier approach.
-- ---------------------------------------------------------------------
drop trigger if exists trg_reviews_recompute_after_insert on public.reviews;
drop trigger if exists trg_reviews_recompute_after_update on public.reviews;
drop trigger if exists trg_reviews_recompute_after_delete on public.reviews;

-- ---------------------------------------------------------------------
-- 3. The original trigger calls fn_recompute_product_rating() — the
--    SAME function name Migration A used with CREATE OR REPLACE, so
--    the function body has already been upgraded to our version
--    (with SECURITY DEFINER + search_path locked down, which fixes a
--    real permission bug — see the README). The original trigger now
--    automatically runs the improved function. Nothing more to do here
--    — this step is just a confirmation query, not a change.
-- ---------------------------------------------------------------------
-- Run this after the migration to confirm:
--   SELECT prosecdef FROM pg_proc WHERE proname = 'fn_recompute_product_rating';
--   -> should return TRUE (security definer is active)

-- ---------------------------------------------------------------------
-- 4. What we KEEP, and why:
--    - trg_recompute_product_rating   (original — now running the
--                                       upgraded, security-definer function)
--    - trg_reviews_set_product_id     (new — nothing pre-existing did this)
--    - trg_reviews_set_updated_at     (new — nothing pre-existing did this)
--    - reviews_one_per_booking, reviews_rating_check,
--      reviews_booking_id_fkey, reviews_user_id_fkey,
--      reviews_product_id_fkey, reviews_pkey    (all original, untouched)
-- ---------------------------------------------------------------------
