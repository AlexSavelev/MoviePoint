from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired

from config import FULL_LENGTH, SERIES


class MyNewForm(FlaskForm):
    type = SelectField('Тип', choices=[(FULL_LENGTH, 'Полнометражный фильм'), (SERIES, 'Сериал')])
    title = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Применить')
