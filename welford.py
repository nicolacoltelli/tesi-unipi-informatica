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