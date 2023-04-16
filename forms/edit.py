from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, SelectField, SelectMultipleField, SubmitField, \
    FileField, MultipleFileField, DateField, TextAreaField
from wtforms.validators import DataRequired

from requests import get
from config import SITE_PATH, FULL_LENGTH, SERIES, AGES, IMAGES, LANG_MAP


class MyNewForm(FlaskForm):
    type = SelectField('Тип', choices=[(FULL_LENGTH, 'Полнометражный фильм'), (SERIES, 'Сериал')])
    title = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Применить')


class EditCoverForm(FlaskForm):
    content = FileField('Новая обложка', validators=[FileRequired(), FileAllowed(IMAGES, f'Загружать можно ТОЛЬКО '
                                                                                         f'ИЗОБРАЖЕНИЯ форматов '
                                                                                         f'{", ".join(IMAGES)}!')])
    submit = SubmitField('Установить')


class EditImagesForm(FlaskForm):
    content = MultipleFileField('Картинки', validators=[FileAllowed(IMAGES, f'Загружать можно ТОЛЬКО ИЗОБРАЖЕНИЯ '
                                                                            f'форматов {", ".join(IMAGES)}!')])
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


class EditPublishForm(FlaskForm):
    submit = SubmitField('Опубликовать')


class EditSeriesTitleForm(FlaskForm):
    season = StringField('Сезон', validators=[DataRequired()])
    title = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Применить')


class EditSeriesVideoForm(FlaskForm):
    content = FileField('Видео (mp4, h264)', validators=[FileRequired(), FileAllowed(['mp4', 'h264'],
                                                                                     f'Загружать можно ТОЛЬКО ВИДЕО '
                                                                                     f'форматов mp4, h264!')])
    submit = SubmitField('Загрузить')


class EditSeriesAudioForm(FlaskForm):
    lang = SelectField('Язык', choices=[(i, j[1]) for i, j in LANG_MAP.items()])
    content = FileField('Аудио (mp3, aac)', validators=[FileRequired(), FileAllowed(['mp3', 'aac'],
                                                                                    f'Загружать можно ТОЛЬКО АУДИО '
                                                                                    f'форматов mp3, aac!')])
    submit = SubmitField('Загрузить')


class EditSeriesSubsForm(FlaskForm):
    lang = SelectField('Язык', choices=[(i, j[1]) for i, j in LANG_MAP.items()])
    content = FileField('Субтитры (srt, vtt)', validators=[FileRequired(), FileAllowed(['srt', 'vtt'],
                                                                                       f'Загружать можно ТОЛЬКО '
                                                                                       f'СУБТИТРЫ форматов srt, vtt!')])
    submit = SubmitField('Загрузить')
