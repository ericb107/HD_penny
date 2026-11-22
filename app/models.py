from datetime import datetime, timezone
from decimal import Decimal

from . import db


def utcnow():
    return datetime.now(timezone.utc)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    sku = db.Column(db.String(100), index=True)
    internet_number = db.Column(db.String(100))
    model_number = db.Column(db.String(100))
    url = db.Column(db.String(2048))
    image_url = db.Column(db.String(2048))
    original_price = db.Column(db.Numeric(12, 2))
    current_price = db.Column(db.Numeric(12, 2))
    paused = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    prices = db.relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan", order_by="PriceHistory.recorded_at")
    tracking = db.relationship("ProductStoreTracking", back_populates="product", cascade="all, delete-orphan")
    sale_cycles = db.relationship("SaleCycle", back_populates="product", cascade="all, delete-orphan")
    alerts = db.relationship("AlertSettings", back_populates="product", cascade="all, delete-orphan", uselist=False)
    notifications = db.relationship("Notification", back_populates="product", cascade="all, delete-orphan")

    @property
    def lowest_price(self):
        return min((p.price for p in self.prices), default=None)

    @property
    def highest_price(self):
        return max((p.price for p in self.prices), default=None)

    def discount(self, price):
        if self.original_price is None or self.original_price <= 0 or price is None:
            return None
        return max(Decimal("0"), (self.original_price - price) / self.original_price * 100)

    @property
    def current_discount(self):
        return self.discount(self.current_price)

    @property
    def maximum_discount(self):
        return self.discount(self.lowest_price)

    @property
    def savings(self):
        if self.original_price is None or self.current_price is None:
            return None
        return max(Decimal("0"), self.original_price - self.current_price)


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120))
    zip_code = db.Column(db.String(20), index=True)


class ProductStoreTracking(db.Model):
    __table_args__ = (db.UniqueConstraint("product_id", "store_id"),)
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False, index=True)
    status = db.Column(db.String(40), nullable=False, default="unknown")
    quantity = db.Column(db.Integer)
    last_success_at = db.Column(db.DateTime(timezone=True))
    product = db.relationship("Product", back_populates="tracking")
    store = db.relationship("Store")
    history = db.relationship("InventoryHistory", back_populates="tracking", cascade="all, delete-orphan")


class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"))
    price = db.Column(db.Numeric(12, 2), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    product = db.relationship("Product", back_populates="prices")


class InventoryHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.Integer, db.ForeignKey("product_store_tracking.id"), nullable=False, index=True)
    status = db.Column(db.String(40), nullable=False)
    quantity = db.Column(db.Integer)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    tracking = db.relationship("ProductStoreTracking", back_populates="history")


class SaleCycle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    ended_at = db.Column(db.DateTime(timezone=True))
    lowest_price = db.Column(db.Numeric(12, 2), nullable=False)
    product = db.relationship("Product", back_populates="sale_cycles")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    event_key = db.Column(db.String(255), nullable=False, unique=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    sent_at = db.Column(db.DateTime(timezone=True))
    product = db.relationship("Product", back_populates="notifications")


class AlertSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, unique=True)
    discount_threshold = db.Column(db.Numeric(5, 2))
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    product = db.relationship("Product", back_populates="alerts")


class ApplicationSettings(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)
