import os
from NtopHostTimeSeries import NtopHostTimeSeries

class Host:

	def __init__(self, path, host_id, store_interval, metrics):
		
		self.id = host_id
		self.path = path
		self.store_interval = store_interval
		self.metrics = metrics
		self.ts_list = []
		self.ts_count = len(metrics) * 2

		series_id = 0
		for entry in os.scandir(self.path):
			if (entry.is_file() and entry.path.endswith(".rrd")):
				if (os.path.basename(entry.path) in metrics):
					self.ts_list.append(NtopHostTimeSeries(entry.path, host_id, series_id, "sent", self.store_interval))
					self.ts_list.append(NtopHostTimeSeries(entry.path, host_id, series_id+1, "rcvd", self.store_interval))
					series_id += 2

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