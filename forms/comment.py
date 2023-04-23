from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalRangeField
from wtforms.validators import DataRequired


class AddCommentForm(FlaskForm):
    rating = DecimalRangeField('Оценка', validators=[DataRequired()])
    title = StringField('Название', validators=[DataRequired()])
    review = StringField('Комментарий', validators=[DataRequired()])
    submit = SubmitField('Добавить')
