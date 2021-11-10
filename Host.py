import os
from HostTimeSeries import HostTimeSeries

class Host:

	def __init__(self, path, host_id, store_interval, metrics):
		
		self.id = host_id
		self.path = path
		self.store_interval = store_interval
		self.metrics = metrics
		self.ts_list = []
		self.ts_count = 0

		for entry in os.scandir(self.path):
			if (entry.is_file() and entry.path.endswith(".rrd")):
				if (os.path.basename(entry.path) in metrics):
					self.ts_list.append(HostTimeSeries(entry.path, self, host_id, self.ts_count, "sent", self.store_interval))
					self.ts_list.append(HostTimeSeries(entry.path, self, host_id, self.ts_count+1, "rcvd", self.store_interval))
					self.ts_count += 2

		directories = os.path.normpath(path).split(os.path.sep)
		self.ip = directories[-4] + "." + directories[-3] + "." + directories[-2] + "." + directories[-1]

	def GetTimeSeries(self, metric, series_type):
		for ts in self.ts_list:
			if (os.path.basename(ts.path) == metric and ts.type == series_type):
				return ts
		return None

class HostEdge:

	def __init__(self, host0, host1):
		self.host0 = host0
		self.host1 = host1
		self.score = 0