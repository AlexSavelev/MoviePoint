from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('publisher', required=True, type=int)
parser.add_argument('title', required=True)
parser.add_argument('description', required=False)
parser.add_argument('duration_seasons', required=False)
parser.add_argument('duration_series', required=False)
parser.add_argument('genres', required=False)
parser.add_argument('world_release_date', required=False)
parser.add_argument('user_released', required=False, type=bool)
parser.add_argument('series', required=False)
