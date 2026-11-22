from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.orm import selectinload
from werkzeug.security import check_password_hash

from . import db
from .forms import ActionForm, LoginForm, ProductForm
from .models import Product
from .services.pricing import record_price

bp = Blueprint("main", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if check_password_hash(current_app.config["PASSWORD_HASH"], form.password.data):
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("main.dashboard"))
        flash("Invalid password.", "danger")
    return render_template("login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    form = ActionForm()
    if form.validate_on_submit():
        session.clear()
    return redirect(url_for("main.login"))


@bp.get("/")
@login_required
def dashboard():
    products = db.session.execute(db.select(Product).options(selectinload(Product.prices))).scalars().all()
    query = request.args.get("q", "").strip().casefold()
    if query:
        products = [p for p in products if query in p.name.casefold() or query in (p.sku or "").casefold()]
    selected_filter = request.args.get("filter", "")
    if selected_filter == "discounted":
        products = [p for p in products if p.current_discount is not None and p.current_discount > 0]
    elif selected_filter == "previously_discounted":
        products = [p for p in products if p.maximum_discount is not None and p.maximum_discount > 0]
    elif selected_filter == "returned":
        products = [p for p in products if p.maximum_discount is not None and p.maximum_discount > 0 and p.current_discount == 0]
    sort = request.args.get("sort", "name")
    sort_keys = {
        "discount": (lambda p: p.current_discount, True),
        "maximum": (lambda p: p.maximum_discount, True),
        "savings": (lambda p: p.savings, True),
        "price_low": (lambda p: p.current_price, False),
        "price_high": (lambda p: p.current_price, True),
        "lowest": (lambda p: p.lowest_price, False),
    }
    if sort in sort_keys:
        key, reverse = sort_keys[sort]
        known = [p for p in products if key(p) is not None]
        unknown = [p for p in products if key(p) is None]
        products = sorted(known, key=key, reverse=reverse) + unknown
    else:
        products.sort(key=lambda p: p.name.casefold())
    return render_template("dashboard.html", products=products, action_form=ActionForm(), query=query, selected_filter=selected_filter, sort=sort)


@bp.route("/products/new", methods=["GET", "POST"])
@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id=None):
    product = db.get_or_404(Product, product_id) if product_id else Product()
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        for field in ("name", "sku", "internet_number", "model_number", "url", "image_url"):
            setattr(product, field, (getattr(form, field).data or "").strip() or None)
        product.original_price = form.original_price.data
        product.paused = form.paused.data
        db.session.add(product)
        record_price(product, form.current_price.data)
        db.session.commit()
        flash("Product saved. Prices are manually entered in Stage 1.", "success")
        return redirect(url_for("main.product_detail", product_id=product.id))
    return render_template("product_form.html", form=form, product=product)


@bp.get("/products/<int:product_id>")
@login_required
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    return render_template("product_detail.html", product=product, action_form=ActionForm())


@bp.post("/products/<int:product_id>/delete")
@login_required
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    if ActionForm().validate_on_submit():
        db.session.delete(product)
        db.session.commit()
        flash("Product and its history deleted.", "success")
    return redirect(url_for("main.dashboard"))


@bp.post("/products/<int:product_id>/pause")
@login_required
def pause_product(product_id):
    product = db.get_or_404(Product, product_id)
    if ActionForm().validate_on_submit():
        product.paused = not product.paused
        db.session.commit()
    return redirect(url_for("main.dashboard"))
