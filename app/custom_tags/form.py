from flask_wtf import FlaskForm
from wtforms.fields import (
    StringField,
    SubmitField,
    ColorField
)
from wtforms.validators import InputRequired, Length


class AddCustomTagForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(1, 25)])
    color = ColorField('Color', validators=[InputRequired()])
    icon = StringField('Icon')
    submit = SubmitField('Create')