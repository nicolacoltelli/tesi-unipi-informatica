import rrdtool
import matplotlib.pyplot as plt

def converter(tuples):
	list_val = []
	for elem in tuples[2]:
		elem = elem[0]
		list_val.append(elem)
	return list_val

file0 = "./rrd/YouTube.rrd"
tuples0 = rrdtool.fetch(file0, 'AVERAGE', "-s -2h")
list_val0 = converter(tuples0)

file1 = "./rrd/udp.rrd"
tuples1 = rrdtool.fetch(file1, 'AVERAGE', "-s -2h")
list_val1 = converter(tuples1)

file2 = "./rrd/tcp.rrd"
tuples2 = rrdtool.fetch(file2, 'AVERAGE', "-s -2h")
list_val2 = converter(tuples2)

#print(list_val)
#print(list_val[-300:])
#print(tuples[2])
#test = list_val[-1000:]
#print(test)
#for i in range(300):
#	if test[i] == None:
#		count +=1
#print(count)

plt.plot(list_val0, label="YouTube")
plt.plot(list_val1, label="udp")
plt.plot(list_val2, label="tcp")
plt.legend()
plt.show()