#!bgg/bin/python3
from flask import Flask
from flask.ext import restful
from flask.ext.restful import reqparse
import asyncio

from parsePlayHistory import get_play_history
from parsePlayHistory import mainLoop


app = Flask(__name__)
api = restful.Api(app)


class Index(restful.Resource):
    def get(self):
        requestParser = reqparse.RequestParser()
        requestParser.add_argument("username", type=str, required=True, help="BoardGameGeek username is required", location="args")
        requestParser.add_argument("startdate", type=str, help="date in YYYY-MM-DD format", location="args")
        requestParser.add_argument("enddate", type=str, help="date in YYYY-MM-DD format", location="args")
        requestParser.add_argument("pagelimit", type=int, help="limit the number of results returned by BGG", location="args")

        args = requestParser.parse_args()

        bggCall = asyncio.async(get_play_history(args))

        playHistory = mainLoop.run_until_complete(bggCall)
        return playHistory

api.add_resource(Index, "/")

if __name__ == '__main__':
    app.run(debug=True)