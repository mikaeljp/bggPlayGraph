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
    create a new instance to clear the history
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
        """
        BGG currently returns XML only.
        Hopefully JSON will be an option at some point, then this method and its caller
        will have to be redone (self.execute())
        """
        yield from Executor.semaphore.acquire()
        response = yield from self.submitRequest(url)
        self.release()
        xmlString = yield from response.read_and_close(decode=False)
        tree = etree.fromstring(xmlString)
        return tree

    @asyncio.coroutine
    def release(self):
        """
        the semaphore is released a half second after the call is done which results
        in a maximum of 20 calls per second.
        I haven't timed the execution yet, but processing is pretty fast.
        """
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
def get_play_history(**kwargs):
    """
    This is the main entry point for this module.

    The function accepts a dictionary of arguments for the call:
    username: bgg username, if the name doesn't match an existing account 
        no results will be returned.  This is the only required value
    startdate: YYYY-MM-DD formatted date string
    enddate: YYYY-MM-DD formatted date string

    There is currently no way to control pagination except with date ranges
    """
    url = URLBuilder("https://www.boardgamegeek.com/xmlapi2/plays")
    if kwargs.get("username") is None:
        raise ValueError("username is required")
    url.addQueryArg("username", kwargs.get("username"))\
        .addQueryArg("mindate", kwargs.get("startdate"))\
        .addQueryArg("maxdate", kwargs.get("enddate"))

    executor = Executor()
    first_page = yield from executor.addRequests([url.build()])

    # bgg api returns the total number of records and 100 records per page
    pageCount = math.ceil(int(first_page[0].attrib.get("total"))/100)

    # new list with url strings for pages 2..n
    # if pageCount is 1, then the list is empty
    last_pages = [url.addQueryArg("page", n).build() for n in range(2, pageCount + 1)]
    responseTrees = yield from executor.addRequests(last_pages)

    playHistory = build_play_history(responseTrees)
    return playHistory

def build_play_history(treelist):
    """
    Takes the xml tree of each page of bgg results and inserts them into a dictionary
    The formatting of the xml seems a little odd to me and this function is very fragile
    w.r.t. any changes in the upstream xml.  Fortunately bgg is really slow to change.
    """
    playRecord = AggregatedPlays()

    for tree in treelist:
        for play in tree.findall('play'):
            quantity = play.get("quantity")
            name = play.find("item").get("name")
            playRecord.insert(name, quantity)

    return playRecord.records

# @asyncio.coroutine
# def get_single_page(url):
#     response = yield from aiohttp.request('GET', url)
#     xmlString = yield from response.read_and_close(decode=False)
#     return etree.fromstring(xmlString)

def call_bgg(**kwargs):
    mainLoop = asyncio.get_event_loop()
    return mainLoop.run_until_complete(get_play_history(**kwargs))


if __name__ == "__main__":
    print(call_bgg(**{"username": "mikaeljp"}))