from statistics import mean
import rrdtool


class TimeSeries:

	
	def __init__(self, path, series_id, store_interval):

		self.path = path
		self.id = series_id

		if (path.endswith(".rrd")):
		
			self.is_rrd = True
			self.rrd_results = rrdtool.fetch(path, 'AVERAGE', "-s -2h")
			self.interval = self.rrd_results[0][2]
			self.start_time = self.rrd_results[0][0]

			self.rrd_count = 0
			self.rrd_values = []
			
			for elem in self.rrd_results[2]:
			
				elem = elem[0]
			
				if elem != None:
					self.rrd_values.append(elem)
				else:
					self.rrd_values.append(0)
			
				self.rrd_count += 1
			
		else:
		
			self.is_rrd = False
			self.interval = 1
			self.start_time = 0
			self.file = open(path, "r")

		self.values = []
		self.index = 0

		self.store_interval = store_interval
		self.sec = []
		self.min = []
		self.hour = []

		#contains a tuple of count, mean, sum of squared differences from current mean.
		self.prediction_statistics = (0,0,0)

		self.anomalies_count = 0
		self.anomalies = []
		self.anomalies_to_correlate = []

		self.alpha = 0.8
		self.beta = 0.8
		self.smoothing_status = None

		self.finished = False


	def ReadValue(self):

		if (self.is_rrd == True):
			new_value = self.ValueFromRRD()
		else:
			new_value = self.ValueFromDat()

		if (new_value == None):
			self.finished = True
			return False

		self.values.append(new_value)
		self.sec.append(new_value)
		self.index += 1
		
		if (len(self.sec) == self.store_interval * 2):
			self.min.append(mean(self.sec[:self.store_interval]))
			self.sec = self.sec[self.store_interval:]
		
		if (len(self.min) == self.store_interval * 2):
			self.hour.append(mean(self.min[:self.store_interval]))
			self.min = self.min[self.store_interval:]

		return True
	

	def ValueFromDat(self):
		line = self.file.readline()
		if (line != ""):
			return float(line)
		else:
			return None


	def ValueFromRRD(self):
		
		if (self.index >= self.rrd_count):
			return None

		new_value =  self.rrd_values[self.index]
		return new_value


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
