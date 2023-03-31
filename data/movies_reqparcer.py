from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('publisher', required=True, type=int)
parser.add_argument('type', required=True)
parser.add_argument('title', required=True)
parser.add_argument('description', required=False)
parser.add_argument('duration', required=False)
parser.add_argument('genres', required=False)
parser.add_argument('world_release_date', required=False)

search_parser = reqparse.RequestParser()
search_parser.add_argument('q', required=True, type=str)
