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

class Executor(object):
    """
    The executor object handles all bgg requests for a single graph job
    There is a class semaphore to limit the call rate of all executor requests

    usage:
    call addRequests() with a list of urls
    method will yield the collected etrees of the result.
    subsequent calls to addRequests() will return all new and old results in a list
    call clearResults to empty the results list
    """
    semaphore = asyncio.Semaphore(10)
    def __init__(self):
        self.todo = set()
        self.pending = set()
        self.completed = set()
        self.results = []

    def isNewURL(self, url):
        """
        checks if the url has been called before
        """
        if url in self.todo: return False
        if url in self.pending: return False
        if url in self.completed: return False
        return True

    def clearResults(self):
        self.completed = set()
        self.results = []

    @asyncio.coroutine
    def addRequests(self, urls):
        for url in urls:
            if self.isNewURL(url):
                self.todo.add(url)
        results = yield from self.execute()
        return results

    @asyncio.coroutine
    def execute(self):
        """
        goes over the set of input urls and collects the results
        """
        requests = [self.getXML(url) for url in self.todo]
        responseTrees = yield from asyncio.gather(*requests)
        self.results.extend(responseTrees)
        return self.results

    @asyncio.coroutine
    def getXML(self, url):
        yield from Executor.semaphore.acquire()
        response = yield from self.submitRequest(url)
        self.release()
        xmlString = yield from response.read_and_close(decode=False)
        tree = etree.fromstring(xmlString)
        return tree

    @asyncio.coroutine
    def release(self):
        yield from asyncio.sleep(0.5)
        Executor.semaphore.release()

    @asyncio.coroutine
    def submitRequest(self, url):
        """
        This is the problem area.  I'm getting an aiohttp.ClientResponseError occasionally
        and I'm trying to figure out more information, but err is undefined once I get into
        the except block
        """
        try:
            response = yield from aiohttp.request('GET', url)
            return response
        except Exception as err:
            print(err)

@asyncio.coroutine
def print_result(**kwargs):
    playRecord = yield from get_play_history(**kwargs)
    print(playRecord)

@asyncio.coroutine
def get_play_history(**kwargs):
    url = URLBuilder("https://www.boardgamegeek.com/xmlapi2/plays")
    url.addQueryArg("username", kwargs.get("username"))\
        .addQueryArg("mindate", kwargs.get("startdate"))\
        .addQueryArg("maxdate", kwargs.get("enddate"))

    executor = Executor()
    first_page = yield from executor.addRequests([url.build()])

    # bgg api returns the total number of records and 100 records per page
    pageCount = math.ceil(int(first_page[0].attrib.get("total"))/100)

    last_pages = [url.addQueryArg("page", n).build() for n in range(2, pageCount + 1)]
    responseTrees = yield from executor.addRequests(last_pages)

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
    mainLoop.run_until_complete(print_result(**{"username": "mikaeljp"}))