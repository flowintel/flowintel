from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import (
    StringField,
    SubmitField,
    SelectMultipleField,
    TextAreaField,
    HiddenField
)
from wtforms.validators import InputRequired, Length, Optional

from ..db_class.db import Case_Template, Task_Template


class TaskTemplateForm(FlaskForm):
    title = StringField('Title', validators=[Optional()])
    time_required = StringField('Time required', validators=[Optional()])
    tasks = SelectMultipleField(u'Task Template', coerce=int, validators=[Optional()])

    submit = SubmitField('Create')

    def validate_title(self, field):
        if not field.data and 0 in self.tasks.data:
            raise ValidationError("Need to enter a title or select a template")
        if field.data and Task_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
    
    def validate_tasks(self, field):
        if 0 in field.data and not self.title.data:
            raise ValidationError("Need to select a template or enter a title")
        

class TaskTemplateEditForm(FlaskForm):
    template_id = HiddenField("")
    title = StringField('Title', validators=[InputRequired()])
    time_required = StringField('Time required', validators=[Optional()])

    submit = SubmitField('Save')

    def validate_title(self, field):
        template = Task_Template.query.get(self.template_id.data)
        if not template.title == field.data and field.data and Task_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
    

class CaseTemplateForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired()])
    tasks = SelectMultipleField(u'Task Template', coerce=int, validators=[Optional()])
    time_required = StringField('Time required', validators=[Optional()])
    
    submit = SubmitField('Create')

    def validate_title(self, field):
        if Case_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
        


class CaseTemplateEditForm(FlaskForm):
    template_id = HiddenField("")
    title = StringField('Title', validators=[InputRequired()])
    time_required = StringField('Time required', validators=[Optional()])
    
    submit = SubmitField('Save')

    def validate_title(self, field):
        template = Case_Template.query.get(self.template_id.data)
        if not template.title == field.data and Case_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")

        