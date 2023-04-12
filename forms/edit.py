from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, SelectField, SelectMultipleField, SubmitField, \
    FileField, MultipleFileField, DateField, TextAreaField
from wtforms.validators import DataRequired

from requests import get
from config import SITE_PATH, FULL_LENGTH, SERIES, AGES

IMAGES = 'jpg jpe jpeg png gif svg bmp'.split()


class MyNewForm(FlaskForm):
    type = SelectField('Тип', choices=[(FULL_LENGTH, 'Полнометражный фильм'), (SERIES, 'Сериал')])
    title = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Применить')


class EditCoverForm(FlaskForm):
    content = FileField('Новая обложка', validators=[FileRequired(), FileAllowed(IMAGES, f'Загружать можно ТОЛЬКО '
                                                                                         f'ИЗОБРАЖЕНИЯ форматов '
                                                                                         f'{", ".join(IMAGES)}')])
    submit = SubmitField('Установить')


class EditImagesForm(FlaskForm):
    content = MultipleFileField('Картинки', validators=[FileAllowed(IMAGES, 'Images only!')])
    submit = SubmitField('Установить')


class EditMovieForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[])
    duration = StringField('Продолжительность', validators=[])
    genres = SelectMultipleField('Жанры', choices=[])
    country = StringField('Страна (-ы)', validators=[])
    director = StringField('Режиссер', validators=[])
    age = SelectField('Возрастное ограничение', choices=[(i, i) for i in AGES])
    world_release_date = DateField('Мировая премьера', format='%Y-%m-%d')
    submit = SubmitField('Применить')

    @staticmethod
    def update_genres():
        EditMovieForm.genres = SelectMultipleField('Жанры', choices=[
            (str(i['id']), i['title']) for i in get(f'{SITE_PATH}/api/v1/genres').json()['genres']])
