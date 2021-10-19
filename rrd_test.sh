#!/bin/bash

mkdir -p ~/Documents/universita/DES/rrd/192/168/1/2/l4protos/
cp /var/lib/ntopng/2/rrd/YouTube.rrd ~/Documents/universita/DES/rrd
cp /var/lib/ntopng/2/rrd/l4protos/udp.rrd ~/Documents/universita/DES/rrd
cp /var/lib/ntopng/2/rrd/l4protos/tcp.rrd ~/Documents/universita/DES/rrd
cp /var/lib/ntopng/2/rrd/192/168/1/2/l4protos/tcp.rrd ~/Documents/universita/DES/rrd/192/168/1/2/l4protos
chmod +777 ~/Documents/universita/DES/rrd/YouTube.rrd
chmod +777 ~/Documents/universita/DES/rrd/udp.rrd
chmod +777 ~/Documents/universita/DES/rrd/tcp.rrd
chmod +777 ~/Documents/universita/DES/rrd/192/168/1/2/l4protos/tcp.rrd
rrdtool fetch ~/Documents/universita/DES/rrd/YouTube.rrd AVERAGE -s -2h | grep -v nan | wc -l
rrdtool fetch ~/Documents/universita/DES/rrd/udp.rrd AVERAGE -s -2h | grep -v nan | wc -l
rrdtool fetch ~/Documents/universita/DES/rrd/tcp.rrd AVERAGE -s -2h | grep -v nan | wc -l
rrdtool fetch ~/Documents/universita/DES/rrd/192/168/1/2/l4protos/tcp.rrd AVERAGE -s -2h | grep -v nan | wc -l