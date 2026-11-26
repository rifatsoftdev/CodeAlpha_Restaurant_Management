import os

os.environ["DATABASE_URL"] = "sqlite:////tmp/test_restaurant.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.models import User
from app.security import hash_password


@pytest.fixture()
def client():
    from app.core.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        with SessionLocal() as db:
            db.add(User(username="admin", password_hash=hash_password("admin-password"), role="admin"))
            db.commit()
        login = c.post("/auth/login", json={"username": "admin", "password": "admin-password"})
        assert login.status_code == 200
        c.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
        yield c
    Base.metadata.drop_all(bind=engine)


def test_order_flow_updates_inventory(client):
    inv = client.post("/inventory", json={"name": "Cheese", "unit": "kg", "quantity": 1, "reorder_level": 0.5}).json()
    item = client.post("/menu", json={"name": "Pizza", "price": 10}).json()
    client.put(f"/menu/{item['id']}/recipe", json=[{"inventory_item_id": inv["id"], "quantity_required": 0.3}])

    r = client.post("/orders", json={"items": [{"menu_item_id": item["id"], "quantity": 2}]})
    assert r.status_code == 201 and r.json()["total_amount"] == 20

    stock = client.get("/inventory").json()[0]["quantity"]
    assert stock == pytest.approx(0.4)
    assert len(client.get("/inventory/low-stock").json()) == 1

    # not enough stock left for 2 more
    assert client.post("/orders", json={"items": [{"menu_item_id": item["id"], "quantity": 2}]}).status_code == 409

    # cancelling gives the stock back
    client.patch(f"/orders/{r.json()['id']}/status", json={"status": "cancelled"})
    assert client.get("/inventory").json()[0]["quantity"] == pytest.approx(1.0)


def test_reservation_overlap_and_admin_protection(client):
    client.post("/auth/staff", json={"username": "floor-staff", "password": "staff-password"})
    staff_login = client.post("/auth/login", json={"username": "floor-staff", "password": "staff-password"}).json()
    assert client.post("/tables", json={"number": 1, "capacity": 4}, headers={"Authorization": f"Bearer {staff_login['access_token']}"}).status_code == 403
    client.post("/tables", json={"number": 1, "capacity": 4})

    body = {"customer_name": "Ann", "party_size": 2, "start_time": "2026-12-01T19:00:00"}
    assert client.post("/reservations", json=body).status_code == 201
    assert client.post("/reservations", json=body).status_code == 409  # only one table

    free = client.get("/tables/available", params={"start_time": "2026-12-01T22:00:00", "party_size": 2})
    assert len(free.json()) == 1
