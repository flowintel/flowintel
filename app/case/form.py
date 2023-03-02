from flask import url_for
from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
    EmailField,
    SelectField,
    TextAreaField
)
from wtforms.validators import Email, EqualTo, InputRequired, Length

from ..db_class.db import Case, Task
from .. import db



class CaseForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description')
    submit = SubmitField('Register')

    def validate_title(self, field):
        if Case.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")

class TaskForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description')
    # group_id = SelectField(u'Category', coerce=str, validators=[InputRequired()])
    submit = SubmitField('Register')

    def validate_title(self, field):
        if Task.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")