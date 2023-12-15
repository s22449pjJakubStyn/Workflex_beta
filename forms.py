import re

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired, Length, Regexp, ValidationError
from password_strength import PasswordPolicy, PasswordStats


class RegistrationEmployeeForm(FlaskForm):
    name = StringField('Imię', validators=[InputRequired()])
    surname = StringField('Nazwisko', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired()])
    password = PasswordField('Hasło', validators=[InputRequired()])
    confirm_password = PasswordField('Powtórz hasło', validators=[InputRequired()])
    phone = StringField('Numer telefonu', validators=[InputRequired()])
    submit = SubmitField('Zarejestruj się ')

    def validate_name(form, field):
        if len(field.data) < 2:
            raise ValidationError('Imię musi mieć minimum 2 znaki.')

    def validate_surname(form, field):
        if len(field.data) < 2:
            raise ValidationError('Nazwisko musi mieć minimum 2 znaki.')

    def validate_email(self, email):
        email_format = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_format, email.data):
            raise ValidationError('Nieprawidłowy format adresu email.')

    def validate_password(form, field):
        password = field.data

        if len(password) < 8:
            raise ValidationError('Hasło musi mieć minimum 8 znaków.')

        if not any(char.islower() for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jedną małą literę.')

        if not any(char.isupper() for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jedną dużą literę.')

        if not any(char.isdigit() for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jedną cyfrę.')

        special_characters = "!@#$%^&*()_+[]{}?:;<>,."
        if not any(char in special_characters for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jeden znak specjalny.')

    def validate_confirm_password(self, confirm_password):
        if self.password.data != confirm_password.data:
            raise ValidationError('Hasła muszą być takie same.')


class RegistrationEmployerForm(FlaskForm):
    name = StringField('Nazwa firmy', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired()])
    password = PasswordField('Hasło', validators=[InputRequired()])
    confirm_password = PasswordField('Powtórz hasło', validators=[InputRequired()])
    phone = StringField('Numer telefonu', validators=[InputRequired()])
    submit = SubmitField('Zarejestruj się')

    def validate_name(form, field):
        if len(field.data) < 2:
            raise ValidationError('Nazwa musi mieć minimum 2 znaki.')

    def validate_email(self, email):
        email_format = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_format, email.data):
            raise ValidationError('Nieprawidłowy format adresu email.')

    def validate_password(form, field):
        password = field.data

        if len(password) < 8:
            raise ValidationError('Hasło musi mieć minimum 8 znaków.')

        if not any(char.islower() for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jedną małą literę.')

        if not any(char.isupper() for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jedną dużą literę.')

        if not any(char.isdigit() for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jedną cyfrę.')

        special_characters = "!@#$%^&*()_+[]{}?:;<>,."
        if not any(char in special_characters for char in password):
            raise ValidationError('Hasło musi zawierać co najmniej jeden znak specjalny.')

    def validate_confirm_password(self, confirm_password):
        if self.password.data != confirm_password.data:
            raise ValidationError('Hasła muszą być takie same.')
