from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('movie', required=False, type=int)
parser.add_argument('publisher', required=False, type=int)
parser.add_argument('rating', required=False, type=int)
parser.add_argument('title', required=False)
parser.add_argument('review', required=False)

search_parser = reqparse.RequestParser()
search_parser.add_argument('id', required=False, type=int)
search_parser.add_argument('movie', required=False, type=int)
search_parser.add_argument('publisher', required=False, type=int)
