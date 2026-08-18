-- =====================================================================
-- Rentora — product catalog seed
--
-- The browse page was rendering with no pictures or prices because the
-- database had zero rows in `products` — schema.sql only seeded
-- categories and test accounts, not actual inventory to browse. This
-- adds real catalog items (with Unsplash image URLs — the frontend's
-- getProductImage() in browse.ts specifically detects and optimizes
-- unsplash.com URLs, so that's the expected image source) across the
-- three categories seeded earlier, matching the "Drones & Aerial
-- Imaging" style browse page from the assignment mockup.
--
-- Safe to re-run: every insert is guarded by a NOT EXISTS check on
-- product title.
--
-- Run:
--   psql -U postgres -d rentora_new_db -f sql/seed_products.sql
-- =====================================================================

INSERT INTO public.categories (name, description) VALUES
    ('Drones', 'Camera and cinema drones'),
    ('Cameras', 'DSLR, mirrorless and cinema cameras'),
    ('Audio Gear', 'Microphones, recorders and mixers')
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------
-- Drones
-- ---------------------------------------------------------------------
INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'DJI Mavic 3 Cine Premium Combo', 'DJI',
    'Professional cinema drone with Hasselblad camera, 5.1K video and a 46-minute max flight time. Comes with the Fly More kit and ND filter set.',
    (SELECT id FROM public.categories WHERE name = 'Drones'),
    4500.00, 25000.00, 'mint', 'available', 4.9, 12,
    ARRAY['https://images.unsplash.com/photo-1473968512647-3e447244af8f','https://images.unsplash.com/photo-1508614999368-9260051292e5'],
    '{"sensor": "4/3 CMOS Hasselblad", "bitrate": "Apple ProRes 422 HQ", "max_flight": "46 Min Flight", "video": "5.1K/50fps"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'DJI Mavic 3 Cine Premium Combo');

INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'DJI Inspire 3 Cinema Pkg', 'DJI',
    'The ultimate aerial cinematography tool with a full-frame 8K ProRes RAW sensor, dual control and RTK positioning.',
    (SELECT id FROM public.categories WHERE name = 'Drones'),
    8500.00, 45000.00, 'excellent', 'available', 5.0, 6,
    ARRAY['https://images.unsplash.com/photo-1524143986875-3b098d78b363','https://images.unsplash.com/photo-1527977966376-1c8408f9f108'],
    '{"sensor": "Full-Frame 8K ProRes RAW", "features": ["Dual-Control", "RTK Positioning"]}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'DJI Inspire 3 Cinema Pkg');

INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'DJI FPV Combo + Goggles', 'DJI',
    'Immersive first-person-view racing drone with goggles, 4K/60fps recording and a top speed of 140 km/h.',
    (SELECT id FROM public.categories WHERE name = 'Drones'),
    2200.00, 12000.00, 'excellent', 'available', 4.7, 9,
    ARRAY['https://images.unsplash.com/photo-1527977966376-1c8408f9f108'],
    '{"top_speed": "140 km/h", "fov": "150 FOV", "video": "4K/60fps"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'DJI FPV Combo + Goggles');

-- ---------------------------------------------------------------------
-- Cameras
-- ---------------------------------------------------------------------
INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'Sony A7S III + 24-70mm G Master', 'Sony',
    'Low-light mirrorless powerhouse with 4K/120fps 10-bit 4:2:2 recording, paired with the versatile 24-70mm f/2.8 GM lens.',
    (SELECT id FROM public.categories WHERE name = 'Cameras'),
    3200.00, 18000.00, 'excellent', 'available', 4.8, 15,
    ARRAY['https://images.unsplash.com/photo-1516035069371-29a1b244cc32','https://images.unsplash.com/photo-1519638399535-1b036603ac77'],
    '{"video": "4K/120fps", "color": "10-bit 4:2:2", "iso_range": "80-102400"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'Sony A7S III + 24-70mm G Master');

INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'Blackmagic Pocket 6K G2', 'Blackmagic Design',
    'Compact cinema camera shooting 6K RAW with an EF mount, ideal for run-and-gun productions.',
    (SELECT id FROM public.categories WHERE name = 'Cameras'),
    2800.00, 15000.00, 'mint', 'available', 4.9, 8,
    ARRAY['https://images.unsplash.com/photo-1550009158-9ebf69173e03'],
    '{"sensor": "Super 35", "video": "6K RAW", "mount": "EF Mount"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'Blackmagic Pocket 6K G2');

INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'RED V-RAPTOR XL 8K Cinema Camera', 'RED',
    'Ultra-high-performance 8K VV cinema camera built for the most demanding productions, with built-in ND and Ethernet.',
    (SELECT id FROM public.categories WHERE name = 'Cameras'),
    12000.00, 60000.00, 'excellent', 'available', 5.0, 4,
    ARRAY['https://images.unsplash.com/photo-1499415479124-43c32433a620'],
    '{"sensor": "8K VV CMOS", "features": ["Built-in ND", "Ethernet"]}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'RED V-RAPTOR XL 8K Cinema Camera');

-- ---------------------------------------------------------------------
-- Audio Gear
-- ---------------------------------------------------------------------
INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'Sennheiser MKH 8060 Shotgun Mic', 'Sennheiser',
    'Short shotgun microphone with exceptional off-axis rejection, the industry standard for film and broadcast.',
    (SELECT id FROM public.categories WHERE name = 'Audio Gear'),
    900.00, 5000.00, 'good', 'available', 4.6, 11,
    ARRAY['https://images.unsplash.com/photo-1590602847861-f357a9332bbc'],
    '{"polar_pattern": "Lobar", "connector": "XLR-3"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'Sennheiser MKH 8060 Shotgun Mic');

INSERT INTO public.products (title, brand, description, category_id, rental_price_per_day, security_deposit, condition, status, average_rating, review_count, images, technical_specifications)
SELECT
    'SSL Big Six Mixer', 'Solid State Logic',
    'Hybrid analogue mixer and USB audio interface with the legendary SSL bus compressor built in.',
    (SELECT id FROM public.categories WHERE name = 'Audio Gear'),
    1800.00, 10000.00, 'excellent', 'available', 4.8, 5,
    ARRAY['https://images.unsplash.com/photo-1478737270239-2f02b77fc618'],
    '{"channels": 6, "features": ["SSL Bus Compressor", "USB Audio Interface"]}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE title = 'SSL Big Six Mixer');

-- ---------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------
-- SELECT title, rental_price_per_day, status, array_length(images,1) AS photo_count
-- FROM public.products ORDER BY created_at;
