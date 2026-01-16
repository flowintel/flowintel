from flask import url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
    EmailField
)
from wtforms.validators import Email, InputRequired, Length, Optional, EqualTo, Regexp

from ..db_class.db import User


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[InputRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


class EditUserFrom(FlaskForm):
    first_name = StringField('First name', validators=[InputRequired(), Length(1, 64)])
    last_name = StringField('Last name', validators=[InputRequired(), Length(1, 64)])
    nickname = StringField('Nickname', validators=[Optional(),Length(1, 64)])
    matrix_id = StringField('Matrix id', render_kw={"placeholder": "@testuser:matrix.org"})
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    change_password = BooleanField('Change password')
    password = PasswordField('Password', validators=[Optional()])
    password2 = PasswordField('Confirm password', validators=[Optional()])

    submit = SubmitField('Save')

    def validate_email(self, field):
        if field.data != current_user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered. (Did you mean to '
                                '<a href="{}">log in</a> instead?)'.format(
                                    url_for('account.index')))
    
    def validate_password(self, field):
        """Validate password only if change_password is checked"""
        if self.change_password.data:
            if not field.data:
                raise ValidationError('Password is required when changing password.')
            if len(field.data) < 8 or len(field.data) > 64:
                raise ValidationError('Password must be between 8 and 64 characters.')
            if not any(c.isupper() for c in field.data):
                raise ValidationError('Password must contain at least one uppercase letter.')
            if not any(c.islower() for c in field.data):
                raise ValidationError('Password must contain at least one lowercase letter.')
            if not any(c.isdigit() for c in field.data):
                raise ValidationError('Password must contain at least one digit.')
    
    def validate_password2(self, field):
        """Validate password confirmation only if change_password is checked"""
        if self.change_password.data:
            if not field.data:
                raise ValidationError('Password confirmation is required.')
            if field.data != self.password.data:
                raise ValidationError('Passwords must match.')


class RequestPasswordResetForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    submit = SubmitField('Request password reset')
