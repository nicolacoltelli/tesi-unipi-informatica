import os
import math
from statistics import mean, pstdev
from functools import reduce

def RoundHalfUp(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier


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


def ScanHost(path, limit=3):
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            if (limit > 0):
                entry_name = os.path.basename(entry.path)
                if (entry_name.isnumeric()):
                    entry_num_name = int(entry_name)
                    if (0 <= entry_num_name and entry_num_name <= 255):
                        yield from ScanHost(entry.path, limit-1)
            else:
                yield entry


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