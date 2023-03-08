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
    TextAreaField,
    DateField,
    TimeField
)
from wtforms.validators import Email, EqualTo, InputRequired, Length

from ..db_class.db import Case, Task
from .. import db



class CaseForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description')
    dead_line_date = DateField('Dead_line_date')
    dead_line_time = TimeField("Dead_line_time")
    submit = SubmitField('Register')

    def validate_title(self, field):
        if Case.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")

class CaseEditForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description')
    dead_line_date = DateField('Dead_line_date')
    dead_line_time = TimeField("Dead_line_time")
    submit = SubmitField('Modify')


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