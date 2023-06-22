from flask import url_for
from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    EmailField,
    SelectField,
    TextAreaField,
    BooleanField,
    HiddenField
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, Optional

from ..db_class.db import User, Org, Role

from ..utils.utils import isUUID

class RegistrationForm(FlaskForm):
    first_name = StringField(
        'First name', validators=[InputRequired(),
                                  Length(1, 64)])
    last_name = StringField(
        'Last name', validators=[InputRequired(),
                                 Length(1, 64)])
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[
            InputRequired(),
            EqualTo('password2', 'Passwords must match')
        ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])

    role = SelectField(u'Role', coerce=str, validators=[InputRequired()])
    org = SelectField(u'Organisation', coerce=str, validators=[InputRequired()])

    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered. (Did you mean to '
                                  '<a href="{}">log in</a> instead?)'.format(
                                    url_for('account.index')))



class AdminEditUserFrom(FlaskForm):
    user_id = HiddenField("")
    first_name = StringField('First name', validators=[InputRequired(), Length(1, 64)])
    last_name = StringField('Last name', validators=[InputRequired(), Length(1, 64)])
    email = EmailField('Email', validators=[InputRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[EqualTo('password2', 'Passwords must match')])
    password2 = PasswordField('Confirm password')

    role = SelectField(u'Role', coerce=str, validators=[InputRequired()])
    org = SelectField(u'Organisation', coerce=str, validators=[InputRequired()])

    submit = SubmitField('Register')

    def validate_email(self, field):
        user = User.query.get(self.user_id.data)
        if not field.data == user.email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already registered. (Did you mean to '
                                    '<a href="{}">log in</a> instead?)'.format(
                                        url_for('account.index')))


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


class AddRoleForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(),Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    admin = BooleanField("Admin", default=False, false_values=(False, 'false'))
    read_only = BooleanField("Read only", default=True, false_values=(False, 'false'))

    submit = SubmitField('Register')

    def validate_name(self, field):
        if Role.query.get(field.data):
            raise ValidationError("Name already exist")