# Z9Pay VTU Backend API

A production-ready Virtual Top-Up (VTU) and digital payments backend service built with **Django** and **Django REST Framework (DRF)**. It provides a secure financial wallet architecture with automated Dedicated Virtual Accounts (DVA) via **Paystack**, phone-number-based JWT authentication, concurrency-safe transactions, and a flexible telecom data catalog with circuit breakers.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Architecture](#project-architecture)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
  - [Environment Variables](#environment-variables)
  - [Database Migrations & Superuser](#database-migrations--superuser)
  - [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
  - [Authentication](#authentication-endpoints)
  - [Wallet & Funding](#wallet-endpoints)
  - [Catalog & Plans](#catalog-endpoints)
- [Architecture & Financial Safety](#architecture--financial-safety)
  - [Row-Level Locking & Idempotency](#row-level-locking--idempotency)
  - [Paystack Webhook Verification](#paystack-webhook-verification)
  - [Catalog Circuit Breakers](#catalog-circuit-breakers)
- [License](#license)

---

## Overview

The **Z9Pay VTU Backend** powers digital service purchases (airtime, data bundles, and bill payments). The system is designed with financial integrity at its core:
- **No Double-Spending**: Utilizes database row-level locking (`select_for_update`) and atomic transactions.
- **Automated Funding**: Automatically generates Paystack Dedicated Virtual Accounts (DVA) so users receive dedicated bank account numbers upon signup.
- **Audit-Ready Ledger**: Every single credit or debit is written to an immutable `WalletLedger` with `balance_before` and `balance_after` snapshots.
- **Resilient Catalog**: Administrative circuit breakers allow disabling individual networks or plans instantly if upstream telco APIs experience downtime.

---

## Key Features

- **Custom Authentication**:
  - Phone-number-based primary identifier (standard for VTU platforms in Nigeria/Africa).
  - Stateless authentication with JSON Web Tokens (`djangorestframework-simplejwt`).
- **Financial Wallet & Ledger**:
  - Real-time balance tracking with non-negative constraints.
  - Double-entry-style immutable ledger (`CREDIT` / `DEBIT`) tracking sources (DVA, Card, Data Purchase, Refunds, Admin adjustments).
  - Idempotency guarantees preventing duplicate webhook or transaction processing.
- **Paystack Integration**:
  - Automated customer creation and Dedicated Virtual Account (DVA) assignment via signals.
  - Cryptographic HMAC-SHA512 webhook signature verification.
  - Automated wallet crediting on successful bank transfer or card payment.
- **Telco & Data Catalog**:
  - Supports major telco networks (MTN, Airtel, Glo, 9mobile).
  - Categorized data plans (SME, Corporate Gifting, Direct Gifting, Awoof).
  - Cost vs. Selling price tracking with real-time profit margin calculation.
  - Parent-child circuit breaker: Deactivating a network automatically hides all associated data plans.
- **Admin Dashboard**:
  - Customized Django admin with inline price edits, network status toggles, and computed profit margins.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12+ (tested up to 3.14) |
| **Framework** | Django 6.1 |
| **API Framework** | Django REST Framework (DRF) |
| **Authentication** | SimpleJWT (JWT Bearer tokens) |
| **Database** | SQLite (Default/Development), PostgreSQL supported (`psycopg2-binary`) |
| **Asynchronous Tasks** | Celery & Redis (`celery`, `redis`) |
| **Payments / DVA** | Paystack API |
| **Configuration** | Python-Decouple (`.env`) |

---

## Directory Structure

```text
z9pay_vtu_backend/
├── catalog/                # Telco networks, data plans, pricing & circuit breakers
│   ├── admin.py            # Admin customization (inline price editing, profit display)
│   ├── models.py           # Network and DataPlan models
│   ├── serializers.py      # Catalog DRF serializers
│   ├── urls.py             # Catalog API routes
│   └── views.py            # Catalog list and filter views
├── config/                 # Project settings and root routing
│   ├── asgi.py
│   ├── settings.py         # Django settings, JWT configuration, Paystack config
│   ├── urls.py             # Root URL routing (/api/v1/...)
│   └── wsgi.py
├── transactions/           # Transaction processing & logging app
├── users/                  # Custom User model and authentication
│   ├── models.py           # Custom User model (phone_number as USERNAME_FIELD)
│   ├── serializers.py      # Registration serializer
│   ├── urls.py             # Auth endpoints (/register/, /login/, /refresh/)
│   └── views.py            # Registration view
├── wallet/                 # Wallet management, ledger & Paystack webhooks
│   ├── models.py           # Wallet and immutable WalletLedger models
│   ├── paystack.py         # Paystack API client & HMAC-SHA512 webhook verification
│   ├── serializers.py      # Wallet and Ledger serializers
│   ├── services.py         # Concurrency-safe credit/debit service (select_for_update)
│   ├── signals.py          # Auto-create wallet & assign DVA on user registration
│   ├── urls.py             # Wallet endpoints
│   └── views.py            # Wallet detail, ledger history, webhook handler
├── z9pay_integration/      # Upstream Z9Pay VTU API integration
├── manage.py
├── requirments.txt         # Project dependencies
├── .env.example            # Sample environment variables
└── README.md
```

---

## Getting Started

### Prerequisites

Ensure you have the following installed on your machine:
- **Python 3.12+** (check via `python --version`)
- **Git**
- Optional: **Redis** (if running background tasks with Celery)

---

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/z9pay_vtu_backend.git
   cd z9pay_vtu_backend
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirments.txt
   ```

---

### Environment Variables

Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

Configure your environment settings:

```ini
# Django Settings
SECRET_KEY=your-secure-django-secret-key
DEBUG=True

# Paystack API Settings
PAYSTACK_SECRET_KEY=sk_test_your_paystack_secret_key
PAYSTACK_PREFERRED_BANK=wema-bank
```

| Variable | Description |
|---|---|
| `SECRET_KEY` | Secret key used by Django for cryptographic signing. |
| `DEBUG` | Set to `True` for development, `False` for production. |
| `PAYSTACK_SECRET_KEY` | Secret key from your Paystack Dashboard (Test or Live). |
| `PAYSTACK_PREFERRED_BANK` | Preferred partner bank for DVAs (e.g., `wema-bank`, `titan-bank`, `test-bank`). |

---

### Database Migrations & Superuser

1. Run database migrations:
   ```bash
   python manage.py migrate
   ```

2. Create an administrative user:
   ```bash
   python manage.py createsuperuser
   ```
   *(Note: The custom user model requires `Phone number`, `Email`, `First name`, `Last name`, and `Password`)*.

---

### Running the Server

Start the local development server:

```bash
python manage.py runserver
```

The server will be available at: **`http://127.0.0.1:8000/`**  
The Django Admin panel is located at: **`http://127.0.0.1:8000/admin/`**

---

## API Documentation

All API endpoints are versioned under `/api/v1/`.

### Authentication Endpoints

Base path: `/api/v1/auth/`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | Register a new user and trigger DVA creation | No |
| `POST` | `/api/v1/auth/login/` | Obtain JWT access and refresh token pair | No |
| `POST` | `/api/v1/auth/token/refresh/` | Refresh expired access token | No |

#### Registration Request Example (`POST /api/v1/auth/register/`):
```json
{
  "phone_number": "08012345678",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "StrongPassword123"
}
```

#### Login Request Example (`POST /api/v1/auth/login/`):
```json
{
  "phone_number": "08012345678",
  "password": "StrongPassword123"
}
```

---

### Wallet Endpoints

Base path: `/api/v1/wallet/`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/wallet/` | Retrieve user balance and virtual bank account details | Bearer JWT |
| `GET` | `/api/v1/wallet/ledger/` | Retrieve complete credit/debit transaction statement | Bearer JWT |
| `POST` | `/api/v1/wallet/webhook/` | Paystack Webhook receiver for payments & DVA assignment | HMAC Signature |

#### Sample Wallet Response (`GET /api/v1/wallet/`):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "balance": "5400.00",
  "bank_name": "Wema Bank",
  "account_number": "9901234567",
  "account_name": "PAYSTACK / JOHN DOE",
  "is_locked": false,
  "created_at": "2026-11-09T10:30:00Z"
}
```

---

### Catalog Endpoints

Base path: `/api/v1/catalog/`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/catalog/networks/` | List all active telecom networks | No |
| `GET` | `/api/v1/catalog/plans/` | List all active data plans (filterable) | No |

#### Query Parameters for Plans:
- `network`: Filter by network code (e.g., `?network=MTN`)
- `category`: Filter by category (e.g., `?category=SME`, `?category=CORPORATE`)

Example:
```http
GET /api/v1/catalog/plans/?network=MTN&category=SME
```

---

## Architecture & Financial Safety

### Row-Level Locking & Idempotency

All wallet mutations are handled via `WalletService`:

```python
# Atomic transaction block with row-level lock
with transaction.atomic():
    wallet = Wallet.objects.select_for_update().get(user_id=user_id)
    # Check balance, compute new balance, and write to WalletLedger
```

- **`select_for_update()`**: Prevents race conditions and double-spending by acquiring an exclusive row lock in the database until the transaction completes.
- **Unique References**: Every ledger entry requires a unique `reference`. If a duplicate reference is submitted (e.g., retried webhooks), the service returns the existing record idempotently without re-crediting.

### Paystack Webhook Verification

The Paystack webhook endpoint (`/api/v1/wallet/webhook/`) is public to allow Paystack dispatch, but secured cryptographically:
1. Paystack sends the HMAC signature in the `x-paystack-signature` header.
2. The server computes `hmac.new(PAYSTACK_SECRET_KEY, raw_request_body, sha512)`.
3. If signatures do not match via `hmac.compare_digest`, the request is rejected with HTTP 400.
4. Handled events:
   - `dedicatedaccount.assign.success`: Updates user's wallet with bank name, account number, and account name.
   - `charge.success`: Converts kobo to Naira and safely credits the user's wallet with ledger entry tagged `PSK-<reference>`.

### Catalog Circuit Breakers

Telecom networks occasionally face downtime. To maintain an optimal user experience:
- If a network is disabled via Admin (`Network.is_active = False`), the `/catalog/plans/` API automatically hides all plans under that network using `network__is_active=True` query filtering.
- Individual plans can also be disabled (`DataPlan.is_active = False`) independently.

---

## Testing

To run the automated test suite:

```bash
python manage.py test
```

---

## License

This project is licensed under the [MIT License](LICENSE).

