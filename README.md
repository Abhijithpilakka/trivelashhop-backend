# KitDrop Backend — FastAPI

Production-ready REST API for the KitDrop jersey catalogue.

## Stack

- **FastAPI** — async Python web framework
- **Supabase** (Postgres) — database with RLS policies
- **Redis** — optional response caching (graceful fallback if not configured)
- **Sentry** — optional error tracking
- **JWT** — stateless admin authentication via `python-jose`
- **slowapi** — IP-based rate limiting

---

## Local Development

```bash
cd backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# → fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, SECRET_KEY

# 3. Set admin password
python scripts/hash_password.py
# → paste the output hash into .env as ADMIN_PASSWORD_HASH

# 4. Run database schema
#    → Go to Supabase → SQL Editor → paste supabase/schema.sql

# 5. (Optional) Seed products
python scripts/seed_db.py

# 6. Start server
uvicorn app.main:app --reload
# → API: http://localhost:8000
# → Docs: http://localhost:8000/docs
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # App factory — CORS, middleware, routes, lifecycle
│   ├── api/v1/
│   │   ├── __init__.py          # Router aggregator
│   │   └── routers/
│   │       ├── auth.py          # POST /auth/login
│   │       ├── products.py      # CRUD products (public read, admin write)
│   │       └── orders.py        # Orders + coupon + shipping endpoints
│   ├── core/
│   │   ├── config.py            # Pydantic Settings — all env vars validated here
│   │   ├── security.py          # bcrypt + JWT helpers
│   │   ├── exceptions.py        # Domain exceptions + FastAPI error handlers
│   │   ├── dependencies.py      # require_admin dep, get_db dep
│   │   └── logging.py           # structlog — JSON in prod, pretty in dev
│   ├── db/
│   │   ├── client.py            # Supabase client singleton
│   │   └── cache.py             # Redis cache with no-op fallback
│   ├── schemas/
│   │   ├── products.py          # ProductCreate, ProductUpdate, ProductOut, …
│   │   ├── orders.py            # OrderCreateIn, OrderOut, CouponOut, …
│   │   └── auth.py              # LoginIn, TokenOut
│   ├── services/
│   │   ├── products.py          # All product business logic + caching
│   │   ├── orders.py            # Order creation: stock check → coupon → ship → persist
│   │   ├── coupons.py           # Coupon validation (DB first, builtin fallback)
│   │   └── shipping.py          # Pincode zone → cost estimate
│   └── middleware/
│       └── logging.py           # Request/response structured logging
├── tests/
│   ├── conftest.py              # Fixtures: mock DB, test client, admin token
│   ├── unit/
│   │   ├── test_products_service.py
│   │   └── test_shipping_and_coupons.py
│   └── integration/
│       └── test_products_api.py
├── scripts/
│   ├── hash_password.py         # Generate bcrypt hash for ADMIN_PASSWORD_HASH
│   └── seed_db.py               # Seed 6 default products into Supabase
├── .env.example
├── requirements.txt
├── pyproject.toml               # pytest config
├── Procfile                     # For Render
└── railway.toml                 # For Railway
```

---

## API Reference

All endpoints are under `/api/v1/`.

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Returns a JWT for admin endpoints |

### Products (Public)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/products` | List with filters, search, pagination, sort |
| GET | `/products/{id}` | Single product |

**Query params for GET /products:**
- `category` — Club \| National \| Retro
- `in_stock` — true \| false
- `tag` — bestseller \| new \| retro \| soldout
- `search` — fuzzy name search
- `sort_by` — id \| price \| name \| created_at
- `sort_order` — asc \| desc
- `page`, `page_size` — pagination

### Products (Admin — Bearer JWT required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/products` | Create product |
| PATCH | `/products/{id}` | Update product (partial) |
| DELETE | `/products/{id}` | Delete product |
| PATCH | `/products/{id}/stock` | Adjust stock for a size (`delta` = +/- qty) |

### Orders (Public)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/orders` | Create order (validates stock, decrements, returns WhatsApp URL) |
| POST | `/orders/coupon/validate` | Validate a coupon code |
| POST | `/orders/shipping/estimate` | Estimate shipping cost for a pincode |

### Orders (Admin — Bearer JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/orders` | List all orders (paginated, filter by status) |
| GET | `/orders/{id}` | Get single order |
| PATCH | `/orders/{id}/status` | Update order status + notes |

---

## Order Creation Flow

`POST /orders` does the following atomically:

1. **Validate products** — each item must exist, be in stock, have enough qty for the requested size, and the version must be available
2. **Calculate subtotal** from live prices (not from frontend)
3. **Validate coupon** (if provided) — checks DB first, falls back to builtins; checks expiry, usage limits, and min order
4. **Estimate shipping** from pincode zone
5. **Decrement stock** — with full rollback if any item fails
6. **Persist order** to Supabase
7. **Return WhatsApp URL** pre-filled with the full order summary

---

## Running Tests

```bash
cd backend

# Unit + integration tests
pytest -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

Tests use `unittest.mock` to mock Supabase — no real DB needed.

---

## Deploy to Railway

1. Push code to GitHub
2. New Railway project → "Deploy from GitHub repo"
3. Set root directory to `/backend`
4. Add all env vars from `.env.example`
5. Railway auto-detects Python and uses `railway.toml`

## Deploy to Render

1. New Web Service → connect GitHub repo
2. Root directory: `backend`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars

---

## Production Checklist

- [ ] `ENVIRONMENT=production` (disables `/docs`, `/redoc`, `/openapi.json`)
- [ ] Strong `SECRET_KEY` (32+ random chars)
- [ ] `ADMIN_PASSWORD_HASH` set via `scripts/hash_password.py`
- [ ] `ALLOWED_ORIGINS` set to your actual frontend URL
- [ ] `SENTRY_DSN` configured for error tracking
- [ ] Redis provisioned for caching (optional but recommended)
- [ ] Supabase RLS policies reviewed
- [ ] Rate limits tuned for expected traffic
