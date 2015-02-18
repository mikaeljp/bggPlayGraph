#!bgg/bin/python3
import asyncio
from aiohttp import web
import json

from parsePlayHistory import get_play_history
from parsePlayHistory import mainLoop

def parseArgs(stringArgs):
    stringPairs = [arg.split("=") for arg in stringArgs.split("&")]
    filteredPairs = [pair for pair in stringPairs if len(pair) == 2]
    arguments = {k:v for k, v in filteredPairs}
    return arguments

@asyncio.coroutine
def callBGG(request):
    qstring = request.query_string
    arguments = parseArgs(qstring)
    if "username" not in arguments.keys():
        return web.Response(body="username argument is required".encode("utf-8"), status=400)

    playHistory = yield from get_play_history(**arguments)
    return web.Response(body=json.dumps(playHistory, indent=2).encode("utf-8"))


@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route("GET", "/", callBGG)

    srv = yield from loop.create_server(app.make_handler(), "127.0.0.1", 8080)
    print("Server started at http://127.0.0.1:8080")
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()