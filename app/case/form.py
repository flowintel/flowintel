from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    StringField,
    SubmitField,
    SelectMultipleField,
    TextAreaField,
    DateField,
    TimeField, 
    HiddenField
)
from wtforms.validators import InputRequired, Length, Optional
from werkzeug.utils import secure_filename

from ..db_class.db import Case, Case_Org


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
    url = StringField('Tool/Link', validators=[Optional(), Length(0, 64)])
    dead_line_date = DateField('Dead_line_date', validators=[Optional()])
    dead_line_time = TimeField("Dead_line_time", validators=[Optional()])
    submit = SubmitField('Register')

    def validate_dead_line_time(self, field):
        if field.data and not self.dead_line_date.data:
            raise ValidationError("Choose a date")



class TaskEditForm(FlaskForm):
    title = StringField(
        'Title', validators=[InputRequired(),
                                  Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    url = StringField('Tool/Link', validators=[Optional(), Length(0, 64)])
    dead_line_date = DateField('Dead_line_date', validators=[Optional()])
    dead_line_time = TimeField("Dead_line_time", validators=[Optional()])
    submit = SubmitField('Modify')

    def validate_dead_line_time(self, field):
        if field.data and not self.dead_line_date.data:
            raise ValidationError("Choose a date")


class AddOrgsCase(FlaskForm):
    org_id = SelectMultipleField(u'Orgs', coerce=int)
    case_id = HiddenField("")

    submit = SubmitField('Register')

    def validate_org_id(self, field):
        for org in field.data:
            if Case_Org.query.filter_by(case_id = self.case_id.data, org_id=org).first():
                raise ValidationError(f"Org {org} already in case")

        