import os
import math
import numpy as np
import matplotlib.pyplot as plt
import argparse
from statistics import mean, pstdev
from functools import reduce
from datetime import datetime

from TimeSeries import TimeSeries, Anomaly

DEBUG = 0

max_neighborhood = 5
store_interval = 20


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str)
args = parser.parse_args()


def RoundHalfUp(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier


# Welford's algorithm
# https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_online_algorithm
def update(existingAggregate, newValue):
    (count, mean, M2) = existingAggregate
    count += 1
    delta = newValue - mean
    mean += delta / count
    delta2 = newValue - mean
    M2 += delta * delta2
    return (count, mean, M2)


# Retrieve the mean, variance and sample variance from an aggregate
def finalize(existingAggregate):
    (count, mean, M2) = existingAggregate
    if count < 2:
        return float("nan")
    else:
        (mean, variance, sampleVariance) = (mean, M2 / count, M2 / (count - 1))
        return (mean, variance, sampleVariance)


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

	statistics = series.statistics
	smoothing_status = series.smoothing_status

	if (smoothing_status == None):
		return None
	
	count = smoothing_status[2]

	last_prediction = smoothing_status[0][-1]
	prediction_error = abs(series.values[count] - last_prediction)

	if (count >= 10):

		stddev = math.sqrt(finalize(statistics)[1])

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

	series.statistics = update(statistics, prediction_error)


def AlignAnomalies(start, end, length, align):

	pad_left = (align + 1) // 2
	pad_right = align // 2

	if ( start >= pad_left):
		#If there is enough space on the left.
		start -= pad_left
		pad_left = 0
	else:
		#If not, pad as much as possible and add the
		# remainder on the right.
		pad_right += (pad_left - start)
		pad_left = 0
		start = 0

	if ( (end + pad_right) < length ):
		#If there is enough space on the right.
		end += pad_right
		pad_right = 0
	else:
		#If not, pad as much as possible and add the
		# remainder on the left.
		pad_left = length - 1 - end
		pad_right = 0
		end = length - 1

	# pad_left > 0 => there is no more space on the right.
	# So we put as much padding as we can on the left
	if ( pad_left > 0 ):
		start = max(start - pad_left, 0)

	return start, end


def CC_Calculator(a0, a1, n):

	mean_a0 = mean(a0) 
	mean_a1 = mean(a1) 
	stddev_a0 = pstdev(a0)
	stddev_a1 = pstdev(a1)

	if (stddev_a0 == 0 or stddev_a1 == 0):
		return 0

	covariance = 0
	for i in range(0, n):
		covariance += ((a0[i] - mean_a0) * (a1[i] - mean_a1))
	covariance /= n

	return covariance / (stddev_a0 * stddev_a1)


def CrossCovariance(a0, a1):
	
	if (len(a0) > len(a1)):
		swap = a0
		a0 = a1
		a1 = swap

	delays = len(a1) - len(a0) + 1
	cc_array = []

	a0_len = len(a0)
	for t in range(0, delays):
		cc = CC_Calculator(a0, a1[t:t+a0_len], a0_len)
		cc_array.append(cc)

	return cc_array


def CheckCorrelationFromAnomalies(ts_list, time):

	current_anomalies = []
	anomalies_count = 0

	# Trying to generate a group of anomalies
	for series in ts_list:
		for anomaly in series.anomalies_to_correlate:
			if series.index - anomaly.end < max_neighborhood * 2 - 1:
				#Waiting because there could be an anomaly ahead still not read.
				return
			else:
				current_anomalies.append((series, anomaly))
				anomalies_count+=1

	# If there are no anomalies in the current group, return
	if (anomalies_count == 0):
		return

	# If two time series both have an anomaly we correlate them, but
	# 	it might be that a time series does not have an anomaly in
	#	that timeframe. If that is the case, we correlate the
	#	timeframe of the time series without looking for a specific
	#	anomaly.
	for series in ts_list:
		if len(series.anomalies_to_correlate) == 0:
			current_anomalies.append((series, None))
		else:
			series.anomalies_to_correlate = []

	for i in range(anomalies_count):
		for j in range(i+1, len(current_anomalies)):
			
			a0 = current_anomalies[i]
			a1 = current_anomalies[j]

			# Don't correlate anomalies from the same time series.
			if (a1[1] != None and a0[0].id == a1[0].id):
				continue

			#If series are from rrd, intervals must match
			if (a0[0].is_rrd == True and a0[0].interval != a1[0].interval):
				continue

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
						time0start = str(datetime.fromtimestamp(a0[0].start_time + a0[1].start * series.interval))
						time0end = str(datetime.fromtimestamp(a0[0].start_time + a0[1].end * series.interval))
						time1start = str(datetime.fromtimestamp(a1[0].start_time + a1[1].start * series.interval))
						time1end = str(datetime.fromtimestamp(a1[0].start_time + a1[1].end * series.interval))

					cc = RoundHalfUp(cc, 2)
					print("Correlation found between " +
						"anomaly from (" + time0start + " to " + time0end + ")" +
						" in " + a0[0].path +
						" and " + 
						"anomaly from (" + time1start + " to " + time1end + ")" +
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
						time0start = str(datetime.fromtimestamp(a0[0].start_time + a0[1].start * series.interval))
						time0end = str(datetime.fromtimestamp(a0[0].start_time + a0[1].end * series.interval))
						time1start = str(datetime.fromtimestamp(a1[0].start_time + (a1_start+delay) * series.interval))
						time1end = str(datetime.fromtimestamp(a1[0].start_time + (a1_start+delay+len_a0) * series.interval))

					print("correlation found between " +
						"anomaly at (" + time0start + ":" + time0end + ")" +
						" in " + a0[0].path +
						" and " + 
						"values at (" + time1start + ":" + time1end + ")" +
						" in " + a1[0].path +
						". (P=" + str(cc) + ")."
						)



def CheckCorrelation(ts_list, interval):

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

			if (series0.interval != series1.interval):
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

			print("continuous correlation between" +
							" ts " + series0.path +
							" and" + 
							" ts " + series1.path +
							": " + str(avg_cc) + " ."
							)


def FindIntervals(ts_list):
	intervals = {ts_list[0].interval}
	for ts in ts_list:
		intervals.add(ts.interval)
	return intervals


def lcm(intervals):
	return reduce(lambda a,b: a*b // math.gcd(a,b), intervals)


def ScanTree(path):
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from ScanTree(entry.path)
        else:
            yield entry


if __name__ == "__main__" :

	ts_list = []

	series_id = 0
	for entry in ScanTree(args.input):
		if (entry.is_file() and (entry.path.endswith(".dat") or entry.path.endswith(".rrd"))):
			ts_list.append(TimeSeries(entry.path, series_id, store_interval))
			series_id += 1

	if (series_id == 0):
		print("No file with extension \".dat\" or \".rrd\" found in the specified directory.")
		exit(1)

	extension = ts_list[0].path[-3:]
	for series in ts_list:
		if series.path[-3:] != extension:
			print("Files must be either only \".dat\" or only \".rrd\". No mixed datasources allowed.")
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

		CheckCorrelationFromAnomalies(ts_list, time)
		time += 1

		for interval in intervals:
			if (time * min_interval >= series.interval * (1+(series.index-1)//store_interval) * store_interval) :
				CheckCorrelation(ts_list, interval)
