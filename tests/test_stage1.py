from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Product
from app.services.pricing import record_price


@pytest.fixture
def application():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-key",
        "PASSWORD_HASH": generate_password_hash("test-password"),
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(application):
    client = application.test_client()
    client.post("/login", data={"password": "test-password"})
    return client


def test_price_history_and_sale_cycles(application):
    product = Product(name="Tool", sku="123", original_price=Decimal("100"))
    db.session.add(product)
    for price in ("100", "30", "100", "80"):
        record_price(product, Decimal(price))
        db.session.flush()
    assert product.current_discount == 20
    assert product.maximum_discount == 70
    assert product.savings == 20
    assert product.lowest_price == 30
    assert len(product.prices) == 4
    assert len(product.sale_cycles) == 2
    assert product.sale_cycles[0].ended_at is not None
    assert product.sale_cycles[0].lowest_price == 30
    assert product.sale_cycles[1].ended_at is None
    record_price(product, Decimal("80"))
    db.session.flush()
    assert len(product.prices) == 4


def test_unknown_values_and_original_correction(application):
    product = Product(name="Tool", sku="123")
    db.session.add(product)
    assert product.current_discount is None
    assert product.maximum_discount is None
    record_price(product, Decimal("25"))
    db.session.flush()
    product.original_price = Decimal("100")
    assert product.maximum_discount == 75
    product.original_price = Decimal("50")
    assert product.maximum_discount == 50
    record_price(product, None)
    assert product.current_discount is None
    assert product.maximum_discount == 50


def test_authentication_and_product_management(application, client):
    anonymous = application.test_client()
    assert anonymous.get("/").status_code == 302
    assert b"Invalid password" in anonymous.post("/login", data={"password": "wrong"}).data
    response = client.post("/products/new", data={"name": "Drill", "sku": "42", "original_price": "100", "current_price": "30"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"70.0%" in response.data
    product = db.session.execute(db.select(Product)).scalar_one()
    client.post(f"/products/{product.id}/edit", data={"name": "Drill", "sku": "42", "original_price": "100", "current_price": "100"})
    assert b"70.0%" in client.get("/?filter=returned&sort=maximum").data
    assert b"Drill" not in client.get("/?filter=discounted").data
    client.post(f"/products/{product.id}/pause")
    assert db.session.get(Product, product.id).paused
    client.post(f"/products/{product.id}/delete")
    assert db.session.get(Product, product.id) is None


@pytest.mark.parametrize("data", [
    {"name": "Tool", "sku": "1", "current_price": "NaN"},
    {"name": "Tool", "sku": "1", "current_price": "abc"},
    {"name": "Tool", "sku": "1", "current_price": "1.234"},
    {"name": "Tool", "url": "https://www.homedepot.com:bad/item"},
    {"name": "Tool", "url": "https://homedepot.com.attacker.invalid/item"},
    {"name": "Tool"},
])
def test_invalid_input_is_rejected(client, data):
    response = client.post("/products/new", data=data)
    assert response.status_code == 200
    assert db.session.execute(db.select(Product)).scalars().all() == []


def test_csrf_protects_mutations(application):
    application.config["WTF_CSRF_ENABLED"] = True
    client = application.test_client()
    assert client.post("/login", data={"password": "test-password"}).status_code == 400
