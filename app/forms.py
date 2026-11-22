from decimal import Decimal
from urllib.parse import urlparse

from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


def money(minimum):
    def validate(form, field):
        value = field.data
        if value is None or not value.is_finite() or value < minimum or value > Decimal("9999999999.99") or value.as_tuple().exponent < -2:
            raise ValidationError("Enter a valid amount with at most two decimal places.")
    return validate


class LoginForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired(), Length(max=1024)])
    submit = SubmitField("Sign in")


class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired(), Length(max=255)])
    sku = StringField("SKU", validators=[Optional(), Length(max=100)])
    internet_number = StringField("Internet number", validators=[Optional(), Length(max=100)])
    model_number = StringField("Model number", validators=[Optional(), Length(max=100)])
    url = StringField("Home Depot product URL", validators=[Optional(), Length(max=2048)])
    image_url = StringField("Image URL", validators=[Optional(), Length(max=2048)])
    original_price = DecimalField("Original price ($)", places=2, validators=[Optional(), money(Decimal("0.01"))])
    current_price = DecimalField("Current price ($)", places=2, validators=[Optional(), money(Decimal("0"))])
    paused = BooleanField("Pause tracking")
    submit = SubmitField("Save product")

    def validate_url(self, field):
        if field.data:
            try:
                url = urlparse(field.data)
                valid = url.scheme == "https" and url.hostname in ("homedepot.com", "www.homedepot.com") and not url.username and not url.password and url.port in (None, 443)
            except ValueError:
                valid = False
            if not valid:
                raise ValidationError("Enter an HTTPS Home Depot product URL.")

    def validate_image_url(self, field):
        if field.data:
            try:
                url = urlparse(field.data)
                valid = url.scheme == "https" and bool(url.hostname) and not url.username and not url.password and (url.port is None or url.port == 443)
            except ValueError:
                valid = False
            if not valid:
                raise ValidationError("Enter a valid HTTPS image URL.")

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators)
        if not any((self.sku.data, self.internet_number.data, self.model_number.data, self.url.data)):
            self.sku.errors.append("Enter at least one product identifier or URL.")
            valid = False
        return valid


class ActionForm(FlaskForm):
    pass
