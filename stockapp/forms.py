from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    FloatField,
    IntegerField,
    FileField,
    BooleanField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    sms_opt_in = BooleanField("SMS Alerts")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[DataRequired()])


class WatchlistAddForm(FlaskForm):
    symbol = StringField("Symbol", validators=[DataRequired(), Length(max=10)])
    threshold = FloatField("Threshold", validators=[Optional()])
    notes = StringField("Notes", validators=[Optional(), Length(max=200)])
    tags = StringField("Tags", validators=[Optional(), Length(max=100)])
    public = BooleanField("Public")


class WatchlistUpdateForm(FlaskForm):
    item_id = IntegerField("Item ID", validators=[DataRequired()])
    threshold = FloatField("Threshold", validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional(), Length(max=200)])
    tags = StringField("Tags", validators=[Optional(), Length(max=100)])
    public = BooleanField("Public")


class PortfolioAddForm(FlaskForm):
    symbol = StringField("Symbol", validators=[DataRequired(), Length(max=10)])
    quantity = FloatField("Quantity", validators=[DataRequired()])
    price_paid = FloatField("Price Paid", validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional(), Length(max=200)])
    tags = StringField("Tags", validators=[Optional(), Length(max=100)])


class PortfolioUpdateForm(FlaskForm):
    item_id = IntegerField("Item ID", validators=[DataRequired()])
    quantity = FloatField("Quantity", validators=[Optional()])
    price_paid = FloatField("Price Paid", validators=[Optional()])
    notes = StringField("Notes", validators=[Optional(), Length(max=200)])
    tags = StringField("Tags", validators=[Optional(), Length(max=100)])


class PortfolioImportForm(FlaskForm):
    file = FileField("File", validators=[DataRequired()])
