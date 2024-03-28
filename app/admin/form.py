from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    EmailField,
    SelectField,
    TextAreaField,
    HiddenField
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, Optional
from ..db_class.db import User, Org
from ..utils.utils import isUUID


class RegistrationForm(FlaskForm):
    first_name = StringField('First name', validators=[InputRequired(), Length(1, 64)])
    last_name = StringField('Last name', validators=[InputRequired(), Length(1, 64)])
    nickname = StringField('Nickname', validators=[Length(1, 64)])
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[
            InputRequired(),
            EqualTo('password2', 'Passwords must match')
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
    nickname = StringField('Nickname', validators=[Length(1, 64)])
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[Optional(), EqualTo('password2', 'Passwords must match')])
    password2 = PasswordField('Confirm password')
    matrix_id = StringField('Matrix id', render_kw={"placeholder": "@testuser:matrix.org"})

    role = SelectField(u'Role', coerce=str, validators=[InputRequired()])
    org = SelectField(u'Organisation', coerce=str, validators=[InputRequired()])

    submit = SubmitField('Register')

    def validate_email(self, field):
        user = User.query.get(self.user_id.data)
        if not field.data == user.email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already registered')


class CreateOrgForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    uuid = StringField('UUID', validators=[Length(0,36)])

    submit = SubmitField('Register')

    def validate_name(self, field):
        if Org.query.filter_by(name=field.data).first():
            raise ValidationError("Name Already Exist")

    def validate_uuid(self, field):
        if field.data:
            if not isUUID(field.data):
                raise ValidationError("UUID is not valid")
