import re
from flask_wtf import FlaskForm
from wtforms import FileField, ValidationError
from wtforms.fields import (
    StringField,
    SubmitField,
    SelectField,
    TextAreaField,
    HiddenField
)
from wtforms.validators import InputRequired, Length, Optional
from ..db_class.db import Connector, Connector_Icon, Connector_Instance


class AddConnectorForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    icon_select = SelectField(u'Icon', coerce=str, validators=[Optional()])
    
    submit = SubmitField('Add')

    def validate_name(self, field):
        if Connector.query.filter_by(name=field.data).first():
            raise ValidationError("Name Already Exist")
        
    
class AddConnectorInstanceForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    url = StringField('Url', validators=[InputRequired(), Length(0, 64)])
    api_key = StringField('Api key', validators=[Optional(), Length(0, 100)])
    type_select= SelectField(u'Type', coerce=str, validators=[Optional()])
    
    submit = SubmitField('Add')
        

class EditConnectorForm(FlaskForm):
    connector_id = HiddenField("")
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    icon_select = SelectField(u'Icon', coerce=str, validators=[Optional()])
    
    submit = SubmitField('Modify')

    def validate_name(self, field):
        if Connector.query.filter_by(name=field.data).first() and not Connector.query.get(self.connector_id.data).name == field.data:
            raise ValidationError("Name Already Exist")
        

class EditConnectorInstanceForm(FlaskForm):
    instance_id = HiddenField("")
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    url = StringField('Url', validators=[InputRequired(), Length(0, 64)])
    api_key = StringField('Api key', validators=[Optional(), Length(0, 100)])
    type_select= SelectField(u'Type', coerce=str, validators=[Optional()])
    
    submit = SubmitField('Modify')
        
        
class AddIconForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    icon_upload = FileField(u'Icon upload (PNG/JPG):', validators=[InputRequired()])
    
    submit = SubmitField('Add')

    def validate_name(self, field):
        if Connector_Icon.query.filter_by(name=field.data).first():
            raise ValidationError("Name Already Exist")
        
    def validate_icon_upload(self, field):
        if field.data.filename:
            if not re.search(u'\\.jpg|\\.jpeg|\\.png$', field.data.filename):
                raise ValidationError("Extenstion not supported")
            

class EditIconForm(FlaskForm):
    icon_id = HiddenField("")
    name = StringField('Name', validators=[InputRequired(), Length(1, 64)])
    description = TextAreaField('Description', default="", validators=[Optional()])
    icon_upload = FileField('Icon upload (PNG/JPG):' , validators=[Optional()])
    
    submit = SubmitField('Modify')

    def validate_name(self, field):
        if Connector_Icon.query.filter_by(name=field.data).first() and not Connector_Icon.query.get(self.icon_id.data).name == field.data:
            raise ValidationError("Name Already Exist")
        
    def validate_icon_upload(self, field):
        if field.data.filename:
            if not re.search(u'\\.jpg|\\.jpeg|\\.png$', field.data.filename):
                raise ValidationError("Extenstion not supported")
