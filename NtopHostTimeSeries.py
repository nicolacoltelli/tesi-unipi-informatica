from statistics import mean
from welford import update, finalize
import rrdtool


class NtopHostTimeSeries:

	
	def __init__(self, path, host_id, series_id, series_type, store_interval):

		self.path = path
		self.host_id = host_id
		self.id = series_id
		self.type = series_type

		self.rrd_results = rrdtool.fetch(path, 'AVERAGE', "-s -2h")
		self.start_time = self.rrd_results[0][0]

		self.rrd_count = 0
		self.rrd_values = []
			
		for elem in self.rrd_results[2]:
		
			if (self.type == "sent"):
				elem = elem[0]
			else:
				elem = elem[1]

			if elem != None:
				self.rrd_values.append(elem)
			else:
				self.rrd_values.append(0)
		
			self.rrd_count += 1
			
		self.values = []
		self.index = 0

		self.store_interval = store_interval
		self.sec = []
		self.min = []
		self.hour = []

		#contains a tuple of count, mean, sum of squared differences from current mean.
		self.values_statistics = (0,0,0)
		self.prediction_statistics = (0,0,0)

		self.anomalies_count = 0
		self.anomalies = []
		self.anomalies_to_correlate = []

		self.alpha = 0.8
		self.beta = 0.8
		self.smoothing_status = None

		self.finished = False


	def ReadValue(self):

		new_value = self.ValueFromRRD()

		if (new_value == None):
			self.finished = True
			return False

		self.values.append(new_value)
		self.sec.append(new_value)
		self.index += 1

		self.UpdateStatistics(new_value)

		if (len(self.sec) == self.store_interval * 2):
			self.min.append(mean(self.sec[:self.store_interval]))
			self.sec = self.sec[self.store_interval:]

		if (len(self.min) == self.store_interval * 2):
			self.hour.append(mean(self.min[:self.store_interval]))
			self.min = self.min[self.store_interval:]

		return True
	

	def ValueFromRRD(self):
		
		if (self.index >= self.rrd_count):
			return None

		new_value =  self.rrd_values[self.index]
		return new_value


	def UpdateStatistics(self, new_value):
		self.values_statistics = update(self.values_statistics, new_value)


	def GetMean(self):
		return self.values_statistics[1]


	def GetStdev(self):
		return finalize(self.values_statistics)[1] ** 0.5


	def GetLastAnomaly(self):
		return self.anomalies[-1]


	def AddAnomaly(self, start):
		new_anomaly = Anomaly(start, self.id, self.anomalies_count)
		self.anomalies.append(new_anomaly)
		self.anomalies_to_correlate.append(new_anomaly)
		self.anomalies_count += 1


	def ExtendLastAnomaly(self):
		self.anomalies[-1].ExtendEnd()


	def PrintAnomalies(self):
		print(self.path + ":")
		for anomaly in self.anomalies:
			print("\t(" + str(anomaly.start) + ":" + str(anomaly.end) + ");")
		print("")



class Anomaly:


	def __init__(self, start, anomaly_id, series_id):
		self.start = start
		self.end = start
		self.id = anomaly_id
		self.series = series_id


	def ExtendEnd(self):
		self.end += 1
