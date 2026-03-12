# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role

You are a **SENIOR BACKEND ENGINEER** responsible for this codebase. You write production-grade, async Python with deep expertise in FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis, and real-time systems. You prioritize correctness, security, and performance. You own architectural decisions and enforce clean boundaries between layers.

## Project Overview

FastAPI backend for a delivery platform targeting Turkmenistan. Fully async with PostgreSQL (asyncpg), Redis for OTP rate limiting, registration tokens, and session caching, MinIO (S3-compatible) for image storage, and WebSocket for real-time notifications. The React Native mobile app lives at `../mobile/`.

## Commands

```bash
# Start infrastructure (postgres, redis, minio, backend with hot-reload)
cd .. && docker compose up -d

# Run backend locally (without Docker)
uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Lint
ruff check app/
ruff check --fix app/

# Tests
pytest
pytest tests/unit/
pytest tests/integration/
pytest -k "test_name"               # single test
pytest --cov=app --cov-report=term  # with coverage
```

## Architecture

### Layered Structure

```
api/          → Route handlers (thin controllers: validate → delegate → respond)
services/     → Business logic + side effects (AuthService, OtpService, NotificationService, ConnectionManager, StoreHoursService)
repositories/ → Data access layer (one per model aggregate, SQLAlchemy queries only)
models/       → SQLAlchemy ORM models (mapped_column style, UUID PKs, UTC timestamps)
schemas/      → Pydantic v2 request/response DTOs (strict validation, no ORM leakage)
core/         → Infrastructure: config, database engine, Redis client, S3 storage, JWT security
middleware/   → Auth dependencies (get_current_user, require_role)
```

**Hard rules:**
- Route handlers NEVER contain business logic or raw SQL — they call services/repositories
- Repositories NEVER import from `api/` or `services/`
- Services orchestrate repositories and external integrations
- Schemas are the only layer that touches HTTP request/response shapes
- Models define database structure only — no business methods

### Models

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `User` | id, email, phone, hashed_password, role, phone_verified | UserRole enum: CUSTOMER, MERCHANT, COURIER, ADMIN |
| `Store` | id, owner_id, name, status, merchant_type, is_open, logo_url, cover_url | MerchantType: RESTAURANT, STORE. StoreStatus: PENDING, APPROVED, REJECTED, SUSPENDED |
| `StoreImage` | id, store_id, image_url, thumbnail_url, sort_order | Gallery images for store |
| `MenuCategory` | id, store_id, name, sort_order | Categories group menu items |
| `MenuItem` | id, store_id, category_id, name, price, status, images | Restaurant fields: portion_size, is_spicy, allergens. Store fields: weight, unit, sku |
| `MenuItemImage` | id, menu_item_id, image_url, thumbnail_url, sort_order | Max 5 per item, min 3 to activate |
| `Order` | id, user_id, store_id, status, total, delivery_latitude/longitude, cancelled_reason | Price snapshotted at creation |
| `Notification` | id, user_id, type, title, body, data (JSON), is_read | NotificationType enum |
| `StoreRating` | id, user_id, store_id, stars | Upsert per user+store pair (1-5 stars) |
| `ProductReview` | id, user_id, menu_item_id, stars, text, image_url, merchant_reply, replied_at | Upsert per user+item. Merchant can reply once |
| `Conversation` | id, customer_id, store_id, last_message_at | One per customer+store pair, auto-created |
| `Message` | id, conversation_id, sender_id, text, is_read | Chat messages between customer and merchant |
| `Address` | id, user_id, label, address_line, is_default | Multiple per user with default tracking |
| `OtpCode` | id, phone, code, expires_at, used, attempts | Rate limiting tracking |
| `RefreshToken` | id, user_id, token_hash, expires_at, revoked | Token rotation and explicit logout |

### Repositories

| Repository | Aggregate | Key Operations |
|-----------|-----------|----------------|
| `UserRepository` | User | CRUD, find by email/phone |
| `StoreRepository` | Store, StoreImage | CRUD, gallery management, immutable merge pattern |
| `MenuRepository` | MenuCategory, MenuItem, MenuItemImage | Category/item CRUD, image management with constraints |
| `OrderRepository` | Order, OrderItem | Create with price snapshot, status updates, listing with filters |
| `AddressRepository` | Address | CRUD, set default (clears other defaults) |
| `NotificationRepository` | Notification | Create, list (with unread filter), mark read (single/all/by store) |
| `RatingRepository` | StoreRating, ProductReview | Upsert ratings/reviews, summaries, merchant reply |
| `MessageRepository` | Conversation, Message | Find/create conversations, send messages, list with unread counts, mark read |
| `OtpRepository` | OtpCode | Create, count recent sends for rate limiting |
| `TokenRepository` | RefreshToken | Create, find by hash, revoke |

### Auth Flow

Two auth paths converge on the same JWT token system:

1. **Email/password** — `POST /register` and `POST /login` directly issue tokens
2. **Phone/OTP** — Three-step flow:
   - `POST /otp/send` → sends OTP via UniMTX (or mock in dev)
   - `POST /otp/verify` → if user exists, returns tokens; if new, returns a `registration_token` (stored in Redis, 10min TTL)
   - `POST /register/complete` → consumes registration_token, creates user + optional store (for merchants), returns tokens

OTP provider is swappable: `SMS_PROVIDER=mock` accepts any 6-digit code, `SMS_PROVIDER=unimtx` uses the real UniMTX API. Provider interface is `OtpProvider` ABC in `services/sms_provider.py`.

### Role System

`UserRole` enum: `CUSTOMER`, `MERCHANT`, `COURIER`, `ADMIN`. Enforced via `require_role(*roles)` dependency that chains on `get_current_user`.

- **Customer** — browses stores, places orders, manages addresses
- **Merchant** — owns a store, manages menu/orders (store auto-created at registration with `PENDING` status)
- **Courier** — accepts deliveries, has `vehicle_type` attribute
- **Admin** — full platform access: approve/reject/suspend stores, manage users, receives store registration notifications

### Store Lifecycle

```
PENDING → APPROVED → can toggle is_open, manage menu, receive orders
       → REJECTED → must contact support
APPROVED → SUSPENDED → admin can suspend active stores
```

Merchants cannot upload menu items or open their store until admin approves. Admin manages status via `PATCH /api/admin/stores/{id}/status`. Status changes trigger real-time notifications to the store owner.

### Order Status State Machine

```
PENDING → CONFIRMED → PREPARING → READY → PICKED_UP → DELIVERED
       ↘ CANCELLED  ↘ CANCELLED
```

Valid transitions enforced in `merchant_orders.py`. Orders snapshot menu item prices at creation — price changes don't affect existing orders.

### Store Hours

`StoreHoursService` in `services/store_hours.py` handles Turkmenistan timezone (UTC+5, no DST). Supports overnight hours (e.g., 22:00→06:00). Used during order creation to reject orders when store is closed.

### WebSocket & Real-Time Notifications

**Connection flow:**
1. Client connects to `GET /api/ws?token=<jwt>`
2. Server validates JWT, extracts user_id
3. Connection registered in `ConnectionManager` (in-memory dict: `user_id → list[WebSocket]`)
4. Server sends/receives JSON messages; supports `ping`/`pong` keepalive

**NotificationService** (`services/notification_service.py`):
- `notify(user_id, type, title, body, data)` — persists to DB, then broadcasts via WebSocket
- `notify_many(user_ids, ...)` — batch notify multiple users
- Gracefully handles dead connections (removes on send failure)

**Notification types** (`NotificationType` enum):
- `STORE_REGISTERED` — sent to all admins when a merchant registers a store
- `STORE_APPROVED` / `STORE_REJECTED` — sent to merchant when admin changes store status
- `ORDER_NEW` — sent to merchant when customer places order
- `ORDER_STATUS` — sent to customer when order status changes
- `ORDER_CANCELLED` — sent to merchant when customer cancels order
- `STORE_RATED` — sent to merchant when customer rates their store
- `PRODUCT_REVIEWED` — sent to merchant when customer reviews a product
- `NEW_MESSAGE` — sent to recipient when a chat message is sent
- `REVIEW_REPLY` — sent to customer when merchant replies to their review

### Ratings & Reviews

- **Store ratings**: Customers rate stores 1-5 stars (upsert per user+store). Summary endpoint returns average + count.
- **Product reviews**: Customers review products with stars + text + optional image. Upsert per user+item.
- **Merchant reply**: Merchants reply to reviews via `POST /api/ratings/reviews/{id}/reply`. Sends `REVIEW_REPLY` notification to the reviewer.
- Repository: `RatingRepository` in `repositories/rating_repository.py`
- Schemas: `schemas/rating.py` — includes `MerchantReplyRequest`

### Messaging

Real-time chat between customers and merchants:
- **Conversation**: Auto-created per customer+store pair via `POST /api/messages/conversations/store/{store_id}`
- **Messages**: Send via `POST /api/messages/conversations/{id}/messages`, list via GET
- **Mark read**: Messages auto-marked read when the other party fetches them
- **Notifications**: Each message sends a `NEW_MESSAGE` notification via WebSocket
- Authorization: customers access their own conversations, merchants access conversations for their store
- Repository: `MessageRepository` in `repositories/message_repository.py`

### Search

- **Public search**: `GET /api/public/search?q=` searches across approved stores (by name) and active products (by name, description, ingredients)
- **Menu search**: `search` param on `GET /api/stores/me/items` for merchant item filtering
- **Order search**: `search` param on `GET /api/stores/me/orders` for merchant order search by ID
- **Admin search**: `search` param on admin store/user listing endpoints
- Uses `ilike` for case-insensitive matching, `func.array_to_string` for PostgreSQL ARRAY columns

### Image Upload Pipeline

`core/storage.py` handles all image uploads:
- Validates mime type (JPEG/PNG/WebP) and size (5MB max)
- Resizes to 1200px max dimension + generates 300px thumbnail (quality=85 JPEG)
- Uploads both to MinIO under structured keys: `stores/{id}/logo/`, `stores/{id}/gallery/`, `menu-items/{id}/`
- Returns public URLs based on `S3_PUBLIC_URL` config
- Menu items: max 5 images, minimum 3 required to mark item as ACTIVE

### Database Patterns

- Async sessions via `get_db()` generator (auto-commit on success, rollback on exception)
- Repositories use `flush()` not `commit()` — the session middleware handles commit
- Store repository uses immutable `merge()` pattern for updates (creates new object with merged attrs)
- All models use UUID primary keys and UTC timestamps
- `models/__init__.py` imports all models so Alembic autogenerate picks them up
- Notification model stores `data` as JSON text (serialized dict with entity IDs and status values)

### API Route Prefixes

| Prefix | Auth | Purpose |
|--------|------|---------|
| `/api/auth/*` | None/Bearer | Registration, login, OTP, token refresh, logout |
| `/api/public/*` | None | Store browsing for customers |
| `/api/orders/*` | Customer | Customer order CRUD |
| `/api/stores/me/*` | Merchant | Store settings, logo/cover/gallery, menu categories & items, merchant orders |
| `/api/addresses/*` | Bearer | Customer address CRUD, set default |
| `/api/profile/*` | Bearer | Update email, phone OTP send/verify |
| `/api/admin/*` | Admin | Store approval/rejection/suspension, user management |
| `/api/notifications/*` | Bearer | List, mark read (single/all/by store), unread count |
| `/api/ratings/*` | Bearer/None | Store ratings, product reviews, merchant replies, review image upload |
| `/api/messages/*` | Bearer | Conversations (list, create), messages (list, send), mark read |
| `/api/public/search` | None | Cross-store search for stores and products |
| `/api/ws` | JWT via query param | WebSocket real-time connection |
| `/api/health` | None | Health check |

### Configuration

`pydantic-settings` loads from `.env` file. Key settings:
- `SMS_PROVIDER`: `mock` (dev) or `unimtx` (prod)
- `APP_DEBUG`: enables SQLAlchemy echo
- `DATABASE_URL` env var overrides `alembic.ini` in Docker
- `REDIS_URL`: Redis connection for OTP, tokens, rate limiting
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_PUBLIC_URL`: MinIO/S3 config

### Docker Setup

`docker-compose.yml` at project root runs PostgreSQL 16 (5432), Redis 7 (6379), MinIO (9000/9001 console), and backend (8000) with hot-reload via volume mount. Backend waits for postgres/redis health checks before starting.

## Engineering Standards

- **Immutability**: Always create new objects, never mutate in-place. Repository updates return new instances.
- **Error handling**: Use `HTTPException` with specific status codes. Never swallow errors silently. Log context server-side.
- **Input validation**: All request bodies validated via Pydantic schemas. Query params validated via FastAPI type annotations.
- **Security**: Parameterized queries only (SQLAlchemy handles this). No raw SQL. Secrets in env vars, never in code.
- **Async everywhere**: All DB operations, Redis calls, and HTTP requests must be async. Never block the event loop.
- **Type hints**: All function signatures must have complete type annotations. Use `Mapped[]` for model columns.
