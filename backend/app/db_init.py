"""
Auto-creates every table Rentora's routers expect, and seeds a starter
product catalog, the moment the backend starts up.

Why this exists: this repo ships with no models.py / migrations / schema
file anywhere — every router (backend/app/routers/*.py) fires raw SQL at
tables it just assumes already exist, a leftover from when it ran against
a shared Supabase Postgres instance. Against a genuinely empty local
database there was nothing to query, so the browse page had no products
(no picture, no price) and every other endpoint would 500 on first use.

Every statement below is idempotent (CREATE TABLE IF NOT EXISTS / ON
CONFLICT DO NOTHING / a NOT EXISTS guard on seed rows), so this is safe
to run on every single startup — it only ever fills in what's missing.
"""
from sqlalchemy import text
import sys


def init_db_tables(engine):
    print("Rentora: checking database schema...")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.categories (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name        VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT
                );
            """))

            conn.execute(text("""
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
            """))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_category_id ON public.products (category_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_status ON public.products (status);"))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.product_availability (
                    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
                    start_date DATE NOT NULL,
                    end_date   DATE NOT NULL,
                    status     VARCHAR(50) NOT NULL CHECK (status IN ('maintenance', 'unavailable'))
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_product_availability_product_id ON public.product_availability (product_id);"))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_product_id ON public.bookings (product_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_customer_id ON public.bookings (customer_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_status ON public.bookings (status);"))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON public.payments (booking_id);"))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON public.reviews (product_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_customer_id ON public.reviews (customer_id);"))

            conn.execute(text("""
                CREATE OR REPLACE FUNCTION public.fn_reviews_set_updated_at()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  NEW.updated_at = now();
                  RETURN NEW;
                END;
                $$;
            """))
            conn.execute(text("DROP TRIGGER IF EXISTS trg_reviews_set_updated_at ON public.reviews;"))
            conn.execute(text("""
                CREATE TRIGGER trg_reviews_set_updated_at
                BEFORE UPDATE ON public.reviews
                FOR EACH ROW EXECUTE FUNCTION public.fn_reviews_set_updated_at();
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.waiting_lists (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    product_id  UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
                    customer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
                    status      VARCHAR(50) NOT NULL DEFAULT 'waiting'
                                CHECK (status IN ('waiting', 'notified')),
                    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_waiting_lists_product_id ON public.waiting_lists (product_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_waiting_lists_status ON public.waiting_lists (status);"))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.notifications (
                    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id    UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
                    title      VARCHAR(255) NOT NULL,
                    message    TEXT NOT NULL,
                    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications (user_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON public.notifications (is_read);"))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_import_requests_customer_id ON public.import_requests (customer_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_import_requests_status ON public.import_requests (status);"))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cargo_shipments_import_request_id ON public.cargo_shipments (import_request_id);"))

            conn.execute(text("""
                CREATE OR REPLACE FUNCTION public.fn_cargo_shipments_set_updated_at()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  NEW.updated_at = now();
                  RETURN NEW;
                END;
                $$;
            """))
            conn.execute(text("DROP TRIGGER IF EXISTS trg_cargo_shipments_set_updated_at ON public.cargo_shipments;"))
            conn.execute(text("""
                CREATE TRIGGER trg_cargo_shipments_set_updated_at
                BEFORE UPDATE ON public.cargo_shipments
                FOR EACH ROW EXECUTE FUNCTION public.fn_cargo_shipments_set_updated_at();
            """))

            conn.execute(text("""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_returns_and_inspections_booking_id ON public.returns_and_inspections (booking_id);"))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.demand_analytics (
                    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    search_term   VARCHAR(255) NOT NULL,
                    was_available BOOLEAN NOT NULL,
                    searched_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_demand_analytics_search_term ON public.demand_analytics (search_term);"))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.wishlists (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    customer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
                    product_id  UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (customer_id, product_id)
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wishlists_customer_id ON public.wishlists (customer_id);"))

            print("Rentora: tables OK. Checking seed data...")

            # ---- Seed: categories -----------------------------------
            # ON CONFLICT DO NOTHING means this always runs safely on
            # every startup — existing categories are left alone, and
            # any new ones added here later just get appended.
            conn.execute(text("""
                INSERT INTO public.categories (name, description) VALUES
                    ('Drones', 'Camera and cinema drones'),
                    ('Cameras', 'DSLR, mirrorless and cinema cameras'),
                    ('Audio Gear', 'Microphones, recorders and mixers'),
                    ('Bags', 'Handbags, backpacks and luggage bags'),
                    ('Shoes', 'Sneakers, heels and formal footwear'),
                    ('Dresses', 'Gowns, bridal wear and party dresses'),
                    ('Home Appliances', 'Kitchen, cleaning and household appliances'),
                    ('Electronic Devices', 'Laptops, tablets, phones and gadgets'),
                    ('Travel', 'Suitcases, travel gear and accessories'),
                    ('Wedding Wear', 'Bridal gowns, suits and wedding accessories'),
                    ('Tools', 'Power tools and equipment'),
                    ('Camping & Outdoor', 'Tents, hiking gear and outdoor equipment'),
                    ('Furniture', 'Event and home furniture'),
                    ('Jewelry', 'Fine jewelry and accessories')
                ON CONFLICT (name) DO NOTHING;
            """))

            # ---- Seed: test accounts (admin/register only allows
            # customer/seller, so these roles can't be created any
            # other way) ------------------------------------------
            conn.execute(text("""
                INSERT INTO public.profiles (full_name, email, password_hash, role) VALUES
                    ('Admin User',      'admin@rentora.com',      'admin123',      'admin'),
                    ('Warehouse Staff', 'warehouse@rentora.com',  'warehouse123',  'warehouse_staff'),
                    ('Cargo Manager',   'cargo@rentora.com',      'cargo123',      'cargo_manager'),
                    ('Test Customer',   'customer@rentora.com',   'customer123',   'customer'),
                    ('Arif Rahman',     'arif.rahman@example.com',  'password123', 'customer'),
                    ('Nusrat Jahan',    'nusrat.jahan@example.com', 'password123', 'customer')
                ON CONFLICT (email) DO NOTHING;
            """))

            # ---- Seed: product catalog ---------------------------
            # Checked one-by-one by title (not just "is the table
            # empty") so that re-running this after new items are
            # added to the list below still fills in the new ones,
            # without touching or duplicating what's already there.
            if True:
                products_to_seed = [
                    {
                        "title": "DJI Mavic 3 Cine Premium Combo", "brand": "DJI", "category": "Drones",
                        "description": "Professional cinema drone with Hasselblad camera, 5.1K video and a 46-minute max flight time. Comes with the Fly More kit and ND filter set.",
                        "price": 4500.00, "deposit": 25000.00, "condition": "mint", "rating": 4.9, "reviews": 12,
                        "images": ["https://images.unsplash.com/photo-1473968512647-3e447244af8f", "https://images.unsplash.com/photo-1508614999368-9260051292e5"],
                        "specs": '{"sensor": "4/3 CMOS Hasselblad", "bitrate": "Apple ProRes 422 HQ", "max_flight": "46 Min Flight", "video": "5.1K/50fps"}',
                    },
                    {
                        "title": "DJI Inspire 3 Cinema Pkg", "brand": "DJI", "category": "Drones",
                        "description": "The ultimate aerial cinematography tool with a full-frame 8K ProRes RAW sensor, dual control and RTK positioning.",
                        "price": 8500.00, "deposit": 45000.00, "condition": "excellent", "rating": 5.0, "reviews": 6,
                        "images": ["https://images.unsplash.com/photo-1524143986875-3b098d78b363", "https://images.unsplash.com/photo-1527977966376-1c8408f9f108"],
                        "specs": '{"sensor": "Full-Frame 8K ProRes RAW", "features": ["Dual-Control", "RTK Positioning"]}',
                    },
                    {
                        "title": "DJI FPV Combo + Goggles", "brand": "DJI", "category": "Drones",
                        "description": "Immersive first-person-view racing drone with goggles, 4K/60fps recording and a top speed of 140 km/h.",
                        "price": 2200.00, "deposit": 12000.00, "condition": "excellent", "rating": 4.7, "reviews": 9,
                        "images": ["https://images.unsplash.com/photo-1527977966376-1c8408f9f108"],
                        "specs": '{"top_speed": "140 km/h", "fov": "150 FOV", "video": "4K/60fps"}',
                    },
                    {
                        "title": "Sony A7S III + 24-70mm G Master", "brand": "Sony", "category": "Cameras",
                        "description": "Low-light mirrorless powerhouse with 4K/120fps 10-bit 4:2:2 recording, paired with the versatile 24-70mm f/2.8 GM lens.",
                        "price": 3200.00, "deposit": 18000.00, "condition": "excellent", "rating": 4.8, "reviews": 15,
                        "images": ["https://images.unsplash.com/photo-1516035069371-29a1b244cc32", "https://images.unsplash.com/photo-1519638399535-1b036603ac77"],
                        "specs": '{"video": "4K/120fps", "color": "10-bit 4:2:2", "iso_range": "80-102400"}',
                    },
                    {
                        "title": "Blackmagic Pocket 6K G2", "brand": "Blackmagic Design", "category": "Cameras",
                        "description": "Compact cinema camera shooting 6K RAW with an EF mount, ideal for run-and-gun productions.",
                        "price": 2800.00, "deposit": 15000.00, "condition": "mint", "rating": 4.9, "reviews": 8,
                        "images": ["https://images.unsplash.com/photo-1550009158-9ebf69173e03"],
                        "specs": '{"sensor": "Super 35", "video": "6K RAW", "mount": "EF Mount"}',
                    },
                    {
                        "title": "RED V-RAPTOR XL 8K Cinema Camera", "brand": "RED", "category": "Cameras",
                        "description": "Ultra-high-performance 8K VV cinema camera built for the most demanding productions, with built-in ND and Ethernet.",
                        "price": 12000.00, "deposit": 60000.00, "condition": "excellent", "rating": 5.0, "reviews": 4,
                        "images": ["https://images.unsplash.com/photo-1499415479124-43c32433a620"],
                        "specs": '{"sensor": "8K VV CMOS", "features": ["Built-in ND", "Ethernet"]}',
                    },
                    {
                        "title": "Sennheiser MKH 8060 Shotgun Mic", "brand": "Sennheiser", "category": "Audio Gear",
                        "description": "Short shotgun microphone with exceptional off-axis rejection, the industry standard for film and broadcast.",
                        "price": 900.00, "deposit": 5000.00, "condition": "good", "rating": 4.6, "reviews": 11,
                        "images": ["https://images.unsplash.com/photo-1590602847861-f357a9332bbc"],
                        "specs": '{"polar_pattern": "Lobar", "connector": "XLR-3"}',
                    },
                    {
                        "title": "SSL Big Six Mixer", "brand": "Solid State Logic", "category": "Audio Gear",
                        "description": "Hybrid analogue mixer and USB audio interface with the legendary SSL bus compressor built in.",
                        "price": 1800.00, "deposit": 10000.00, "condition": "excellent", "rating": 4.8, "reviews": 5,
                        "images": ["https://images.unsplash.com/photo-1478737270239-2f02b77fc618"],
                        "specs": '{"channels": 6, "features": ["SSL Bus Compressor", "USB Audio Interface"]}',
                    },
                    {
                        "title": "Louis Vuitton Neverfull MM Tote", "brand": "Louis Vuitton", "category": "Bags",
                        "description": "Iconic monogram canvas tote, roomy enough for everyday essentials with a timeless silhouette.",
                        "price": 1200.00, "deposit": 15000.00, "condition": "excellent", "rating": 4.9, "reviews": 7,
                        "images": ["https://images.unsplash.com/photo-1548036328-c9fa89d128fa"],
                        "specs": '{"material": "Monogram Canvas", "includes": "Dust bag, pochette"}',
                    },
                    {
                        "title": "Nike Air Jordan 1 Retro High", "brand": "Nike", "category": "Shoes",
                        "description": "The legendary silhouette in its original high-top colorway, perfect for events and photoshoots.",
                        "price": 400.00, "deposit": 4000.00, "condition": "good", "rating": 4.5, "reviews": 6,
                        "images": ["https://images.unsplash.com/photo-1542291026-7eec264c27ff"],
                        "specs": '{"sizes_available": "US 7-12", "colorway": "Chicago"}',
                    },
                    {
                        "title": "Vera Wang Bridal Gown", "brand": "Vera Wang", "category": "Dresses",
                        "description": "Hand-beaded silk bridal gown with a cathedral train — the centerpiece for your wedding day.",
                        "price": 3500.00, "deposit": 40000.00, "condition": "excellent", "rating": 5.0, "reviews": 9,
                        "images": ["https://images.unsplash.com/photo-1594736797933-d0501ba2fe65"],
                        "specs": '{"fabric": "Silk & Beaded Lace", "sizes_available": "US 2-14"}',
                    },
                    {
                        "title": "Dyson V15 Detect Vacuum", "brand": "Dyson", "category": "Home Appliances",
                        "description": "Laser dust-detection cordless vacuum with powerful suction for a deep, thorough clean.",
                        "price": 500.00, "deposit": 6000.00, "condition": "mint", "rating": 4.7, "reviews": 10,
                        "images": ["https://images.unsplash.com/photo-1558317374-067fb5f30001"],
                        "specs": '{"battery_life": "60 min", "features": ["Laser Dust Detect", "HEPA Filtration"]}',
                    },
                    {
                        "title": "MacBook Pro 16 M3 Max", "brand": "Apple", "category": "Electronic Devices",
                        "description": "Top-spec creative powerhouse laptop for video editing, 3D rendering and heavy multitasking.",
                        "price": 1500.00, "deposit": 25000.00, "condition": "excellent", "rating": 4.9, "reviews": 14,
                        "images": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8"],
                        "specs": '{"chip": "Apple M3 Max", "ram": "36GB", "storage": "1TB SSD"}',
                    },
                    {
                        "title": "Samsonite Hardside Luggage Set", "brand": "Samsonite", "category": "Travel",
                        "description": "3-piece hardside spinner luggage set — durable, lightweight, and ready for any trip.",
                        "price": 300.00, "deposit": 3000.00, "condition": "good", "rating": 4.4, "reviews": 5,
                        "images": ["https://images.unsplash.com/photo-1553440569-bcc63803a83d"],
                        "specs": '{"pieces": 3, "material": "Polycarbonate"}',
                    },
                    {
                        "title": "Designer Sherwani Groom Set", "brand": "Manyavar", "category": "Wedding Wear",
                        "description": "Hand-embroidered groom's sherwani with matching stole, ideal for the wedding ceremony.",
                        "price": 2000.00, "deposit": 15000.00, "condition": "excellent", "rating": 4.8, "reviews": 6,
                        "images": ["https://images.unsplash.com/photo-1594938298603-c8148c4dae35"],
                        "specs": '{"fabric": "Silk Blend", "sizes_available": "S-XXL"}',
                    },
                    {
                        "title": "DeWalt Power Tool Combo Kit", "brand": "DeWalt", "category": "Tools",
                        "description": "20V cordless drill, impact driver and circular saw combo kit with two batteries and a case.",
                        "price": 450.00, "deposit": 5000.00, "condition": "good", "rating": 4.6, "reviews": 8,
                        "images": ["https://images.unsplash.com/photo-1504148455328-c376907d081c"],
                        "specs": '{"voltage": "20V MAX", "pieces": 3}',
                    },
                    {
                        "title": "REI Co-op Half Dome Tent", "brand": "REI", "category": "Camping & Outdoor",
                        "description": "4-person freestanding dome tent, easy setup, great ventilation for weekend camping trips.",
                        "price": 300.00, "deposit": 3000.00, "condition": "excellent", "rating": 4.7, "reviews": 11,
                        "images": ["https://images.unsplash.com/photo-1504280390367-361c6d9f38f4"],
                        "specs": '{"capacity": "4 person", "weight": "5.4 kg"}',
                    },
                    {
                        "title": "Event Chiavari Chairs (Set of 50)", "brand": "Generic", "category": "Furniture",
                        "description": "Elegant gold chiavari chairs for weddings and events, rented in sets of 50 with cushions included.",
                        "price": 2500.00, "deposit": 10000.00, "condition": "excellent", "rating": 4.5, "reviews": 4,
                        "images": ["https://images.unsplash.com/photo-1519167758481-83f550bb49b3"],
                        "specs": '{"set_size": 50, "includes": "Seat cushions"}',
                    },
                    {
                        "title": "Diamond Tennis Bracelet", "brand": "Tiffany & Co.", "category": "Jewelry",
                        "description": "Classic diamond tennis bracelet in platinum setting, perfect for galas and special occasions.",
                        "price": 1500.00, "deposit": 50000.00, "condition": "mint", "rating": 5.0, "reviews": 3,
                        "images": ["https://images.unsplash.com/photo-1515562141207-7a88fb7ce338"],
                        "specs": '{"metal": "Platinum", "carat_weight": "5ct total"}',
                    },
                ]

                seeded_count = 0
                for p in products_to_seed:
                    already_exists = conn.execute(
                        text("SELECT 1 FROM public.products WHERE title = :title"),
                        {"title": p["title"]}
                    ).fetchone()
                    if already_exists:
                        continue

                    conn.execute(
                        text("""
                            INSERT INTO public.products
                                (title, brand, description, category_id, rental_price_per_day,
                                 security_deposit, condition, status, average_rating, review_count,
                                 images, technical_specifications)
                            VALUES
                                (:title, :brand, :description,
                                 (SELECT id FROM public.categories WHERE name = :category),
                                 :price, :deposit, :condition, 'available', :rating, :reviews,
                                 :images, CAST(:specs AS jsonb))
                        """),
                        {
                            "title": p["title"], "brand": p["brand"], "description": p["description"],
                            "category": p["category"], "price": p["price"], "deposit": p["deposit"],
                            "condition": p["condition"], "rating": p["rating"], "reviews": p["reviews"],
                            "images": p["images"], "specs": p["specs"],
                        }
                    )
                    seeded_count += 1

                if seeded_count:
                    print(f"Rentora: seeded {seeded_count} new product(s).")
                else:
                    print("Rentora: product catalog already up to date.")

            # ---- Seed: rental history demo data ----------------------
            # A handful of realistic past/active/upcoming bookings with
            # payments, return inspections and reviews, so the admin
            # dashboard's Rentals tab and the customer-facing rentals/
            # reviews pages have real data to show instead of being
            # empty. Only runs once — guarded on bookings being empty,
            # so it never touches real bookings once the app is in use.
            booking_count = conn.execute(text("SELECT COUNT(*) FROM public.bookings")).scalar()
            if booking_count == 0:
                print("Rentora: seeding demo rental history...")

                def profile_id(email):
                    return conn.execute(
                        text("SELECT id FROM public.profiles WHERE email = :e"), {"e": email}
                    ).scalar()

                def product_id(title):
                    return conn.execute(
                        text("SELECT id FROM public.products WHERE title = :t"), {"t": title}
                    ).scalar()

                customer_id = profile_id("customer@rentora.com")
                arif_id     = profile_id("arif.rahman@example.com")
                nusrat_id   = profile_id("nusrat.jahan@example.com")
                staff_id    = profile_id("warehouse@rentora.com")

                mavic_id   = product_id("DJI Mavic 3 Cine Premium Combo")
                sony_id    = product_id("Sony A7S III + 24-70mm G Master")
                gown_id    = product_id("Vera Wang Bridal Gown")
                jordan_id  = product_id("Nike Air Jordan 1 Retro High")
                macbook_id = product_id("MacBook Pro 16 M3 Max")
                tent_id    = product_id("REI Co-op Half Dome Tent")

                def make_booking(customer, product, start_days_ago, end_days_ago, rental_fee, tax, deposit, status):
                    """days_ago: how many days before today. Negative = in the future."""
                    total = round(rental_fee + tax + deposit, 2)
                    booking_id = conn.execute(
                        text("""
                            INSERT INTO public.bookings
                                (product_id, customer_id, start_date, end_date,
                                 total_rental_fee, tax, security_deposit, total_amount, status)
                            VALUES
                                (:product_id, :customer_id,
                                 CURRENT_DATE - make_interval(days => :start_days_ago),
                                 CURRENT_DATE - make_interval(days => :end_days_ago),
                                 :rental_fee, :tax, :deposit, :total, :status)
                            RETURNING id
                        """),
                        {
                            "product_id": product, "customer_id": customer,
                            "start_days_ago": start_days_ago, "end_days_ago": end_days_ago,
                            "rental_fee": rental_fee, "tax": tax, "deposit": deposit,
                            "total": total, "status": status
                        }
                    ).scalar()

                    conn.execute(
                        text("""
                            INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                            VALUES (:booking_id, :amount, 'rental_fee', 'completed', :ref)
                        """),
                        {"booking_id": booking_id, "amount": round(rental_fee + tax, 2), "ref": f"DEMO-RENT-{booking_id}"}
                    )
                    conn.execute(
                        text("""
                            INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                            VALUES (:booking_id, :amount, 'security_deposit',
                                    CASE WHEN :status = 'completed' THEN 'refunded' ELSE 'escrow' END, :ref)
                        """),
                        {"booking_id": booking_id, "amount": deposit, "status": status, "ref": f"DEMO-DEPOSIT-{booking_id}"}
                    )
                    return booking_id

                def complete_return(booking_id, customer, product, return_days_ago, condition,
                                     damage_description, damage_penalty, late_fee, deposit,
                                     rating, review_text):
                    conn.execute(
                        text("""
                            INSERT INTO public.returns_and_inspections
                                (booking_id, warehouse_staff_id, return_date, condition_on_return,
                                 needs_maintenance, damage_description, damage_penalty_amount, late_fee_amount)
                            VALUES
                                (:booking_id, :staff_id,
                                 CURRENT_DATE - make_interval(days => :return_days_ago),
                                 :condition, false, :damage_description, :damage_penalty, :late_fee)
                        """),
                        {
                            "booking_id": booking_id, "staff_id": staff_id, "return_days_ago": return_days_ago,
                            "condition": condition, "damage_description": damage_description,
                            "damage_penalty": damage_penalty, "late_fee": late_fee
                        }
                    )

                    if late_fee > 0:
                        conn.execute(
                            text("""
                                INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                                VALUES (:booking_id, :amount, 'late_fee', 'completed', :ref)
                            """),
                            {"booking_id": booking_id, "amount": late_fee, "ref": f"DEMO-LATEFEE-{booking_id}"}
                        )
                    if damage_penalty > 0:
                        conn.execute(
                            text("""
                                INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                                VALUES (:booking_id, :amount, 'damage_penalty', 'completed', :ref)
                            """),
                            {"booking_id": booking_id, "amount": damage_penalty, "ref": f"DEMO-PENALTY-{booking_id}"}
                        )
                    refund_amount = round(deposit - damage_penalty - late_fee, 2)
                    if refund_amount > 0:
                        conn.execute(
                            text("""
                                INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                                VALUES (:booking_id, :amount, 'refund', 'completed', :ref)
                            """),
                            {"booking_id": booking_id, "amount": refund_amount, "ref": f"DEMO-REFUND-{booking_id}"}
                        )

                    conn.execute(
                        text("""
                            INSERT INTO public.reviews (product_id, customer_id, booking_id, rating, review_text)
                            VALUES (:product_id, :customer_id, :booking_id, :rating, :review_text)
                        """),
                        {
                            "product_id": product, "customer_id": customer, "booking_id": booking_id,
                            "rating": rating, "review_text": review_text
                        }
                    )

                # 1. Clean, on-time return — DJI Mavic 3
                b1 = make_booking(customer_id, mavic_id, 10, 7, 13500.00, 675.00, 25000.00, 'completed')
                complete_return(b1, customer_id, mavic_id, 7, 'excellent', None, 0, 0, 25000.00,
                                 5, "Amazing drone, footage was stunning and pickup process was smooth!")

                # 2. Returned 2 days late — Sony A7S III
                b2 = make_booking(arif_id, sony_id, 15, 12, 9600.00, 480.00, 18000.00, 'completed')
                complete_return(b2, arif_id, sony_id, 10, 'good', None, 0, 6400.00, 18000.00,
                                 4, "Great camera, returned it a couple days late by accident but the team was understanding. Video quality is incredible.")

                # 3. Clean, on-time return — Vera Wang Bridal Gown
                b3 = make_booking(nusrat_id, gown_id, 20, 18, 7000.00, 350.00, 40000.00, 'completed')
                complete_return(b3, nusrat_id, gown_id, 18, 'excellent', None, 0, 0, 40000.00,
                                 5, "Absolutely gorgeous gown, fit perfectly for my sister's wedding. Highly recommend Rentora!")

                # 4. Returned with minor damage — Nike Air Jordan 1
                b4 = make_booking(nusrat_id, jordan_id, 8, 6, 800.00, 40.00, 4000.00, 'completed')
                complete_return(b4, nusrat_id, jordan_id, 6, 'fair', 'Sole showing wear, small scuff on toe box', 800.00, 0, 4000.00,
                                 3, "Shoes were nice but arrived with a bit more wear than expected. Comfortable for the event though.")

                # 5. Currently active, not yet returned — MacBook Pro
                make_booking(customer_id, macbook_id, 2, -3, 7500.00, 375.00, 25000.00, 'active')

                # 6. Confirmed, awaiting admin to start the rental — REI Tent
                make_booking(arif_id, tent_id, -1, -4, 1200.00, 60.00, 3000.00, 'confirmed')

                # Recompute average_rating / review_count for the products
                # that just got real reviews, from the actual review rows.
                for pid in (mavic_id, sony_id, gown_id, jordan_id):
                    conn.execute(
                        text("""
                            UPDATE public.products p
                            SET average_rating = sub.avg_rating,
                                review_count   = sub.review_total
                            FROM (
                                SELECT round(avg(rating)::numeric, 2) as avg_rating, count(*) as review_total
                                FROM public.reviews WHERE product_id = :pid
                            ) sub
                            WHERE p.id = :pid
                        """),
                        {"pid": pid}
                    )

                print("Rentora: seeded 6 demo bookings (4 completed w/ reviews, 1 active, 1 confirmed).")
            else:
                print(f"Rentora: bookings table already has {booking_count} row(s), skipping rental history seed.")

            # ---- Seed: demand analytics -------------------------------
            # Search-term activity for the admin Demand Analytics tab —
            # normally populated by real visitor searches on the browse
            # page, seeded here so the tab isn't empty on a fresh demo.
            demand_count = conn.execute(text("SELECT COUNT(*) FROM public.demand_analytics")).scalar()
            if demand_count == 0:
                demo_searches = (
                    [("gimbal stabilizer", False)] * 4 +
                    [("professional lighting kit", False)] * 3 +
                    [("action camera", True)] * 5 +
                    [("wedding dress", True)] * 4 +
                    [("drone", True)] * 6 +
                    [("laptop", True)] * 3 +
                    [("bridal jewelry", False)] * 2 +
                    [("camping tent", True)] * 3 +
                    [("power tools", True)] * 2 +
                    [("designer handbag", False)] * 3
                )
                for i, (term, available) in enumerate(demo_searches):
                    conn.execute(
                        text("""
                            INSERT INTO public.demand_analytics (search_term, was_available, searched_at)
                            VALUES (:term, :available, now() - make_interval(days => :days_ago))
                        """),
                        {"term": term, "available": available, "days_ago": i % 14}
                    )
                print(f"Rentora: seeded {len(demo_searches)} demand analytics entries.")

            # ---- Seed: import requests + cargo shipments ---------------
            # Demo data for the "Import on Demand" pipeline: one still
            # awaiting admin review, and three already approved sitting at
            # different cargo stages, so both the customer's shipment
            # tracker and the admin's cargo tracking view have real data
            # to show instead of being empty on a fresh demo.
            import_count = conn.execute(text("SELECT COUNT(*) FROM public.import_requests")).scalar()
            if import_count == 0:
                cust_id  = conn.execute(text("SELECT id FROM public.profiles WHERE email = 'customer@rentora.com'")).scalar()
                arif_id  = conn.execute(text("SELECT id FROM public.profiles WHERE email = 'arif.rahman@example.com'")).scalar()
                nusrat_id = conn.execute(text("SELECT id FROM public.profiles WHERE email = 'nusrat.jahan@example.com'")).scalar()
                cargo_mgr_id = conn.execute(text("SELECT id FROM public.profiles WHERE email = 'cargo@rentora.com'")).scalar()

                def seed_import(customer_id, product_name, description, duration_days, budget,
                                 extra_notes, status, shipment_status, tracking_notes):
                    req_id = conn.execute(
                        text("""
                            INSERT INTO public.import_requests
                                (customer_id, product_name, product_description,
                                 preferred_rental_duration_days, estimated_budget,
                                 additional_requirements, status)
                            VALUES
                                (:customer_id, :product_name, :description,
                                 :duration_days, :budget, :extra_notes, :status)
                            RETURNING id
                        """),
                        {
                            "customer_id": customer_id, "product_name": product_name,
                            "description": description, "duration_days": duration_days,
                            "budget": budget, "extra_notes": extra_notes, "status": status
                        }
                    ).scalar()

                    if shipment_status:
                        conn.execute(
                            text("""
                                INSERT INTO public.cargo_shipments
                                    (import_request_id, status, tracking_notes, cargo_manager_id)
                                VALUES
                                    (:req_id, :status, :notes, :mgr_id)
                            """),
                            {"req_id": req_id, "status": shipment_status,
                             "notes": tracking_notes, "mgr_id": cargo_mgr_id}
                        )
                    return req_id

                seed_import(
                    cust_id, "Canon EOS R5 C Cinema Camera",
                    "Need it for a two-day documentary shoot, prefer with an extra battery.",
                    5, 180000.00, "Would like a spare battery included if possible.",
                    "pending", None, None
                )
                seed_import(
                    arif_id, "GoPro Hero 12 Black + Accessories Kit",
                    "For an upcoming diving trip, need the underwater housing too.",
                    7, 45000.00, None,
                    "approved", "purchased", "Order placed with supplier, awaiting dispatch."
                )
                seed_import(
                    nusrat_id, "Bose QuietComfort Ultra Headphones",
                    "For a long-haul flight, need noise cancelling.",
                    10, 55000.00, None,
                    "approved", "in_transit",
                    "Package left supplier warehouse in Dubai, expected to clear customs within 5 days."
                )
                seed_import(
                    cust_id, "Herman Miller Aeron Office Chair",
                    "Setting up a temporary home office for a client project.",
                    30, 90000.00, None,
                    "approved", "customs_cleared",
                    "Cleared Dhaka customs, out for final delivery to our warehouse."
                )
                print("Rentora: seeded 4 demo import requests (1 pending, 3 in the cargo pipeline).")

        print("Rentora: database ready.")
    except Exception as e:
        print(f"Rentora: error initializing database: {e}", file=sys.stderr)
        raise e
