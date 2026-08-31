# Rentora

A rent/borrow marketplace with a secondary **Import on Demand** service — customers can rent
listed products directly, or request an item the platform doesn't carry, which the company
imports, retains ownership of, and rents out once it arrives.

Built for CSE471 (Section 8, Group 12).

## Features

**Browse, Search & Reviews**
- Category/brand/price/condition filters, keyword search, availability calendar
- Post-rental reviews and star ratings

**Rental Management**
- Booking creation with overlap prevention and server-side cost calculation
- `/rentals` page with PDF invoices
- Waiting list + notification when a booked item frees up

**Import on Demand**
- Customers submit a request → admin approves/rejects → a Cargo Manager tracks it through
  `purchased → in_transit → customs_cleared → arrived`
- On arrival, the item is automatically added to the bookable catalog
- Demand analytics: which searches come up empty most often, to guide what to import next

**Warehouse Operations**
- Return inspection, automatic inventory status updates
- Automatic late-fee calculation plus admin-entered damage penalties

**Seller Marketplace**
- Any customer can become a seller and list, edit, and delete their own products
- Sellers manage their own listings' availability (Available / Under Maintenance); items with
  an active booking show as read-only "Rented" until returned

**Also included**
- Wishlist (heart-toggle + profile page section)
- Mock escrow payments (deposit, refund, late fee/damage penalty) with a full audit trail
- In-app notifications standing in for email/SMS (nothing external is actually sent)

## Tech Stack

| Layer    | Stack |
|----------|-------|
| Backend  | FastAPI (Python 3.13), raw SQL via SQLAlchemy `text()` — no ORM models |
| Frontend | Angular 22 (standalone components, zoneless change detection), Tailwind CSS |
| Database | PostgreSQL, with native `ENUM` types (`booking_status`, `product_condition`, etc.) |

## Project Structure

```
backend/
  app/
    routers/        # one file per resource: auth, products, bookings, imports,
                     # admin, cargo, warehouse, sellers, wishlist, reviews, ...
    utils/           # notifications, auth helpers
    db_init.py       # auto-creates tables + seeds demo data on every startup
    main.py          # FastAPI app, router registration, CORS
    config.py        # env-driven settings (.env)
frontend/
  src/app/
    pages/           # one folder per route: home, browse, sell, my-listings,
                      # admin/dashboard, cargo, warehouse, rentals, import, ...
    core/             # AuthService, route guards
    shared/           # navbar and other shared components
sql/
  schema.sql          # reference schema dump (not required for setup — see below)
  seed_products.sql
```

## Run with Docker

The whole stack (Postgres + FastAPI + Angular behind nginx) runs from one file:

```bash
cp .env.docker.example .env   # optional — defaults work as-is; edit JWT_SECRET for anything real
docker compose up --build
```

Open `http://localhost:8080`. The frontend container's nginx serves the built
Angular app and proxies `/api` to the backend, so there's no CORS setup and no
backend URL to hardcode. Postgres data persists in the `pgdata` volume; the
backend seeds the demo catalog on first startup (see **Test Accounts** below).

Ports and secrets are overridable via `.env` — see `.env.docker.example`.
Stop with `docker compose down` (add `-v` to also wipe the database).

## Deploy to Render

`render.yaml` is a [Blueprint](https://render.com/docs/blueprint-spec) that
provisions a managed Postgres, the backend (from `backend/Dockerfile`), and the
frontend (static build, with `/api/*` rewritten to the backend so it stays
same-origin — no CORS).

1. Push the repo to GitHub.
2. Render dashboard → **New +** → **Blueprint** → pick the repo → **Apply**.
3. `JWT_SECRET` is auto-generated; the DB vars are wired from the managed database.

After the first deploy, if Render didn't hand out `rentora-backend.onrender.com` /
`rentora-frontend.onrender.com` (the names may be taken), update the route
`destination` and `FRONTEND_URL` in `render.yaml` to the real URLs and redeploy.
The free tiers sleep when idle and the free database is deleted after 30 days —
bump the plans for anything long-lived.

## Getting Started (local, without Docker)

### Prerequisites
- Python 3.13+
- Node.js + npm
- PostgreSQL running locally (or reachable) with an empty database created

### 1. Database

Create an empty Postgres database — no manual schema import needed. The backend's
`db_init.py` creates every table it needs (idempotently) and seeds demo data the first
time it connects to an empty database.

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
copy .env.example .env       # then fill in DB_PASSWORD and JWT_SECRET
uvicorn app.main:app --reload
```

Runs on `http://localhost:8000`. On first startup you'll see `Rentora: checking database
schema...` in the console while it creates tables and seeds the demo catalog.

### 3. Frontend

```bash
cd frontend
npm install
npm start -- --port 4201
```

Runs on `http://localhost:4201`.

### Environment variables (`backend/.env`)

| Variable | Purpose |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Postgres connection |
| `FRONTEND_URL` | Allowed CORS origin |
| `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES` | Auth token signing |

## Test Accounts

Seeded automatically by `db_init.py` on first run against an empty database (passwords are
stored in plain text — a deliberate team decision for this project, not an oversight):

| Email | Password | Role |
|---|---|---|
| `admin@rentora.com` | `admin123` | Admin |
| `cargo@rentora.com` | `cargo123` | Cargo Manager |
| `warehouse@rentora.com` | `warehouse123` | Warehouse Staff |
| `customer@rentora.com` | `customer123` | Customer |

Any account can also become a seller from the **Sell** page in the app.

## Known Limitations

- Payments and email/SMS notifications are mocked — real rows are written to the database,
  but nothing external is actually sent (no Bkash/Gmail credentials in this environment).
- No automated test suite.
- No background scheduler, so there are no "upcoming return deadline" reminder
  notifications.
