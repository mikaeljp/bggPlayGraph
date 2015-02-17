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

	def getRecords(self):
		# return self.records
		for record in self.records.items():
			yield record

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
		stringArgs = ["{0}={1}".format(k, v) for k, v in self.queryArgs.items()]
		stringArgs = ("&").join(stringArgs)
		return self.baseURL + "?" + stringArgs

@asyncio.coroutine
def print_result(userName, startDate=None, endDate=None, page=None):
	url = URLBuilder("https://www.boardgamegeek.com/xmlapi2/plays")
	url.addQueryArg("username", userName).addQueryArg("page", page)
	responseTrees = []
	requestTasks = []

	recordDict = AggregatedPlays()
	response = yield from aiohttp.request('GET', url.build())
	xmlString = yield from response.read_and_close(decode=False)
	responseTrees.append(etree.fromstring(xmlString))

	# bgg api returns the total number of records and 100 records per page
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
			recordDict.insert(name, quantity)

	for k, v in recordDict.getRecords():
		print("{0}: {1}".format(k, v))

@asyncio.coroutine
def get_single_page(url):
	response = yield from aiohttp.request('GET', url)
	xmlString = yield from response.read_and_close(decode=False)
	return etree.fromstring(xmlString)



if __name__ == "__main__":
	sample_call = "https://www.boardgamegeek.com/xmlapi2/plays?username=mikaeljp"
	loop = asyncio.get_event_loop()
	loop.run_until_complete(print_result("mikaeljp"))