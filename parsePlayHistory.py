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


	recordDict = AggregatedPlays()
	response = yield from aiohttp.request('GET', url.build())
	xmlString = yield from response.read_and_close(decode=False)
	tree = etree.fromstring(xmlString)

	pageCount = math.ceil(int(tree.attrib.get("total"))/100)

	for play in tree.findall('play'):
		quantity = play.get("quantity")
		name = play.find("item").get("name")
		recordDict.insert(name, quantity)

	for k, v in recordDict.getRecords():
		print("{0}: {1}".format(k, v))

@asyncio.coroutine
def multi_request(url, pageCount):
	"""
	once the first page has returned the program can determine the remaining number
	of pages.  This function will aggregate the remaining pages 2...n and add their
	records to the AggregatedPlays object
	"""



if __name__ == "__main__":
	sample_call = "https://www.boardgamegeek.com/xmlapi2/plays?username=mikaeljp"
	loop = asyncio.get_event_loop()
	loop.run_until_complete(print_result("mikaeljp"))