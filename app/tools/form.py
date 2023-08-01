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
    title = StringField('Title', validators=[Optional(),Length(1, 64)])
    body = TextAreaField('Description', validators=[Optional()])
    url = StringField('Tool/Link', validators=[Optional(), Length(0, 64)])
    tasks = SelectMultipleField(u'Task Template', coerce=int, validators=[Optional()])

    submit = SubmitField('Create')

    def validate_title(self, field):
        if field.data and Task_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
        

class TaskTemplateEditForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(),Length(1, 64)])
    body = TextAreaField('Description', validators=[Optional()])
    url = StringField('Tool/Link', validators=[Optional(), Length(0, 64)])

    submit = SubmitField('Edit')
        
    

class CaseTemplateForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(),Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    tasks = SelectMultipleField(u'Task Template', coerce=int, validators=[Optional()])
    
    submit = SubmitField('Create')

    def validate_title(self, field):
        if Case_Template.query.filter_by(title=field.data).first():
            raise ValidationError("The title already exist")
        


# class CaseEditForm(FlaskForm):
#     title = StringField(
#         'Title', validators=[InputRequired(),
#                                   Length(1, 64)])
#     description = TextAreaField('Description', validators=[Optional()])
#     deadline_date = DateField('deadline_date', validators=[Optional()])
#     deadline_time = TimeField("deadline_time", validators=[Optional()])
#     submit = SubmitField('Modify')

#     def validate_deadline_time(self, field):
#         if field.data and not self.deadline_date.data:
#             raise ValidationError("Choose a date")


        