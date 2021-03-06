#!bgg/bin/python3
import asyncio
import aiohttp
import xml.etree.ElementTree as etree
import math

class AggregatedPlays(object):
    def __init__(self):
        self.records = {}

    def insert(self, name, quantity):
        if name in self.records:
            self.records[name] += int(quantity)
        else:
            self.records[name] = int(quantity)

class URLBuilder(object):
    def __init__(self, baseURL=None):
        if baseURL is not None:
            self.baseURL = baseURL
        else:
            self.baseURL = ""
        self.queryArgs = {}

    def addQueryArg(self, key, value):
        if value is not None:
            self.queryArgs[key] = value
        return self

    def build(self):
        if self.baseURL == "":
            raise(ValueError("URL cannot be built without a base url"))
        if self.queryArgs == {}:
            return self.baseURL
        stringArgs = ["{0}={1}".format(k, v) for k, v in self.queryArgs.items()]
        stringArgs = ("&").join(stringArgs)
        return "?".join([self.baseURL, stringArgs])

@asyncio.coroutine
def print_result(**kwargs):
    playRecord = yield from get_play_history(**kwargs)
    print(playRecord)

@asyncio.coroutine
def get_play_history(**kwargs):
    MAXIMUM_PAGE_COUNT = 10

    url = URLBuilder("https://www.boardgamegeek.com/xmlapi2/plays")
    url.addQueryArg("username", kwargs.get("username"))\
        .addQueryArg("mindate", kwargs.get("startdate"))\
        .addQueryArg("maxdate", kwargs.get("enddate"))
    pagelimit = kwargs.get("pagelimit", MAXIMUM_PAGE_COUNT)
    responseTrees = []
    requestTasks = []

    response = yield from aiohttp.request('GET', url.build())
    xmlString = yield from response.read_and_close(decode=False)
    responseTrees.append(etree.fromstring(xmlString))
    # bgg api returns the total number of records and 100 records per page
    pageCount = min(
        math.ceil(int(responseTrees[0].attrib.get("total"))/100),
        int(pagelimit),
        MAXIMUM_PAGE_COUNT)

    for pageNumber in range(2, pageCount + 1):
        taskURL = url.addQueryArg("page", pageNumber).build()
        task = asyncio.async(get_single_page(taskURL))
        requestTasks.append(task)

    for pendingTree in asyncio.as_completed(requestTasks):
        tree = yield from pendingTree
        responseTrees.append(tree)

    playHistory = build_play_history(responseTrees)
    return playHistory

def build_play_history(treelist):
    playRecord = AggregatedPlays()

    for tree in treelist:
        for play in tree.findall('play'):
            quantity = play.get("quantity")
            name = play.find("item").get("name")
            playRecord.insert(name, quantity)

    return playRecord.records

@asyncio.coroutine
def get_single_page(url):
    response = yield from aiohttp.request('GET', url)
    xmlString = yield from response.read_and_close(decode=False)
    return etree.fromstring(xmlString)



if __name__ == "__main__":
    mainLoop = asyncio.get_event_loop()
    mainLoop.run_until_complete(print_result({"username": "mikaeljp"}))