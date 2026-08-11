from sqlalchemy import text
import sys

def init_db_tables(engine):
    print("Initializing Rentora database tables...")
    try:
        with engine.begin() as conn:
            # 1. Create categories table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL
                );
            """))

            # 2. Create products table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    category_id INTEGER REFERENCES public.categories(id),
                    rental_price_per_day NUMERIC(10, 2) NOT NULL,
                    security_deposit NUMERIC(10, 2) NOT NULL,
                    condition VARCHAR(50) DEFAULT 'good',
                    status VARCHAR(50) DEFAULT 'available',
                    average_rating NUMERIC(3, 2) DEFAULT 0.00,
                    review_count INTEGER DEFAULT 0
                );
            """))

            # 3. Create inventory_items table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.inventory_items (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES public.products(id) ON DELETE CASCADE,
                    serial_number VARCHAR(100) UNIQUE NOT NULL,
                    condition VARCHAR(50) DEFAULT 'good',
                    status VARCHAR(50) DEFAULT 'available',
                    acquired_at DATE DEFAULT CURRENT_DATE
                );
            """))

            # 4. Create users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL CHECK (role IN ('customer', 'seller', 'admin', 'warehouse_staff', 'cargo_manager'))
                );
            """))

            # 5. Create bookings table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.bookings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
                    inventory_item_id INTEGER REFERENCES public.inventory_items(id) ON DELETE CASCADE,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    rental_fee NUMERIC(10, 2) NOT NULL,
                    tax NUMERIC(10, 2) NOT NULL,
                    security_deposit NUMERIC(10, 2) NOT NULL,
                    total_amount NUMERIC(10, 2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'active', 'completed', 'cancelled'))
                );
            """))

            # 6. Create reviews table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.reviews (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER UNIQUE REFERENCES public.bookings(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES public.products(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    review_text TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))

            # 7. Create waiting_list table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.waiting_list (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES public.products(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
                    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    notified_at TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'notified', 'cancelled')),
                    UNIQUE (product_id, user_id, status)
                );
            """))

            # 8. Create notifications table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
                    message TEXT NOT NULL,
                    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_read BOOLEAN DEFAULT FALSE
                );
            """))

            # Indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON public.reviews (product_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON public.reviews (user_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_waiting_list_product_id ON public.waiting_list (product_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_waiting_list_status ON public.waiting_list (status);"))

            # Triggers & Functions from Migration A
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION public.fn_reviews_set_product_id()
                RETURNS trigger
                LANGUAGE plpgsql
                SECURITY DEFINER
                SET search_path = public
                AS $$
                BEGIN
                  IF new.product_id IS NULL THEN
                    SELECT ii.product_id
                      INTO new.product_id
                      FROM public.bookings b
                      JOIN public.inventory_items ii ON ii.id = b.inventory_item_id
                     WHERE b.id = new.booking_id;

                    IF new.product_id IS NULL THEN
                      RAISE EXCEPTION
                        'Could not resolve product_id for booking % — check bookings.inventory_item_id and inventory_items.product_id',
                        new.booking_id;
                    END IF;
                  END IF;
                  RETURN new;
                END;
                $$;
            """))

            conn.execute(text("""
                DROP TRIGGER IF EXISTS trg_reviews_set_product_id ON public.reviews;
                CREATE TRIGGER trg_reviews_set_product_id
                BEFORE INSERT ON public.reviews
                FOR EACH ROW EXECUTE FUNCTION public.fn_reviews_set_product_id();
            """))

            conn.execute(text("""
                CREATE OR REPLACE FUNCTION public.fn_recompute_product_rating()
                RETURNS trigger
                LANGUAGE plpgsql
                SECURITY DEFINER
                SET search_path = public
                AS $$
                DECLARE
                  target_product_id bigint := coalesce(new.product_id, old.product_id);
                BEGIN
                  UPDATE public.products p
                     SET average_rating = coalesce(sub.avg_rating, 0),
                         review_count   = coalesce(sub.review_total, 0)
                    FROM (
                      SELECT round(avg(rating)::numeric, 2) as avg_rating,
                             count(*)                        as review_total
                        FROM public.reviews
                       WHERE product_id = target_product_id
                    ) sub
                   WHERE p.id = target_product_id;

                  RETURN coalesce(new, old);
                END;
                $$;
            """))

            conn.execute(text("""
                DROP TRIGGER IF EXISTS trg_reviews_recompute_after_insert ON public.reviews;
                CREATE TRIGGER trg_reviews_recompute_after_insert
                AFTER INSERT ON public.reviews
                FOR EACH ROW EXECUTE FUNCTION public.fn_recompute_product_rating();
            """))

            conn.execute(text("""
                DROP TRIGGER IF EXISTS trg_reviews_recompute_after_update ON public.reviews;
                CREATE TRIGGER trg_reviews_recompute_after_update
                AFTER UPDATE OF rating ON public.reviews
                FOR EACH ROW EXECUTE FUNCTION public.fn_recompute_product_rating();
            """))

            conn.execute(text("""
                DROP TRIGGER IF EXISTS trg_reviews_recompute_after_delete ON public.reviews;
                CREATE TRIGGER trg_reviews_recompute_after_delete
                AFTER DELETE ON public.reviews
                FOR EACH ROW EXECUTE FUNCTION public.fn_recompute_product_rating();
            """))

            conn.execute(text("""
                CREATE OR REPLACE FUNCTION public.fn_reviews_set_updated_at()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                  new.updated_at = now();
                  RETURN new;
                END;
                $$;
            """))

            conn.execute(text("""
                DROP TRIGGER IF EXISTS trg_reviews_set_updated_at ON public.reviews;
                CREATE TRIGGER trg_reviews_set_updated_at
                BEFORE UPDATE ON public.reviews
                FOR EACH ROW EXECUTE FUNCTION public.fn_reviews_set_updated_at();
            """))

            # Seed Categories if empty
            cat_count = conn.execute(text("SELECT COUNT(*) FROM public.categories")).scalar()
            if cat_count == 0:
                conn.execute(text("INSERT INTO public.categories (name) VALUES ('Drones')"))
                print("Seeded Category: Drones")

            # Seed Products if empty
            prod_count = conn.execute(text("SELECT COUNT(*) FROM public.products")).scalar()
            if prod_count == 0:
                conn.execute(text("""
                    INSERT INTO public.products (name, description, category_id, rental_price_per_day, security_deposit, condition, status)
                    VALUES ('DJI Mavic 3 Cine Premium Combo', 'Professional cinema drone with Hasselblad camera', 1, 149.00, 850.00, 'mint', 'available');
                """))
                print("Seeded Product: DJI Mavic 3 Cine Premium Combo")

            # Seed Inventory if empty
            inv_count = conn.execute(text("SELECT COUNT(*) FROM public.inventory_items")).scalar()
            if inv_count == 0:
                conn.execute(text("""
                    INSERT INTO public.inventory_items (product_id, serial_number, condition, status, acquired_at)
                    VALUES (1, 'MAVIC-001', 'mint', 'available', CURRENT_DATE);
                """))
                print("Seeded Inventory Item: MAVIC-001")

            # Seed Users if empty
            user_count = conn.execute(text("SELECT COUNT(*) FROM public.users")).scalar()
            if user_count == 0:
                conn.execute(text("""
                    INSERT INTO public.users (name, email, password_hash, role) VALUES
                    ('Julian D.', 'julian.d@example.com', 'pwd_hash_julian', 'customer'),
                    ('Sarah K.', 'sarah.k@example.com', 'pwd_hash_sarah', 'customer'),
                    ('Alex M.', 'alex.m@example.com', 'pwd_hash_alex', 'customer'),
                    ('Admin User', 'admin@rentora.com', 'pwd_hash_admin', 'admin');
                """))
                print("Seeded Users: Julian, Sarah, Alex, Admin")

            # Seed Booking if empty (so Julian can leave a review as in the original design)
            booking_count = conn.execute(text("SELECT COUNT(*) FROM public.bookings")).scalar()
            if booking_count == 0:
                conn.execute(text("""
                    INSERT INTO public.bookings (user_id, inventory_item_id, start_date, end_date, rental_fee, tax, security_deposit, total_amount, status)
                    VALUES (1, 1, CURRENT_DATE - 5, CURRENT_DATE - 2, 447.00, 44.70, 850.00, 1341.70, 'completed');
                """))
                print("Seeded Completed Booking for Julian D.")

        print("Rentora database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        raise e
