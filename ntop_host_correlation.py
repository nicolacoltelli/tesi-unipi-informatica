import os
import argparse
from datetime import datetime

from NtopHostTimeSeries import NtopHostTimeSeries, Anomaly
from Host import Host, HostEdge
from welford import update, finalize
from utils import (
	AlignAnomalies,
	CC_Calculator,
	CrossCovariance,
	FindIntervals,
	lcm,
	RoundHalfUp,
	ScanHost,
	ScaledSigmoid,
)

import networkx
import pygraphviz
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import random

max_correlation_score = 200


DEBUG = 0


max_neighborhood = 5
metrics = ["active_flows.rrd", "bytes.rrd", "score.rrd", "total_flows.rrd"]

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str)
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


def CheckCorrelationFromAnomalies(ts_list, time, host_edges):

	current_anomalies = []
	anomalies_count = 0

	# Trying to generate a group of anomalies
	for series in ts_list:
		for anomaly in series.anomalies_to_correlate:

			if (series.index - anomaly.end < max_neighborhood * 2 - 1 and series.finished == False):
				#Waiting because there could be an anomaly ahead still not read.
				continue
			
			wait_unfinished = False
			anomalies_around = []

			for other_series in ts_list:
				if (other_series.host_id == series.host_id):
					continue

				if (len(other_series.anomalies_to_correlate) == 0):
					anomalies_around.append((other_series, None))
					continue
			
				anomalies_in_interval_count = 0
				for other_anomaly in other_series.anomalies_to_correlate:

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

				cc_score = int((cc * 100) - 80)
				if (a1[1] != None):
					cc_score *= 2
				correlation_score = 10 + cc_score

				host0 = a0[0].host_id
				host1 = a1[0].host_id
				for edge in host_edges:
					if ((host0 == edge.host0.id and host1 == edge.host1.id) or (host0 == edge.host1.id and host1 == edge.host0.id)):
						edge.score += correlation_score
						break


def CheckCorrelation(ts_list, host_edges, store_interval):

	series_count = len(ts_list)

	for i in range(series_count):

		series0 = ts_list[i]
		if (series0.finished == True):
			continue
		if (len(series0.sec) < 10 ):
			continue
		
		for j in range(i+1, series_count):

			series1 = ts_list[j]
			if (series1.finished == True):
				continue
			if ( len(series1.sec) < 10):
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

				cc_score = int((avg_cc * 100) - 80)
				correlation_score = store_interval + cc_score

				host0 = series0.host_id
				host1 = series1.host_id
				for edge in host_edges:
					if ((host0 == edge.host0.id and host1 == edge.host1.id) or (host0 == edge.host1.id and host1 == edge.host0.id)):
						edge.score += correlation_score
						break


def DrawHostGraph(host_list, host_edges):

	G = networkx.Graph()

	for host in host_list:
		G.add_node(host.ip)

	for edge in host_edges:

		score = edge.score

		#debug
		#if (random.randint(1,100) <= 40):
		#	score = 0
		#else:
		#	score = random.randint(0, max_correlation_score)

		print(edge.host0.ip + " <===> " + edge.host1.ip + ": " + str(score))
		score = ScaledSigmoid(score, max_correlation_score)

		if (score < 1):
			score = 1

		#print(edge.host0.path + " <===> " + edge.host1.path + ": " + str(score))

		#if (score == 0):
		#	continue

		#if (score > max_correlation_score):
		#	score = max_correlation_score

		#score = max_correlation_score - score
		G.add_edge(edge.host0.ip,edge.host1.ip,len=score)


	pos = graphviz_layout(G)
	#networkx.draw_networkx(G,pos)
	networkx.draw_networkx_nodes(G,pos)
	#networkx.draw_networkx_edges(G,pos)
	networkx.draw_networkx_labels(G,pos)
	plt.show()




if __name__ == "__main__" :

	if (args.input == None):
		print("Error: input path not specified. Use python3 ntop_host_correlation.py --input input_path")
		exit(1)

	host_list = []
	store_interval = args.store

	host_id = 0
	host_edges = []
	
	for entry in ScanHost(args.input):
		
		new_host = Host(entry.path, host_id, store_interval, metrics)
	
		for host in host_list:
			host_edges.append(HostEdge(host, new_host))
	
		host_list.append(new_host)
		host_id += 1

	if (host_id == 0):
		print("Error: no host found in the specified directory.")
		exit(1)

	ts_by_metric = []
	for i in range(len(metrics)):
		ts_by_metric.append([])
		for host in host_list:
			ts_by_metric[i].append(host.GetTimeSeries(metrics[i], "sent"))
			ts_by_metric[i].append(host.GetTimeSeries(metrics[i], "rcvd"))

	time = 0
	host_count = len(host_list)
	while host_count > 0:
		
		for host in host_list:
			for series in host.ts_list:

				if (series.finished):
					continue

				if (time >= series.index):
					if (series.ReadValue()):
						CheckAnomaly(series)
						des(series)
					else:
						host.ts_count -= 1
						if (host.ts_count == 0):
							host_count -= 1

		for ts_group in ts_by_metric:
			CheckCorrelationFromAnomalies(ts_group, time, host_edges)
		
		if ( store_interval - 1  <=  time % store_interval ):
			for ts_group in ts_by_metric:
				CheckCorrelation(ts_group, host_edges, store_interval)

		time += 1

	DrawHostGraph(host_list, host_edges)