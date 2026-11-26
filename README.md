# Restaurant Management System (FastAPI)

Backend for orders, tables, reservations, menu and inventory. Python 3.10+, FastAPI, SQLAlchemy 2.0, SQLite.

## Run it
```bash
python3.10 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed              # optional sample data
python -m app.create_admin     # create the first administrator interactively
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 for the responsive restaurant operations dashboard, or http://127.0.0.1:8000/docs for the interactive API docs. The dashboard supports order placement and status updates, reservation management, stock restocking and alerts, menu search, and admin daily sales.
Sign in using the administrator credentials created by `python -m app.create_admin` (or `python app/create_admin.py`). Admins can manage menu availability and recipes, add ingredients and tables, create staff accounts, and view sales. Staff can manage orders, reservations, and stock. Dashboard prices are displayed in BDT. Set a private `AUTH_SECRET` environment variable before deployment; the built-in value is for local development only. Login tokens expire after eight hours.

## Run with Docker

Requirements: Docker Engine and the Docker Compose plugin.

```bash
cp .env.example .env
```

Edit `.env` and replace `AUTH_SECRET` with a private random value. Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then build and start the app:

```bash
docker compose up --build -d
docker compose ps
```

The dashboard is at http://localhost:3000 and the API docs are at http://localhost:3000/docs. Compose stores the SQLite database in the named `restaurant_data` volume, so it remains available after the container is restarted or rebuilt.

Create the initial admin account and optionally load sample menu, tables, and inventory:

```bash
docker compose exec -it app python -m app.create_admin
docker compose exec app python -m app.seed
```

The seed command skips loading data once a menu item already exists. For logs use `docker compose logs -f app`; stop the app with `docker compose down`. To use a different host port, set `PORT` in `.env`. `docker compose down -v` also deletes the database volume and all stored restaurant data.

Run tests locally with `pytest`.

## Structure
```
app/
  main.py            app + router registration, creates tables on startup
  core/database.py   engine, session, get_db dependency
  models/models.py   User, MenuItem, InventoryItem, RecipeIngredient, Table, Reservation, Order, OrderItem
  schema/schemas.py  Pydantic request/response models
  security.py        password hashing, signed login tokens, role checks
  create_admin.py    interactive initial-admin setup
  seed.py            sample data
  routers/           auth, menu, orders, tables, reservations, inventory, reports
  services/          business logic
    order_service.py      place order, status transitions, cancel -> restore stock
    inventory_service.py  check/deduct/restore stock, low-stock query
    table_service.py      availability (overlap check), create reservation, auto-assign table
tests/test_flow.py   smoke tests
```

## Endpoints
| Area | Endpoint | Access |
|---|---|---|
| Authentication | `POST /auth/login` | public |
| | `GET /auth/me` | signed-in user |
| | `POST /auth/change-password` | signed-in user |
| | `GET/POST /auth/staff` | admin |
| Menu | `GET /menu`, `GET /menu/{id}` | public |
| | `POST /menu`, `PATCH /menu/{id}`, `DELETE /menu/{id}`, `PUT /menu/{id}/recipe` | admin |
| Orders | `POST /orders`, `GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}/status` | staff/admin |
| Tables | `GET /tables`, `GET /tables/available?start_time=&party_size=&duration_minutes=` | staff/admin |
| | `POST /tables`, `PATCH /tables/{id}` (activate/deactivate) | admin |
| Reservations | `POST /reservations`, `GET /reservations`, `GET /reservations/{id}`, `DELETE /reservations/{id}` (cancels) | staff/admin |
| Inventory | `GET /inventory`, `GET /inventory/low-stock`, `PATCH /inventory/{id}/restock` | staff/admin |
| | `POST /inventory`, `PATCH /inventory/{id}` (edit item/count) | admin |
| Reports | `GET /reports/daily-sales?day=YYYY-MM-DD`, `GET /reports/stock-alerts` | admin |

Menu edits use `PATCH /menu/{id}` with only the changed fields, for example `{"name":"House noodles","price":380,"category":"main"}`. The response contains the updated menu item; a duplicate name returns `409`. Only admins can create or edit menu items.

Staff accounts created by an admin must change their temporary password at first sign-in. The API blocks staff operations until `POST /auth/change-password` succeeds with a body such as `{"current_password":"temporary-pass","new_password":"my-private-pass"}`; the new password must be at least eight characters.

Admins can mark damaged tables out of service from **Inventory → Dining tables**. Inactive tables are removed from order and reservation choices. A table with a confirmed reservation cannot be deactivated until the reservation is cancelled or moved.

## How the core logic works
- **Order processing:** validates table + items -> sums ingredients from each item's recipe -> rejects with 409 if stock is short -> deducts stock and saves the order in one transaction. Cancelling a `pending`/`preparing` order restores the stock.
- **Order lifecycle:** `pending -> preparing -> served -> paid` (or `cancelled`).
- **Table availability:** a table is free if no confirmed reservation overlaps the requested `[start, end)` window. Omit `table_id` when reserving to auto-pick the smallest table that fits.
- **Inventory auto-update:** driven by `RecipeIngredient` (inventory consumed per portion). Menu items with no recipe don't touch stock.

## Ideas for what to build next
- Password reset and staff account deactivation
- Alembic migrations, PostgreSQL + `Numeric` prices
- Link orders to reservations, table "occupied" status, payments/receipts
- Weekly/monthly reports, email alerts for low stock
