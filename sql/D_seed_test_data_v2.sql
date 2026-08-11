-- =====================================================================
-- Module 1, Part 4: Ratings & Reviews
-- Seed script v2: reuses your EXISTING "Drones" category (id 1) instead
-- of creating a new one, since categories.name has a unique constraint
-- and "Drones" already exists in your database.
--
-- Run this ONCE in the Supabase SQL Editor. The final SELECT shows you
-- every ID you'll need for testing.
-- =====================================================================

with existing_category as (
  select id as category_id
  from public.categories
  where name = 'Drones'
  limit 1
),
new_product as (
  insert into public.products (
    name, description, category_id, rental_price_per_day,
    security_deposit, condition, status
  )
  select
    'DJI Mavic 3 Cine Premium Combo',
    'Professional cinema drone with Hasselblad camera',
    category_id,
    149.00,
    850.00,
    'mint',
    'available'
  from existing_category
  returning id as product_id
),
new_inventory_item as (
  insert into public.inventory_items (
    product_id, serial_number, condition, status, acquired_at
  )
  select product_id, 'MAVIC-001', 'mint', 'available', current_date
  from new_product
  returning id as inventory_item_id, product_id
),
new_user as (
  insert into public.users (name, email, password_hash, role)
  values (
    'Julian D.',
    'julian.d@example.com',
    -- Placeholder only — NOT a real password. Real signups (Module 1
    -- Part 1) will hash an actual password before inserting here.
    'test_seed_data_not_a_real_password_hash',
    'customer'
  )
  returning id as user_id
),
new_booking as (
  insert into public.bookings (
    user_id, inventory_item_id, start_date, end_date,
    rental_fee, tax, security_deposit, total_amount, status
  )
  select
    new_user.user_id,
    new_inventory_item.inventory_item_id,
    current_date - interval '5 days',
    current_date - interval '2 days',
    447.00,
    44.70,
    850.00,
    1341.70,
    'completed'
  from new_user, new_inventory_item
  returning id as booking_id, user_id, inventory_item_id
)
select
  ec.category_id,
  np.product_id,
  nii.inventory_item_id,
  nu.user_id,
  nb.booking_id
from existing_category ec, new_product np, new_inventory_item nii,
     new_user nu, new_booking nb;
