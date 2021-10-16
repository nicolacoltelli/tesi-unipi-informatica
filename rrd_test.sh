#!/bin/bash

cp /var/lib/ntopng/2/rrd/YouTube.rrd ~/Documents/universita/DES/rrd
cp /var/lib/ntopng/2/rrd/l4protos/udp.rrd ~/Documents/universita/DES/rrd
cp /var/lib/ntopng/2/rrd/l4protos/tcp.rrd ~/Documents/universita/DES/rrd
chmod +777 ~/Documents/universita/DES/rrd/YouTube.rrd
chmod +777 ~/Documents/universita/DES/rrd/udp.rrd
chmod +777 ~/Documents/universita/DES/rrd/tcp.rrd
rrdtool fetch ~/Documents/universita/DES/rrd/YouTube.rrd AVERAGE -s -2h | grep -v nan | wc -l
rrdtool fetch ~/Documents/universita/DES/rrd/udp.rrd AVERAGE -s -2h | grep -v nan | wc -l
rrdtool fetch ~/Documents/universita/DES/rrd/tcp.rrd AVERAGE -s -2h | grep -v nan | wc -l