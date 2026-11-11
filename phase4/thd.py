import numpy as np
def spectrum(t, v, t0, t1):
    m = (t >= t0 - 1e-9) & (t < t1 - 1e-9)
    x = v[m] - v[m].mean(); N = len(x)
    return np.fft.rfftfreq(N, t[1] - t[0]), np.abs(np.fft.rfft(x)) * 2 / N
def amp_at(f, X, f0):
    i = np.argmin(abs(f - f0)); return X[max(i - 1, 0):i + 2].max()
def thd(t, v, f0, t0, t1, nh=10):
    f, X = spectrum(t, v, t0, t1)
    h = [amp_at(f, X, k * f0) for k in range(1, nh + 1)]
    return np.sqrt(np.sum(np.square(h[1:]))) / h[0], h
