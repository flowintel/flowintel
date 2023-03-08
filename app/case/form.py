from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    BooleanField,
    StringField,
    SubmitField,
    EmailField,
    SelectField,
    TextAreaField,
    DateField,
    TimeField
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, Optional

from ..db_class.db import Case, Task


class CaseForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    dead_line_date = DateField('Dead_line_date', validators=[Optional()])
    dead_line_time = TimeField("Dead_line_time", validators=[Optional()])
    submit = SubmitField('Register')

    def validate_title(self, field):
        if Case.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
    
    def validate_dead_line_time(self, field):
        if field.data and not self.dead_line_date.data:
            raise ValidationError("Choose a date")

class CaseEditForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    dead_line_date = DateField('Dead_line_date', validators=[Optional()])
    dead_line_time = TimeField("Dead_line_time", validators=[Optional()])
    submit = SubmitField('Modify')

    def validate_dead_line_time(self, field):
        if field.data and not self.dead_line_date.data:
            raise ValidationError("Choose a date")


class TaskForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    # group_id = SelectField(u'Category', coerce=str, validators=[InputRequired()])
    dead_line_date = DateField('Dead_line_date', validators=[Optional()])
    dead_line_time = TimeField("Dead_line_time", validators=[Optional()])
    submit = SubmitField('Register')

    def validate_title(self, field):
        if Task.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")

    def validate_dead_line_time(self, field):
        if field.data and not self.dead_line_date.data:
            raise ValidationError("Choose a date")


class TaskEditForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    dead_line_date = DateField('Dead_line_date', validators=[Optional()])
    dead_line_time = TimeField("Dead_line_time", validators=[Optional()])
    submit = SubmitField('Modify')

    def validate_dead_line_time(self, field):
        if field.data and not self.dead_line_date.data:
            raise ValidationError("Choose a date")
