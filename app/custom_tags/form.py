from flask_wtf import FlaskForm
from wtforms.fields import (
    StringField,
    SubmitField,
    ColorField
)
from wtforms.validators import InputRequired, Length, ValidationError

from ..db_class.db import Custom_Tags


class AddCustomTagForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 25)])
    color = ColorField('Color', validators=[InputRequired()])
    icon = StringField('Icon')
    submit = SubmitField('Create')

    def validate_name(self, field):
        if field.data and Custom_Tags.query.filter_by(name=field.data.strip()).first():
            raise ValidationError("A custom tag with this name already exists")