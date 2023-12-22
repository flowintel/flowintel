from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    StringField,
    SubmitField,
    SelectMultipleField,
    TextAreaField,
    HiddenField,
    IntegerField
)
from wtforms.validators import InputRequired, Length, Optional

from ..db_class.db import Case_Template, Task_Template


class TaskTemplateForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(),Length(1, 64)])
    body = TextAreaField('Description', validators=[Optional()])
    url = StringField('Tool/Link', validators=[Optional(), Length(0, 64)])
    tasks = SelectMultipleField(u'Task Template', coerce=int, validators=[Optional()])

    submit = SubmitField('Create')

    def validate_title(self, field):
        if field.data and Task_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
        

class TaskTemplateEditForm(FlaskForm):
    template_id = HiddenField("")
    title = StringField('Title', validators=[InputRequired(),Length(1, 64)])
    body = TextAreaField('Description', validators=[Optional()])
    url = StringField('Tool/Link', validators=[Optional(), Length(0, 64)])

    submit = SubmitField('Save')

    def validate_title(self, field):
        template = Task_Template.query.get(self.template_id.data)
        if not template.title == field.data:
            if field.data and Task_Template.query.filter_by(title=field.data).first():
                raise ValidationError("The title already exist")
    

class CaseTemplateForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(),Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    tasks = SelectMultipleField(u'Task Template', coerce=int, validators=[Optional()])
    
    submit = SubmitField('Create')

    def validate_title(self, field):
        if Case_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
        


class CaseTemplateEditForm(FlaskForm):
    template_id = HiddenField("")
    title = StringField('Title', validators=[InputRequired(),Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    
    submit = SubmitField('Save')

    def validate_title(self, field):
        template = Case_Template.query.get(self.template_id.data)
        if not template.title == field.data:
            if Case_Template.query.filter_by(title=field.data).first():
                raise ValidationError("The title already exist")

        