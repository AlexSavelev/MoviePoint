from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalRangeField, TextAreaField
from wtforms.validators import DataRequired


class AddCommentForm(FlaskForm):
    rating = DecimalRangeField('Оценка', validators=[DataRequired()], default=10)
    title = StringField('Название', validators=[DataRequired()])
    review = TextAreaField('Комментарий', validators=[DataRequired()])
    submit = SubmitField('Добавить')
