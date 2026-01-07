from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    EmailField,
    SelectField,
    TextAreaField,
    HiddenField,
    BooleanField
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, Optional, Regexp
from ..db_class.db import User, Org
from ..utils.utils import isUUID


class RegistrationForm(FlaskForm):
    first_name = StringField('First name', validators=[InputRequired(), Length(1, 64)])
    last_name = StringField('Last name', validators=[InputRequired(), Length(1, 64)])
    nickname = StringField('Nickname', validators=[Optional(), Length(1, 64)])
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[
            InputRequired(),
            EqualTo('password2', 'Passwords must match'),
            Length(min=8, max=64, message="Password must be between 8 and 64 characters."),
            Regexp(r'.*[A-Z].*', message="Password must contain at least one uppercase letter."),
            Regexp(r'.*[a-z].*', message="Password must contain at least one lowercase letter."),
            Regexp(r'.*\d.*', message="Password must contain at least one digit.")
        ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])
    matrix_id = StringField('Matrix id', render_kw={"placeholder": "@testuser:matrix.org"})

    role = SelectField(u'Role', coerce=str, validators=[InputRequired()])
    org = SelectField(u'Organisation', coerce=str, validators=[InputRequired()])

    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')


class AdminEditUserFrom(FlaskForm):
    user_id = HiddenField("")
    first_name = StringField('First name', validators=[InputRequired(), Length(1, 64)])
    last_name = StringField('Last name', validators=[InputRequired(), Length(1, 64)])
    nickname = StringField('Nickname', validators=[Optional(), Length(1, 64)])
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    change_password = BooleanField('Change password')
    password = PasswordField('Password', validators=[Optional()])
    password2 = PasswordField('Confirm password', validators=[Optional()])
    matrix_id = StringField('Matrix id', render_kw={"placeholder": "@testuser:matrix.org"})

    role = SelectField(u'Role', coerce=str, validators=[InputRequired()])
    org = SelectField(u'Organisation', coerce=str, validators=[InputRequired()])

    submit = SubmitField('Edit')

    def validate_email(self, field):
        user = User.query.get(self.user_id.data)
        if field.data != user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')
    
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


class CreateOrgForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    uuid = StringField('UUID', validators=[Length(0,36)])

    submit = SubmitField('Register')

    def validate_name(self, field):
        if Org.query.filter_by(name=field.data).first():
            raise ValidationError("Name Already Exist")

    def validate_uuid(self, field):
        if field.data and not isUUID(field.data):
            raise ValidationError("UUID is not valid")
