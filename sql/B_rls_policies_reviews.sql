-- =====================================================================
-- Module 1, Part 4: Ratings & Reviews
-- Migration B: Row Level Security for `reviews`
--
-- WHY THIS LOOKS DIFFERENT FROM A "TYPICAL" SUPABASE RLS SETUP:
-- Most Supabase RLS tutorials assume you're using Supabase's own Auth
-- system, where auth.uid() tells Postgres who's making the request.
-- Your `users` table (id, name, email — no role, no auth.users link)
-- shows your team is building a CUSTOM login system in FastAPI
-- (Module 1 Part 1), not Supabase Auth. That means auth.uid() is not
-- available here — Postgres has no idea who the "current user" is
-- when FastAPI queries it, because FastAPI itself is the one who knows
-- (it decoded the JWT and identified the user in Python).
--
-- Given your architecture is React -> FastAPI -> Postgres (FastAPI is
-- the ONLY thing that talks to the database), the correct security
-- model is:
--   - FastAPI connects to Postgres with a single trusted/privileged
--     connection (not a different one per user), and enforces ALL the
--     "is this your booking / is it completed / no double-review"
--     rules itself in Python (already built in crud/reviews.py).
--   - RLS's job here is simpler: make sure NO ONE can write to
--     `reviews` directly except through that trusted connection —
--     e.g. if someone got the Supabase anon/public API key and tried
--     to insert a fake review straight into the database, bypassing
--     your FastAPI's rules entirely, RLS blocks that.
--
-- If your team adds real Supabase Auth later (so React logs users in
-- via Supabase directly), you can swap the INSERT/UPDATE/DELETE
-- policies below for ownership-based ones using auth.uid() — same
-- pattern as before, just add a column linking users.id to auth.uid().
-- =====================================================================

alter table public.reviews enable row level security;

-- Anyone can READ reviews — public browsing, no login needed. This is
-- what makes "the system displays the average rating for every
-- product" work for visitors who aren't even logged in.
drop policy if exists "Public can read reviews" on public.reviews;
create policy "Public can read reviews"
on public.reviews
for select
to anon, authenticated
using (true);

-- Nobody using the public anon/authenticated Supabase keys can insert,
-- update, or delete reviews directly. Only your FastAPI backend can —
-- and it does so using a separate, privileged database connection
-- (the SUPABASE_DB_URL in your backend's .env) that bypasses RLS
-- entirely, by design. This is what actually enforces "you can only
-- review your own completed booking" — that logic lives in
-- backend/app/crud/reviews.py, not in a Postgres policy, because
-- Postgres has no way to know who the logged-in user is without your
-- own auth system telling it.
--
-- (We simply don't create INSERT/UPDATE/DELETE policies for
-- anon/authenticated — with RLS enabled and no matching policy, those
-- operations are denied by default. This comment documents that
-- on purpose, not by accident.)
