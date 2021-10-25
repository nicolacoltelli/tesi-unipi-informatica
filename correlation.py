import os
import argparse
from datetime import datetime

from TimeSeries import TimeSeries, Anomaly
from welford import update, finalize
from utils import (
	AlignAnomalies,
	CC_Calculator,
	CrossCovariance,
	FindIntervals,
	lcm,
	RoundHalfUp,
	ScanTree,
)


DEBUG = 0


max_neighborhood = 5


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str)
parser.add_argument('--known', action='store_true')
parser.add_argument('--store', type=int, default=60)
args = parser.parse_args()


def des(series):

	smoothing_status = series.smoothing_status
	alpha = series.alpha
	beta = series.beta

	#initialize smoothing status
	if (smoothing_status == None):
		
		trends = []
		predictions = []
		
		#padding for 0th prediction
		predictions.append(series.values[0])
		trends.append(series.values[0])
		
		predictions.append(series.values[0])
		
		series.smoothing_status = (predictions, trends, 1)
		return

	(predictions, trends, count) = smoothing_status
	
	if (count == 1):
		trends.append(series.values[1] - series.values[0])

	new_prediction = alpha * series.values[count] + (1-alpha)*(predictions[count]+trends[count])
	predictions.append(new_prediction)
	
	new_trend = beta * (new_prediction - predictions[count]) + (1-beta)*trends[count]
	trends.append(new_trend)
	
	count += 1

	series.smoothing_status = (predictions, trends, count)


def CheckAnomaly(series):

	prediction_statistics = series.prediction_statistics
	smoothing_status = series.smoothing_status

	if (smoothing_status == None):
		return None
	
	count = smoothing_status[2]

	last_prediction = smoothing_status[0][-1]
	prediction_error = abs(series.values[count] - last_prediction)

	if (count >= 10):

		stddev = finalize(prediction_statistics)[1] ** 0.5
 
		if ( prediction_error > 3 * stddev ):

			if (stddev != 0):
				anomaly_probability = (prediction_error/stddev - 3)/10
				anomaly_probability = RoundHalfUp(anomaly_probability, 2)
				anomaly_probability = min(anomaly_probability, 1)
			else:
				anomaly_probability = 1

			if (DEBUG > 0):
				if (series.is_rrd == False):
					time = str(count)
				else:
					time = str(datetime.fromtimestamp(series.start_time + count * series.interval))
				print(series.path + ": anomaly found at time " + time + ". (P=" + str(anomaly_probability) + ")." )
			
			# First anomaly (special case).
			if (series.anomalies_count == 0): 
				series.AddAnomaly(count)

			# Previous anomaly still not done. Stretch it.
			elif (series.GetLastAnomaly().end == (count - 1)):
				series.ExtendLastAnomaly()

			# Not following up a previous anomaly. Creating a new instance.
			else:
				series.AddAnomaly(count)

	series.prediction_statistics = update(prediction_statistics, prediction_error)


def CheckCorrelationFromAnomalies(ts_list, time, interval, compare_name):

	current_anomalies = []
	anomalies_count = 0

	#Only correlate anomalies from ts that have the same interval.
	ts_list_interval = []
	for series in ts_list:
		if (series.interval == interval):
			ts_list_interval.append(series)

	# Trying to generate a group of anomalies
	for series in ts_list_interval:
		for anomaly in series.anomalies_to_correlate:

			if (series.index - anomaly.end < max_neighborhood * 2 - 1 and series.finished == False):
				#Waiting because there could be an anomaly ahead still not read.
				continue
			
			wait_unfinished = False
			anomalies_around = []

			for other_series in ts_list_interval:
				if (other_series.id == series.id):
					continue

				if (compare_name == True):
					if (os.path.basename(series.path) != os.path.basename(other_series.path)):
						continue

				if (len(other_series.anomalies_to_correlate) == 0):
					anomalies_around.append((other_series, None))
					continue
			
				anomalies_in_interval_count = 0
				for other_anomaly in series.anomalies_to_correlate:

					if (other_anomaly.start < anomaly.end + max_neighborhood * 2):
						anomalies_in_interval_count += 1

						if (other_anomaly.end == time):
							#A candidate anomaly to correlate has been found, but it's not finished yet
							wait_unfinished = True
							break

						anomalies_around.append((other_series, other_anomaly))

				if (wait_unfinished == True):
					break

				# If two time series both have an anomaly we correlate them, but
				# 	it might be that a time series does not have an anomaly in
				#	that timeframe. If that is the case, we correlate the
				#	timeframe of the time series without looking for a specific
				#	anomaly.
				if (anomalies_in_interval_count == 0):
					anomalies_around.append((other_series, None))
					continue

			if (wait_unfinished == True):
				continue

			current_anomalies.append(((series, anomaly), anomalies_around))
			series.anomalies_to_correlate.remove(anomaly)
			anomalies_count+=1

	# If there are no anomalies in the current group, return
	if (anomalies_count == 0):
		return

	for current_anomaly in current_anomalies:
		a0 = current_anomaly[0]

		for a1 in current_anomaly[1]:

			a0_ts = a0[0].values
			a1_ts = a1[0].values

			a0_start = max(a0[1].start - max_neighborhood, 0)
			a0_end = min(a0[1].end + max_neighborhood, len(a0_ts))

			if (a1[1] != None):
				#Both anomalies
				a1_start = max(a1[1].start - max_neighborhood, 0)
				a1_end = min(a1[1].end + max_neighborhood, len(a1_ts))

				len_a0 = a0_end - a0_start
				len_a1 = a1_end - a1_start

				if ( len_a0 > len_a1 ):
					diff = len_a0 - len_a1
					a1_start, a1_end = AlignAnomalies(a1_start, a1_end, len(a1_ts), diff)

				if ( len_a1 > len_a0 ):
					diff = len_a1 - len_a0
					a0_start, a0_end = AlignAnomalies(a0_start, a0_end, len(a0_ts), diff)

			else:
				#a0 anomaly, a1 ts
				if ( a0_end < len(a1_ts) ):
					a1_start = max(a0_start - max_neighborhood, 0)
					a1_end = min(a0_end + max_neighborhood, len(a1_ts))
				else:
					continue

			cc_array = CrossCovariance(a0_ts[a0_start:a0_end], a1_ts[a1_start:a1_end])
			abs_cc_array = [abs(elem) for elem in cc_array] 
			cc = max(abs_cc_array)

			if (cc >= 0.8):

				if (a1[1] != None):

					if (a0[0].is_rrd == False):
						time0start = str(a0[1].start)
						time0end = str(a0[1].end)
						time1start = str(a1[1].start)
						time1end = str(a1[1].end)
					else:
						time0start = str(datetime.fromtimestamp(a0[0].start_time + a0[1].start * a0[0].interval))
						time0end = str(datetime.fromtimestamp(a0[0].start_time + a0[1].end * a0[0].interval))
						time1start = str(datetime.fromtimestamp(a1[0].start_time + a1[1].start * a1[0].interval))
						time1end = str(datetime.fromtimestamp(a1[0].start_time + a1[1].end * a1[0].interval))

					cc = RoundHalfUp(cc, 2)
					print("Correlation found between " +
						"anomaly from " + time0start + " to " + time0end +
						" in " + a0[0].path +
						" and " + 
						"anomaly from " + time1start + " to " + time1end +
						" in " + a1[0].path +
						". (P=" + str(cc) + ")."
						)
				else:

					delay = abs_cc_array.index(cc)
					len_a0 = a0_end - a0_start
					cc = RoundHalfUp(cc, 2)

					if (a0[0].is_rrd == False):
						time0start = str(a0[1].start)
						time0end = str(a0[1].end)
						time1start = str(a1_start+delay)
						time1end = str(a1_start+delay+len_a0)
					else:
						time0start = str(datetime.fromtimestamp(a0[0].start_time + a0[1].start * a0[0].interval))
						time0end = str(datetime.fromtimestamp(a0[0].start_time + a0[1].end * a0[0].interval))
						time1start = str(datetime.fromtimestamp(a1[0].start_time + (a1_start+delay) * a1[0].interval))
						time1end = str(datetime.fromtimestamp(a1[0].start_time + (a1_start+delay+len_a0) * a1[0].interval))

					print("Correlation found between " +
						"anomaly from " + time0start + " to " + time0end +
						" in " + a0[0].path +
						" and " + 
						"values from " + time1start + " to " + time1end +
						" in " + a1[0].path +
						". (P=" + str(cc) + ")."
						)


def CheckCorrelation(ts_list, interval, compare_name):

	#Only correlate ts that have the same interval.
	ts_list_interval = []
	for series in ts_list:
		if (series.interval == interval):
			ts_list_interval.append(series)

	series_count = len(ts_list_interval)

	for i in range(series_count):

		series0 = ts_list_interval[i]
		if (series0.finished == True):
			continue

		if (len(series0.sec) < 10 ):
			continue
		
		for j in range(i+1, series_count):

			series1 = ts_list_interval[j]
			if (series1.finished == True):
				continue

			if ( len(series1.sec) < 10):
				continue

			if (compare_name == True):
				if (os.path.basename(series0.path) != os.path.basename(series1.path)):
					continue

			mean0 = series0.GetMean()
			mean1 = series1.GetMean()
			stdev0 = series0.GetStdev() 
			stdev1 = series1.GetStdev()

			if ( (mean0 == 0 and stdev0 == 0)  or  (mean1 == 0 and stdev1 == 0) ):
				#one of the two series (or both) contains no significant data.
				continue

			if (mean0 == 0 or mean1 == 0):
				mean_ratio = 1
			else:
				mean_ratio = abs(mean0 / mean1)

			adjusted_stdev0 = stdev0 / mean_ratio
			stdev_difference = abs(adjusted_stdev0 - stdev1)
			min_stdev = min(adjusted_stdev0, stdev1)

			# @@@ check logic
			if (min_stdev == 0):
				stdev_difference_ratio = stdev_difference
			else:
				stdev_difference_ratio = stdev_difference / min_stdev

			if (stdev_difference_ratio > 0.5):
				continue

			sec_cc = abs(CrossCovariance(series0.sec, series1.sec)[0])
			denominator = 1

			min_cc = 0
			hour_cc = 0
			if (len(series0.min) >= 10 and len(series1.min) >= 10):
				min_cc = abs(CrossCovariance(series0.min, series1.min)[0])
				denominator += 1

				if (len(series0.hour) >= 10 and len(series1.hour) >= 10):
					hour_cc = abs(CrossCovariance(series0.hour, series1.hour)[0])
					denominator += 1

			avg_cc = (sec_cc + min_cc + hour_cc)/denominator
			avg_cc = RoundHalfUp(avg_cc, 2)

			if (avg_cc >= 0.8):

				if (series0.is_rrd == False):
					time = str(series0.index)
				else:
					time = str(datetime.fromtimestamp(series0.start_time + series0.index * series0.interval))

				print("continuous correlation between" +
							" ts " + series0.path +
							" and" + 
							" ts " + series1.path +
							" at time " + time +
							": " + str(avg_cc) + " ."
							)


if __name__ == "__main__" :

	if (args.input == None):
		print("Error: input path not specified. Use python3 correlation.py --input input_path")
		exit(1)

	ts_list = []
	store_interval = args.store

	series_id = 0
	for entry in ScanTree(args.input):
		if (entry.is_file() and (entry.path.endswith(".dat") or entry.path.endswith(".rrd"))):
			ts_list.append(TimeSeries(entry.path, series_id, store_interval))
			series_id += 1

	if (series_id == 0):
		print("Error: no file with extension \".dat\" or \".rrd\" found in the specified directory.")
		exit(1)

	extension = ts_list[0].path[-3:]
	for series in ts_list:
		if series.path[-3:] != extension:
			print("Error: files must be either only \".dat\" or only \".rrd\". No mixed datasources allowed.")
			exit(1)

	#lcm = least common multiple
	intervals = FindIntervals(ts_list)
	lcm_interval = lcm(intervals)
	min_interval = min(intervals)

	time = 0
	ts_count = len(ts_list)
	while ts_count > 0:
		for series in ts_list:

			if (series.finished):
				continue

			if (time * min_interval >= series.interval * series.index):
				if (series.ReadValue()):
					CheckAnomaly(series)
					des(series)
				else:
					ts_count -= 1

		for interval in intervals:
			if ( min_interval  >  (time * min_interval) % interval ):
				CheckCorrelationFromAnomalies(ts_list, time, interval, args.known)
		
		time += 1

		for interval in intervals:
			if ( store_interval * interval - min_interval  <=  ((time - 1) * min_interval) % (store_interval * interval) ):
				CheckCorrelation(ts_list, interval, args.known)
