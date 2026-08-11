-- =====================================================================
-- Module 1, Part 4: Ratings & Reviews
-- Migration A: harden the EXISTING `reviews` table
--
-- Your `reviews` table already exists (someone on the team created it),
-- and `products.average_rating` / `products.review_count` already
-- exist too. This migration does NOT create the table — it only adds
-- the missing safety rules on top of what's already there:
--   1. one review per booking (unique constraint)
--   2. rating must be 1-5 (check constraint)
--   3. foreign keys to bookings/users/products, if not already present
--   4. auto-fill product_id from booking_id if the app doesn't supply it
--   5. auto-recalculate products.average_rating / review_count
--   6. auto-update reviews.updated_at on edit
--
-- Safe to re-run: every step below checks "does this already exist?"
-- before adding it, so running this twice does nothing the second time.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. One review per booking
-- ---------------------------------------------------------------------
do $$
begin
  alter table public.reviews
    add constraint uq_reviews_one_per_booking unique (booking_id);
exception
  when duplicate_object or duplicate_table then
    raise notice 'uq_reviews_one_per_booking already exists, skipping.';
end $$;

-- ---------------------------------------------------------------------
-- 2. Rating must be between 1 and 5
-- ---------------------------------------------------------------------
do $$
begin
  alter table public.reviews
    add constraint ck_reviews_rating_range check (rating between 1 and 5);
exception
  when duplicate_object then
    raise notice 'ck_reviews_rating_range already exists, skipping.';
end $$;

-- ---------------------------------------------------------------------
-- 3. Foreign keys (in case the table was created without them)
-- ---------------------------------------------------------------------
do $$
begin
  alter table public.reviews
    add constraint fk_reviews_booking foreign key (booking_id)
      references public.bookings(id) on delete cascade;
exception
  when duplicate_object then
    raise notice 'fk_reviews_booking already exists, skipping.';
end $$;

do $$
begin
  alter table public.reviews
    add constraint fk_reviews_user foreign key (user_id)
      references public.users(id) on delete cascade;
exception
  when duplicate_object then
    raise notice 'fk_reviews_user already exists, skipping.';
end $$;

do $$
begin
  alter table public.reviews
    add constraint fk_reviews_product foreign key (product_id)
      references public.products(id) on delete cascade;
exception
  when duplicate_object then
    raise notice 'fk_reviews_product already exists, skipping.';
end $$;

-- Also required: booking_id and user_id should never be empty.
alter table public.reviews alter column booking_id set not null;
alter table public.reviews alter column user_id set not null;
alter table public.reviews alter column rating set not null;

create index if not exists idx_reviews_product_id on public.reviews (product_id);
create index if not exists idx_reviews_user_id    on public.reviews (user_id);

-- ---------------------------------------------------------------------
-- 4. Auto-resolve product_id from booking_id if the caller left it out
--    (bookings -> inventory_items -> products)
--    SECURITY DEFINER: runs with the function owner's privileges, so it
--    can read inventory_items even if the calling role can't directly.
-- ---------------------------------------------------------------------
create or replace function public.fn_reviews_set_product_id()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.product_id is null then
    select ii.product_id
      into new.product_id
      from public.bookings b
      join public.inventory_items ii on ii.id = b.inventory_item_id
     where b.id = new.booking_id;

    if new.product_id is null then
      raise exception
        'Could not resolve product_id for booking % — check bookings.inventory_item_id and inventory_items.product_id',
        new.booking_id;
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_reviews_set_product_id on public.reviews;
create trigger trg_reviews_set_product_id
before insert on public.reviews
for each row execute function public.fn_reviews_set_product_id();

-- ---------------------------------------------------------------------
-- 5. Keep products.average_rating / review_count in sync automatically
-- ---------------------------------------------------------------------
create or replace function public.fn_recompute_product_rating()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  target_product_id bigint := coalesce(new.product_id, old.product_id);
begin
  update public.products p
     set average_rating = coalesce(sub.avg_rating, 0),
         review_count   = coalesce(sub.review_total, 0)
    from (
      select round(avg(rating)::numeric, 2) as avg_rating,
             count(*)                        as review_total
        from public.reviews
       where product_id = target_product_id
    ) sub
   where p.id = target_product_id;

  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_reviews_recompute_after_insert on public.reviews;
create trigger trg_reviews_recompute_after_insert
after insert on public.reviews
for each row execute function public.fn_recompute_product_rating();

drop trigger if exists trg_reviews_recompute_after_update on public.reviews;
create trigger trg_reviews_recompute_after_update
after update of rating on public.reviews
for each row execute function public.fn_recompute_product_rating();

drop trigger if exists trg_reviews_recompute_after_delete on public.reviews;
create trigger trg_reviews_recompute_after_delete
after delete on public.reviews
for each row execute function public.fn_recompute_product_rating();

-- ---------------------------------------------------------------------
-- 6. Auto-update `updated_at` whenever a review is edited
--    (your table already has this column — let's actually use it)
-- ---------------------------------------------------------------------
create or replace function public.fn_reviews_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_reviews_set_updated_at on public.reviews;
create trigger trg_reviews_set_updated_at
before update on public.reviews
for each row execute function public.fn_reviews_set_updated_at();
