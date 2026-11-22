from .. import db
from ..models import PriceHistory, SaleCycle, utcnow


def record_price(product, price):
    """Append a manual observation only when the price changes."""
    if price == product.current_price and product.prices:
        return
    product.current_price = price
    if price is None:
        return
    db.session.add(PriceHistory(product=product, price=price))
    active = next((cycle for cycle in product.sale_cycles if cycle.ended_at is None), None)
    if product.original_price is None:
        return
    if price < product.original_price:
        if active:
            active.lowest_price = min(active.lowest_price, price)
        else:
            db.session.add(SaleCycle(product=product, lowest_price=price))
    elif active:
        active.ended_at = utcnow()
