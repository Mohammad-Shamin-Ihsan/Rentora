# Rentora — Module 1, Part 4: Ratings & Reviews
### Final build — Angular + FastAPI + Supabase (PostgreSQL)

Implements: *"After completing a rental, users can submit a rating from
1 to 5 stars and write a review. The system calculates and displays the
average rating for every product."*

Matches your team's tech stack exactly:
- **Language:** Python, JavaScript/TypeScript
- **Framework:** FastAPI, **Angular**
- **Styling:** TailwindCSS
- **Database:** PostgreSQL (hosted on Supabase, shared team database)

---

## Everything here was actually tested, not just written

- All 4 SQL migrations were run against a local Postgres instance
  seeded to match your real schema (bigint ids, your real column
  names), including simulating different users via `SET ROLE` to
  confirm RLS actually blocks/allows the right people.
- The FastAPI backend was started for real and hit with actual HTTP
  requests (`curl`), confirming `201` on a valid review, `400` on a
  duplicate, `403` on reviewing someone else's booking, `422` on an
  invalid rating.
- The Angular frontend was built with `ng build` (full AOT template
  type-checking) — compiled with zero errors.
- **The visual design was checked pixel-by-pixel against your uploaded
  mockup PDF** — colors were sampled directly from the source image
  (not eyeballed) and corrected to match exactly:
  - Star rating fill: peach/coral `#F6B8A6` (not a generic gold/amber)
  - Review card background: purple-tinted `#211A29` (not neutral grey)
  - Page background: `#17172A`
  - Removed a checkmark badge icon next to "Verified Rental" that
    isn't actually in the design — it's plain text
  - Matched avatar size, name font size, and the "Customer Feedback /
    4.9 ★★★★★ (48 Reviews)" heading row layout to the source exactly

---

## File structure

```
rentora-final-angular/
├── README.md                        ← this file
├── docs/
│   └── VIVA_GUIDE.md                 ← line-by-line explanation of every file, for your viva
│
├── sql/                               ← run these 4, IN ORDER, in Supabase SQL Editor
│   ├── A_harden_existing_reviews_table.sql
│   ├── B_rls_policies_reviews.sql
│   ├── C_cleanup_duplicates.sql
│   └── D_seed_test_data_v2.sql
│
├── backend/                           ← FastAPI
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── auth.py
│       ├── crud/reviews.py
│       └── routers/reviews.py
│
└── frontend/                          ← Angular
    ├── package.json
    ├── angular.json
    ├── tsconfig.json / tsconfig.app.json
    ├── tailwind.config.js
    ├── postcss.config.js
    └── src/
        ├── index.html
        ├── main.ts
        ├── styles.css
        ├── environments/
        │   ├── environment.ts          ← API URL for local dev
        │   └── environment.prod.ts     ← API URL for deployed backend
        └── app/
            ├── app.component.ts/html
            ├── app.config.ts            ← registers HttpClient, icons
            ├── models/review.model.ts
            ├── services/reviews.service.ts
            ├── components/
            │   ├── star-rating/
            │   ├── review-card/
            │   ├── review-form/
            │   └── reviews-section/
            └── pages/
                └── product-reviews-demo/
```

---

## Setup — in order

### 1. Database (Supabase)
Run these 4 files, in order, in the Supabase SQL Editor:
`A_harden_existing_reviews_table.sql` → `B_rls_policies_reviews.sql` →
`C_cleanup_duplicates.sql` → `D_seed_test_data_v2.sql`.

⚠️ These were written against YOUR reported schema
(`bookings.status`, `bookings.inventory_item_id`,
`inventory_items.product_id`, `users.password_hash` etc.) — if a
teammate changes those tables later, re-check before re-running.

### 2. Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Mac/Linux: source venv/bin/activate
# Windows:   venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — paste your real Supabase connection string
uvicorn app.main:app --reload
```
Visit `http://localhost:8000/docs` to test it directly.

### 3. Frontend (Angular)
```bash
cd frontend
npm install
npm start
```
This runs `ng serve`, opening the app at `http://localhost:4200`.

If your backend isn't at `http://localhost:8000`, edit
`src/environments/environment.ts` and change `apiBaseUrl`.

---

## Using the component in your real product page

```html
<app-reviews-section
  [productId]="product.id"
  [eligibleBookingId]="myCompletedUnreviewedBookingId"
  [currentUserId]="loggedInUserId">
</app-reviews-section>
```

Set `eligibleBookingId` to `null` to hide the review form (visitor
browsing, or someone who's already reviewed this booking).

**Remember:** `currentUserId` and the `X-Debug-User-Id` header
(`services/reviews.service.ts`) are a **temporary stand-in** until
Module 1 Part 1's real login system exists — see `backend/app/auth.py`
for the swap-out point.

---

## API reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/products/{product_id}/reviews` | required | submit `{ booking_id, rating, review_text }` |
| GET | `/products/{product_id}/reviews?page=&page_size=` | none | paginated review list |
| GET | `/products/{product_id}/reviews/summary` | none | `{ average_rating, review_count, breakdown }` |

Full line-by-line explanation of every file: see `docs/VIVA_GUIDE.md`.
