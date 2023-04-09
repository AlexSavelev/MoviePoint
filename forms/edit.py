from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, SelectField, SubmitField, IntegerField, FileField
from wtforms.validators import DataRequired

from config import FULL_LENGTH, SERIES

IMAGES = 'jpg jpe jpeg png gif svg bmp'.split()


class MyNewForm(FlaskForm):
    type = SelectField('Тип', choices=[(FULL_LENGTH, 'Полнометражный фильм'), (SERIES, 'Сериал')])
    title = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Применить')


class EditCoverForm(FlaskForm):
    content = FileField('Новая обложка', validators=[FileRequired(), FileAllowed(IMAGES, 'Images only!')])
    submit = SubmitField('Установить')
