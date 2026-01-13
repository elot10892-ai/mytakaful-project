"""
Formulaires Flask-WTF pour MyTakaful.
- Fournit des validations côté serveur pour les vues principales
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange


class LoginForm(FlaskForm):
    identifier = StringField("Nom ou Email", validators=[DataRequired(), Length(min=2, max=120)])
    password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Se connecter")


class RegisterForm(FlaskForm):
    name = StringField("Nom", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Créer un compte")


class CreateGroupForm(FlaskForm):
    name = StringField("Nom du groupe", validators=[DataRequired(), Length(min=2, max=120)])
    description = TextAreaField("Description")
    submit = SubmitField("Créer")


class AidRequestForm(FlaskForm):
    amount = IntegerField("Montant de l'aide", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Demander")


class ProfileForm(FlaskForm):
    email = StringField("Email", validators=[Email()])
    password = PasswordField("Nouveau mot de passe", validators=[Length(min=6)])
    submit = SubmitField("Mettre à jour")


class AdminUserActionForm(FlaskForm):
    is_blocked = BooleanField("Bloquer l'utilisateur")
    make_admin = BooleanField("Promouvoir en admin")
    make_user = BooleanField("Rétrograder en utilisateur")
    submit = SubmitField("Appliquer")

