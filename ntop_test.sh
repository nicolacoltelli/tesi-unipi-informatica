#!/bin/bash

folder="/var/lib/ntopng/2/rrd/"

python3 correlation.py --input $folder --known --store 10 > out.txt

grep "anomaly found" out.txt > anomaly_found.txt
grep "Correlation found" out.txt > correlation_found.txt
grep "continuous" out.txt > continuous.txt
grep "debug" out.txt > debug.txt

rm out.txt