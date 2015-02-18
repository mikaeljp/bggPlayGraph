#!bgg/bin/python3
import asyncio
import aiohttp
import xml.etree.ElementTree as etree
import math

mainLoop = asyncio.get_event_loop()

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
def print_result(username, startDate=None, endDate=None, pageLimit=None):
    playRecord = yield from get_play_history(username, startDate, endDate, pageLimit)
    print(playRecord)

@asyncio.coroutine
def get_play_history(username, startdate=None, enddate=None, pagelimit=None):
    url = URLBuilder("https://www.boardgamegeek.com/xmlapi2/plays")
    url.addQueryArg("username", username)\
        .addQueryArg("mindate", startdate)\
        .addQueryArg("maxdate", enddate)
    responseTrees = []
    requestTasks = []

    playRecord = AggregatedPlays()
    response = yield from aiohttp.request('GET', url.build())
    xmlString = yield from response.read_and_close(decode=False)
    responseTrees.append(etree.fromstring(xmlString))
    # bgg api returns the total number of records and 100 records per page
    if pagelimit is not None:
        pageCount = min(
            math.ceil(int(responseTrees[0].attrib.get("total"))/100),
            pageLimit)
    else: 
        pageCount = math.ceil(int(responseTrees[0].attrib.get("total"))/100)

    for pageNumber in range(2, pageCount + 1):
        taskURL = url.addQueryArg("page", pageNumber).build()
        task = asyncio.async(get_single_page(taskURL))
        requestTasks.append(task)

    for pendingTree in asyncio.as_completed(requestTasks):
        tree = yield from pendingTree
        responseTrees.append(tree)

    for tree in responseTrees:
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
    # loop = asyncio.get_event_loop()
    mainLoop.run_until_complete(print_result("mikaeljp"))