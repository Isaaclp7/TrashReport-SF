from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

class RequestForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    picture = FileField('Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Post')

    