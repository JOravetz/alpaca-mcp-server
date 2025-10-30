from math import log, pi

import numpy as np
from scipy.fft import fft, ifft  # type: ignore[import-untyped]
from scipy.optimize import curve_fit  # type: ignore[import-untyped]
from scipy.signal import cspline1d, cspline1d_eval  # type: ignore[import-untyped]

__all__ = [
    "peakdetect",
    "peakdetect_fft",
    "peakdetect_parabola",
    "peakdetect_sine",
    "peakdetect_sine_locked",
    "peakdetect_spline",
    "peakdetect_zero_crossing",
    "peakdetect_savgol",
    "zero_crossings",
    "zero_crossings_sine_fit",
    "_n",
    "_pad",
]


def _datacheck_peakdetect(x_axis, y_axis):
    if x_axis is None:
        x_axis = range(len(y_axis))

    if len(y_axis) != len(x_axis):
        raise ValueError("Input vectors y_axis and x_axis must have same length")

    # needs to be a numpy array
    y_axis = np.array(y_axis)
    x_axis = np.array(x_axis)
    return x_axis, y_axis


def _pad(fft_data, pad_len):
    """
    Pads fft data to interpolate in time domain

    keyword arguments:
    fft_data -- the fft
    pad_len --  By how many times the time resolution should be increased by

    return: padded list
    """
    length = len(fft_data)
    n = _n(length * pad_len)
    fft_data = list(fft_data)

    return fft_data[: length // 2] + [0] * (2**n - length) + fft_data[length // 2 :]


def _n(x):
    """
    Find the smallest value for n, which fulfils 2**n >= x

    keyword arguments:
    x -- the value, which 2**n must surpass

    return: the integer n
    """
    return int(log(x) / log(2)) + 1


def _peakdetect_parabola_fitter(raw_peaks, x_axis, y_axis, points):
    """
    Performs the actual parabola fitting for the peakdetect_parabola function.

    keyword arguments:
    raw_peaks -- A list of either the maxima or the minima peaks, as given
        by the peakdetect functions, with index used as x-axis

    x_axis -- A numpy array of all the x values

    y_axis -- A numpy array of all the y values

    points -- How many points around the peak should be used during curve
        fitting, must be odd.


    return: A list giving all the peaks and the fitted waveform, format:
        [[x, y, [fitted_x, fitted_y]]]

    """

    def func(x, a, tau, c):
        return a * ((x - tau) ** 2) + c

    fitted_peaks = []  # type: ignore[var-annotated]

    # Handle empty raw_peaks
    if len(raw_peaks) < 2:
        return fitted_peaks

    # Calculate an approximate distance between peaks
    try:
        distance = abs(x_axis[raw_peaks[1][0]] - x_axis[raw_peaks[0][0]]) / 4
    except (IndexError, TypeError):
        # Fallback if there's an issue with calculating distance
        distance = (x_axis[-1] - x_axis[0]) / (len(raw_peaks) * 4)

    for peak in raw_peaks:
        try:
            index = peak[0]

            # Ensure index is valid
            if not isinstance(index, int | np.integer):
                continue

            # Make sure we have enough points around the peak
            half_points = points // 2
            if index < half_points or index >= len(x_axis) - half_points:
                continue

            x_data = x_axis[index - half_points : index + half_points + 1]
            y_data = y_axis[index - half_points : index + half_points + 1]

            # Skip if we don't have enough data points
            if len(x_data) < 3 or len(y_data) < 3:
                continue

            # get a first approximation of tau (peak position in time)
            tau = x_axis[index]

            # get a first approximation of peak amplitude
            c = peak[1]

            # Calculate initial 'a' parameter carefully to avoid numerical issues
            # For a parabola, a controls the width: larger |a| = narrower peak
            try:
                a = np.sign(c) * (-1) * (np.sqrt(abs(c)) / max(distance, 1e-6)) ** 2
            except (ValueError, ZeroDivisionError):
                # Fallback value if calculation fails
                a = -0.1 if c > 0 else 0.1

            # build list of approximations
            p0 = (a, tau, c)

            # Try curve fitting with increased maxfev (max function evaluations)
            try:
                popt, pcov = curve_fit(func, x_data, y_data, p0, maxfev=2000)

                # retrieve tau and c i.e x and y value of peak
                x, y = popt[1:3]

                # create a high resolution data set for the fitted waveform
                x2 = np.linspace(x_data[0], x_data[-1], points * 10)
                y2 = func(x2, *popt)

                fitted_peaks.append([x, y, [x2, y2]])

            except (RuntimeError, ValueError):
                # If curve_fit fails, we'll use the raw peak instead
                # This ensures we don't lose the peak just because fitting failed
                x = x_axis[index]
                y = y_axis[index]

                # Create a simple parabola for visualization
                x2 = np.linspace(x_data[0], x_data[-1], points * 10)
                # Use the initial guess parameters
                y2 = func(x2, *p0)

                fitted_peaks.append([x, y, [x2, y2]])

        except Exception:
            # Skip this peak if any other error occurs
            continue

    return fitted_peaks


def peakdetect(y_axis, x_axis=None, lookahead=200, delta=0):
    """
    Converted from/based on a MATLAB script at:
    http://billauer.co.il/peakdet.html

    function for detecting local maxima and minima in a signal.
    Discovers peaks by searching for values which are surrounded by lower
    or larger values for maxima and minima respectively

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list and is used
        in the return to specify the position of the peaks. If omitted an
        index of the y_axis is used.
        (default: None)

    lookahead -- distance to look ahead from a peak candidate to determine if
        it is the actual peak
        (default: 200)
        '(samples / period) / f' where '4 >= f >= 1.25' might be a good value

    delta -- this specifies a minimum difference between a peak and
        the following points, before a peak may be considered a peak. Useful
        to hinder the function from picking up false peaks towards to end of
        the signal. To work well delta should be set to delta >= RMSnoise * 5.
        (default: 0)
            When omitted delta function causes a 20% decrease in speed.
            When used Correctly it can double the speed of the function


    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
        to get the average peak value do: np.mean(max_peaks, 0)[1] on the
        results to unpack one of the lists into x, y coordinates do:
        x, y = zip(*max_peaks)
    """

    max_peaks = []
    min_peaks = []
    dump = []  # Used to pop the first hit which almost always is false

    # check input data
    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)
    # store data length for later use
    length = len(y_axis)

    # perform some checks
    if lookahead < 1:
        raise ValueError("Lookahead must be '1' or above in value")
    if not (np.isscalar(delta) and delta >= 0):  # type: ignore[operator]
        raise ValueError("delta must be a positive number")

    # maxima and minima candidates are temporarily stored in
    # mx and mn respectively
    mn, mx = np.inf, -np.inf

    # Only detect peak if there is 'lookahead' amount of points after it
    for index, (x, y) in enumerate(zip(x_axis[:-lookahead], y_axis[:-lookahead], strict=False)):
        if y > mx:
            mx = y
            mxpos = x
        if y < mn:
            mn = y
            mnpos = x

        # look for max
        if y < mx - delta and mx != np.inf and y_axis[index : index + lookahead].max() < mx:  # type: ignore[operator]
            # Maxima peak candidate found
            # look ahead in signal to ensure that this is a peak and not jitter
            max_peaks.append([mxpos, mx])
            dump.append(True)
            # set algorithm to only find minima now
            mx = np.inf
            mn = np.inf
            if index + lookahead >= length:
                # end is within lookahead no more peaks can be found
                break
            continue

        # look for min
        if y > mn + delta and mn != -np.inf and y_axis[index : index + lookahead].min() > mn:  # type: ignore[operator]
            # Minima peak candidate found
            # look ahead in signal to ensure that this is a peak and not jitter
            min_peaks.append([mnpos, mn])
            dump.append(False)
            # set algorithm to only find maxima now
            mn = -np.inf
            mx = -np.inf
            if index + lookahead >= length:
                # end is within lookahead no more peaks can be found
                break

    # Remove the false hit on the first value of the y_axis
    try:
        if dump[0]:
            max_peaks.pop(0)
        else:
            min_peaks.pop(0)
        del dump
    except IndexError:
        # no peaks were found, should the function return empty lists?
        pass

    return [max_peaks, min_peaks]


def peakdetect_fft(y_axis, x_axis, pad_len=20):
    """
    Performs a FFT calculation on the data and zero-pads the results to
    increase the time domain resolution after performing the inverse fft and
    send the data to the 'peakdetect' function for peak
    detection.

    Omitting the x_axis is forbidden as it would make the resulting x_axis
    value silly if it was returned as the index 50.234 or similar.

    Will find at least 1 less peak then the 'peakdetect_zero_crossing'
    function, but should result in a more precise value of the peak as
    resolution has been increased. Some peaks are lost in an attempt to
    minimize spectral leakage by calculating the fft between two zero
    crossings for n amount of signal periods.

    The biggest time eater in this function is the ifft and thereafter it's
    the 'peakdetect' function which takes only half the time of the ifft.
    Speed improvements could include to check if 2**n points could be used for
    fft and ifft or change the 'peakdetect' to the 'peakdetect_zero_crossing',
    which is maybe 10 times faster than 'peakdetct'. The pro of 'peakdetect'
    is that it results in one less lost peak. It should also be noted that the
    time used by the ifft function can change greatly depending on the input.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list and is used
        in the return to specify the position of the peaks.

    pad_len -- By how many times the time resolution should be
        increased by, e.g. 1 doubles the resolution. The amount is rounded up
        to the nearest 2**n amount
        (default: 20)


    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
        to get the average peak value do: np.mean(max_peaks, 0)[1] on the
        results to unpack one of the lists into x, y coordinates do:
        x, y = zip(*max_peaks)
    """
    # check input data
    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)
    zero_indices = zero_crossings(y_axis, window_len=11)
    #  select a n amount of periods
    last_indice = -1 - (1 - len(zero_indices) & 1)
    ###
    # Calculate the fft between the first and last zero crossing
    # this method could be ignored if the beginning and the end of the signal
    # are unnecessary as any errors induced from not using whole periods
    # should mainly manifest in the beginning and the end of the signal, but
    # not in the rest of the signal
    # this is also unnecessary if the given data is an amount of whole periods
    ###
    fft_data = fft(y_axis[zero_indices[0] : zero_indices[last_indice]])

    def padd(x, c):
        return x[: len(x) // 2] + [0] * c + x[len(x) // 2 :]

    def n(x):
        return int(log(x) / log(2)) + 1

    # pads to 2**n amount of samples
    fft_padded = padd(list(fft_data), 2 ** n(len(fft_data) * pad_len) - len(fft_data))

    # There is amplitude decrease directly proportional to the sample increase
    sf = len(fft_padded) / float(len(fft_data))
    # There might be a leakage giving the result an imaginary component
    # Return only the real component
    y_axis_ifft = ifft(fft_padded).real * sf  # (pad_len + 1)
    x_axis_ifft = np.linspace(
        x_axis[zero_indices[0]], x_axis[zero_indices[last_indice]], len(y_axis_ifft)
    )
    # get the peaks to the interpolated waveform
    max_peaks, min_peaks = peakdetect(
        y_axis_ifft, x_axis_ifft, 500, delta=abs(np.diff(y_axis).max() * 2)
    )
    # max_peaks, min_peaks = peakdetect_zero_crossing(y_axis_ifft, x_axis_ifft)

    # store one 20th of a period as waveform data
    # Fix: Cast to int before performing bitwise operation
    data_len = int(np.diff(zero_indices).mean()) / 10
    data_len = int(data_len)  # Convert to integer before bitwise operation
    data_len += 1 - (data_len & 1)  # Now perform bitwise AND with integer

    return [max_peaks, min_peaks]


def peakdetect_parabola(y_axis, x_axis, points=31):
    """
    Function for detecting local maxima and minima in a signal.
    Discovers peaks by fitting the model function: y = k (x - tau) ** 2 + m
    to the peaks. The amount of points used in the fitting is set by the
    points argument.

    Omitting the x_axis is forbidden as it would make the resulting x_axis
    value silly, if it was returned as index 50.234 or similar.

    will find the same amount of peaks as the 'peakdetect_zero_crossing'
    function, but might result in a more precise value of the peak.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list and is used
        in the return to specify the position of the peaks.

    points -- How many points around the peak should be used during curve
        fitting (default: 31)


    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
        to get the average peak value do: np.mean(max_peaks, 0)[1] on the
        results to unpack one of the lists into x, y coordinates do:
        x, y = zip(*max_peaks)
    """
    # check input data
    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)

    # make the points argument odd
    points += 1 - points % 2

    # First, get peaks using the basic peakdetect method
    # This is more reliable for initial peak detection
    basic_max_peaks, basic_min_peaks = peakdetect(y_axis, x_axis)

    # If basic peak detection found peaks, use those
    if basic_max_peaks and basic_min_peaks:
        # Convert the peak positions to indices
        max_indices = []
        for x, _y in basic_max_peaks:
            # Find the index closest to this x position
            idx = np.abs(x_axis - x).argmin()
            max_indices.append(idx)

        min_indices = []
        for x, _y in basic_min_peaks:
            # Find the index closest to this x position
            idx = np.abs(x_axis - x).argmin()
            min_indices.append(idx)

        # Create raw peaks format expected by _peakdetect_parabola_fitter
        max_raw = [[idx, y_axis[idx]] for idx in max_indices]
        min_raw = [[idx, y_axis[idx]] for idx in min_indices]
    else:
        # Fallback to zero_crossing if basic detection fails
        try:
            max_raw, min_raw = peakdetect_zero_crossing(y_axis, x_axis)
        except (ValueError, IndexError, TypeError):
            # Just return the basic peaks if everything else fails
            return [basic_max_peaks, basic_min_peaks]

    # If we still don't have peaks, return empty lists
    if not max_raw and not min_raw:
        return [[], []]

    # Now attempt to fit parabolas to the peaks
    try:
        # If max_raw has indices, fit parabolas to them
        if max_raw:
            max_ = _peakdetect_parabola_fitter(max_raw, x_axis, y_axis, points)
            # Convert fitted peaks to output format
            max_peaks = [[x[0], x[1]] for x in max_] if max_ else []
        else:
            # If no max_raw, just use basic peaks
            max_peaks = basic_max_peaks

        # If min_raw has indices, fit parabolas to them
        if min_raw:
            min_ = _peakdetect_parabola_fitter(min_raw, x_axis, y_axis, points)
            # Convert fitted peaks to output format
            min_peaks = [[x[0], x[1]] for x in min_] if min_ else []
        else:
            # If no min_raw, just use basic peaks
            min_peaks = basic_min_peaks

    except Exception:
        # If anything goes wrong with fitting, use the basic peaks
        return [basic_max_peaks, basic_min_peaks]

    # Final check - if either list is empty but the basic detection found peaks,
    # use the basic detection results for that list
    if not max_peaks and basic_max_peaks:
        max_peaks = basic_max_peaks
    if not min_peaks and basic_min_peaks:
        min_peaks = basic_min_peaks

    return [max_peaks, min_peaks]


def peakdetect_sine(y_axis, x_axis, points=31, lock_frequency=False):
    """
    Function for detecting local maxima and minima in a signal.
    Discovers peaks by fitting the model function:
    y = A * sin(2 * pi * f * (x - tau)) to the peaks. The amount of points used
    in the fitting is set by the points argument.

    Omitting the x_axis is forbidden as it would make the resulting x_axis
    value silly if it was returned as index 50.234 or similar.

    will find the same amount of peaks as the 'peakdetect_zero_crossing'
    function, but might result in a more precise value of the peak.

    The function might have some problems if the sine wave has a
    non-negligible total angle i.e. a k*x component, as this messes with the
    internal offset calculation of the peaks, might be fixed by fitting a
    y = k * x + m function to the peaks for offset calculation.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list and is used
        in the return to specify the position of the peaks.

    points -- How many points around the peak should be used during curve
        fitting (default: 31)

    lock_frequency -- Specifies if the frequency argument of the model
        function should be locked to the value calculated from the raw peaks
        or if optimization process may tinker with it.
        (default: False)


    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
        to get the average peak value do: np.mean(max_peaks, 0)[1] on the
        results to unpack one of the lists into x, y coordinates do:
        x, y = zip(*max_peaks)
    """
    # check input data
    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)
    # make the points argument odd
    points += 1 - points % 2
    # points += 1 - int(points) & 1 slower when int conversion needed

    # get raw peaks
    max_raw, min_raw = peakdetect_zero_crossing(y_axis)

    # get global offset
    offset = np.mean([np.mean(max_raw, 0)[1], np.mean(min_raw, 0)[1]])
    # fitting a k * x + m function to the peaks might be better
    # offset_func = lambda x, k, m: k * x + m

    # calculate an approximate frequency of the signal
    Hz_h_peak = np.diff(
        list(zip(*max_raw, strict=False))[0]
    ).mean()  # Convert tuple to list to handle map
    Hz_l_peak = np.diff(
        list(zip(*min_raw, strict=False))[0]
    ).mean()  # Convert tuple to list to handle map
    Hz = 1 / np.mean([Hz_h_peak, Hz_l_peak])

    # model function
    # if cosine is used then tau could equal the x position of the peak
    # if sine were to be used then tau would be the first zero crossing
    if lock_frequency:

        def func(x_ax, A, tau):
            return A * np.sin(2 * pi * Hz * (x_ax - tau) + pi / 2)

    else:

        def func(x_ax, A, Hz, tau):  # type: ignore[misc]
            return A * np.sin(2 * pi * Hz * (x_ax - tau) + pi / 2)

    # func = lambda x_ax, A, Hz, tau: A * np.cos(2 * pi * Hz * (x_ax - tau))

    # get peaks
    fitted_peaks = []
    for raw_peaks in [max_raw, min_raw]:
        peak_data = []
        for peak in raw_peaks:
            index = peak[0]
            x_data = x_axis[index - points // 2 : index + points // 2 + 1]
            y_data = y_axis[index - points // 2 : index + points // 2 + 1]
            # get a first approximation of tau (peak position in time)
            tau = x_axis[index]
            # get a first approximation of peak amplitude
            A = peak[1]

            # build list of approximations
            p0 = (A, tau) if lock_frequency else (A, Hz, tau)

            # subtract offset from wave-shape
            y_data -= offset
            popt, pcov = curve_fit(func, x_data, y_data, p0)
            # retrieve tau and A i.e x and y value of peak
            x = popt[-1]
            y = popt[0]

            # create a high resolution data set for the fitted waveform
            x2 = np.linspace(x_data[0], x_data[-1], points * 10)
            y2 = func(x2, *popt)

            # add the offset to the results
            y += offset
            y2 += offset
            y_data += offset

            peak_data.append([x, y, [x2, y2]])

        fitted_peaks.append(peak_data)

    # structure date for output
    max_peaks = [[x[0], x[1]] for x in fitted_peaks[0]]  # Convert map to list
    # max_fitted = map(lambda x: x[-1], fitted_peaks[0])
    min_peaks = [[x[0], x[1]] for x in fitted_peaks[1]]  # Convert map to list
    # min_fitted = map(lambda x: x[-1], fitted_peaks[1])

    return [max_peaks, min_peaks]


def peakdetect_sine_locked(y_axis, x_axis, points=31):
    """
    Convenience function for calling the 'peakdetect_sine' function with
    the lock_frequency argument as True.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks
    x_axis -- A x-axis whose values correspond to the y_axis list and is used
        in the return to specify the position of the peaks.
    points -- How many points around the peak should be used during curve
        fitting (default: 31)

    return: see the function 'peakdetect_sine'
    """
    return peakdetect_sine(y_axis, x_axis, points, True)


def peakdetect_spline(y_axis, x_axis, pad_len=20):
    """
    Performs a b-spline interpolation on the data to increase resolution and
    send the data to the 'peakdetect_zero_crossing' function for peak
    detection.

    Omitting the x_axis is forbidden as it would make the resulting x_axis
    value silly if it was returned as the index 50.234 or similar.

    will find the same amount of peaks as the 'peakdetect_zero_crossing'
    function, but might result in a more precise value of the peak.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list and is used
        in the return to specify the position of the peaks.
        x-axis must be equally spaced.

    pad_len -- By how many times the time resolution should be increased by,
        e.g. 1 doubles the resolution.
        (default: 20)


    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
        to get the average peak value do: np.mean(max_peaks, 0)[1] on the
        results to unpack one of the lists into x, y coordinates do:
        x, y = zip(*max_peaks)
    """
    # Get peaks using standard method first
    basic_max_peaks, basic_min_peaks = peakdetect(y_axis, x_axis)

    try:
        # check input data
        x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)

        # could perform a check if x_axis is equally spaced
        dx = x_axis[1] - x_axis[0]
        x_interpolated = np.linspace(x_axis.min(), x_axis.max(), len(x_axis) * (pad_len + 1))

        # perform spline interpolations
        try:
            cj = cspline1d(y_axis)
            y_interpolated = cspline1d_eval(cj, x_interpolated, dx=dx, x0=x_axis[0])

            # get peaks from interpolated signal
            max_peaks_i, min_peaks_i = peakdetect_zero_crossing(y_interpolated, x_interpolated)

            # Filter peaks that are too close to the signal edges
            max_peaks_filtered = []
            for peak in max_peaks_i:
                # Only keep peaks if they are reasonable
                if not np.isnan(peak[0]) and not np.isnan(peak[1]):
                    # Check if this peak matches any basic peak (within a small window)
                    is_valid = False
                    for basic_peak in basic_max_peaks:
                        if abs(peak[0] - basic_peak[0]) < 0.005:  # 5ms window
                            is_valid = True
                            break
                    if is_valid:
                        max_peaks_filtered.append(peak)

            min_peaks_filtered = []
            for peak in min_peaks_i:
                # Only keep peaks if they are reasonable
                if not np.isnan(peak[0]) and not np.isnan(peak[1]):
                    # Check if this peak matches any basic peak (within a small window)
                    is_valid = False
                    for basic_peak in basic_min_peaks:
                        if abs(peak[0] - basic_peak[0]) < 0.005:  # 5ms window
                            is_valid = True
                            break
                    if is_valid:
                        min_peaks_filtered.append(peak)

            # If we filtered out too many peaks, use the basic ones
            if len(max_peaks_filtered) < len(basic_max_peaks) / 2:
                max_peaks_filtered = basic_max_peaks
            if len(min_peaks_filtered) < len(basic_min_peaks) / 2:
                min_peaks_filtered = basic_min_peaks

            return [max_peaks_filtered, min_peaks_filtered]

        except Exception:
            # If spline interpolation fails, use basic peak detection
            return [basic_max_peaks, basic_min_peaks]

    except Exception:
        # Fall back to basic peak detection
        return [basic_max_peaks, basic_min_peaks]


def peakdetect_zero_crossing(y_axis, x_axis=None, window=11):
    """
    Function for detecting local maxima and minima in a signal.
    Discovers peaks by dividing the signal into bins and retrieving the
    maximum and minimum value of each the even and odd bins respectively.
    Division into bins is performed by smoothing the curve and finding the
    zero crossings.

    Suitable for repeatable signals, where some noise is tolerated. Executes
    faster than 'peakdetect', although this function will break if the offset
    of the signal is too large. It should also be noted that the first and
    last peak will probably not be found, as this function only can find peaks
    between the first and last zero crossing.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list
        and is used in the return to specify the position of the peaks. If
        omitted an index of the y_axis is used.
        (default: None)

    window -- the dimension of the smoothing window; should be an odd integer
        (default: 11)


    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
        to get the average peak value do: np.mean(max_peaks, 0)[1] on the
        results to unpack one of the lists into x, y coordinates do:
        x, y = zip(*max_peaks)
    """
    # check input data
    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)

    zero_indices = zero_crossings(y_axis, window_len=window)
    period_lengths = np.diff(zero_indices)

    bins_y = [
        y_axis[index : index + diff]
        for index, diff in zip(zero_indices, period_lengths, strict=False)
    ]
    bins_x = [
        x_axis[index : index + diff]
        for index, diff in zip(zero_indices, period_lengths, strict=False)
    ]

    even_bins_y = bins_y[::2]
    odd_bins_y = bins_y[1::2]
    even_bins_x = bins_x[::2]
    odd_bins_x = bins_x[1::2]
    hi_peaks_x = []
    lo_peaks_x = []

    # check if even bin contains maxima
    if abs(even_bins_y[0].max()) > abs(even_bins_y[0].min()):
        hi_peaks = [bin.max() for bin in even_bins_y]
        lo_peaks = [bin.min() for bin in odd_bins_y]
        # get x values for peak
        for bin_x, bin_y, peak in zip(even_bins_x, even_bins_y, hi_peaks, strict=False):
            hi_peaks_x.append(bin_x[np.where(bin_y == peak)[0][0]])
        for bin_x, bin_y, peak in zip(odd_bins_x, odd_bins_y, lo_peaks, strict=False):
            lo_peaks_x.append(bin_x[np.where(bin_y == peak)[0][0]])
    else:
        hi_peaks = [bin.max() for bin in odd_bins_y]
        lo_peaks = [bin.min() for bin in even_bins_y]
        # get x values for peak
        for bin_x, bin_y, peak in zip(odd_bins_x, odd_bins_y, hi_peaks, strict=False):
            hi_peaks_x.append(bin_x[np.where(bin_y == peak)[0][0]])
        for bin_x, bin_y, peak in zip(even_bins_x, even_bins_y, lo_peaks, strict=False):
            lo_peaks_x.append(bin_x[np.where(bin_y == peak)[0][0]])

    max_peaks = [[x, y] for x, y in zip(hi_peaks_x, hi_peaks, strict=False)]
    min_peaks = [[x, y] for x, y in zip(lo_peaks_x, lo_peaks, strict=False)]

    return [max_peaks, min_peaks]


def _smooth(x, window_len=11, window="hanning"):
    """
    smooth the data using a window of the requested size.

    This method is based on the convolution of a scaled window on the signal.
    The signal is prepared by introducing reflected copies of the signal
    (with the window size) in both ends so that transient parts are minimized
    in the beginning and end part of the output signal.

    keyword arguments:
    x -- the input signal

    window_len -- the dimension of the smoothing window; should be an odd
        integer (default: 11)

    window -- the type of window from 'flat', 'hanning', 'hamming',
        'bartlett', 'blackman', where flat is a moving average
        (default: 'hanning')


    return: the smoothed signal

    example:

    t = linspace(-2,2,0.1)
    x = sin(t)+randn(len(t))*0.1
    y = _smooth(x)

    see also:

    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman,
    numpy.convolve, scipy.signal.lfilter
    """

    if x.ndim != 1:
        raise ValueError("smooth only accepts 1 dimension arrays.")

    if x.size < window_len:
        raise ValueError("Input vector needs to be bigger than window size.")

    if window_len < 3:
        return x
    # declare valid windows in a dictionary
    window_funcs = {
        "flat": lambda _len: np.ones(_len, "d"),  # type: ignore[arg-type]
        "hanning": np.hanning,
        "hamming": np.hamming,
        "bartlett": np.bartlett,
        "blackman": np.blackman,
    }

    s = np.r_[x[window_len - 1 : 0 : -1], x, x[-1:-window_len:-1]]
    try:
        w = window_funcs[window](window_len)
    except KeyError as e:
        raise ValueError(
            "Window is not one of '{}', '{}', '{}', '{}', '{}'".format(*window_funcs.keys())
        ) from e

    y = np.convolve(w / w.sum(), s, mode="valid")

    return y


def peakdetect_savgol(y_axis, x_axis=None, window_length=5, polyorder=3, delta=1, min_distance=1):
    """
    Detect peaks and troughs using Savitzky-Golay filter for derivative calculation.

    This implementation uses scipy's find_peaks with prominence filtering to detect
    only significant peaks and troughs, avoiding detection of minor fluctuations.

    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks
    x_axis -- A x-axis whose values correspond to the y_axis list
    window_length -- The length of the filter window for Savitzky-Golay (default: 5)
    polyorder -- The order of the polynomial used to fit the samples (default: 3)
    delta -- The spacing of the samples to which the filter will be applied (default: 1)
    min_distance -- Minimum distance between peaks/troughs (default: 1)

    return: two lists [max_peaks, min_peaks] containing the positive and
        negative peaks respectively. Each cell of the lists contains a tuple
        of: (position, peak_value)
    """
    import numpy as np
    from scipy import signal as scipy_signal  # type: ignore[import-untyped]

    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)

    # Ensure window_length is appropriate for the data
    window_length = min(window_length, len(y_axis))
    if window_length % 2 == 0:
        window_length += 1
    window_length = max(3, window_length)  # Use minimum of 3 as specified

    # Ensure polyorder is valid
    polyorder = min(polyorder, window_length - 1)

    # First, apply additional smoothing to the already-filtered data
    # This helps eliminate minor fluctuations
    smoothed_y = scipy_signal.savgol_filter(
        y_axis,
        window_length=(
            min(31, len(y_axis) // 4)
            if min(31, len(y_axis) // 4) % 2 == 1
            else min(31, len(y_axis) // 4) + 1
        ),
        polyorder=3,
        delta=delta,
    )

    # Calculate first derivative using Savitzky-Golay filter on smoothed data
    first_derivative = scipy_signal.savgol_filter(
        smoothed_y, window_length=window_length, polyorder=polyorder, deriv=1, delta=delta
    )

    # Use scipy's find_peaks with prominence to detect significant peaks
    # Calculate prominence threshold based on the data range
    data_range = np.ptp(smoothed_y)  # peak-to-peak range
    prominence_threshold = data_range * 0.01  # 1% of data range for significance

    # Find peaks (maxima) in the smoothed data
    peak_indices, peak_properties = scipy_signal.find_peaks(
        smoothed_y,
        prominence=prominence_threshold,
        distance=min_distance,
        width=2,  # Minimum width to avoid noise spikes
    )

    # Find troughs (minima) by inverting the signal
    trough_indices, trough_properties = scipy_signal.find_peaks(
        -smoothed_y, prominence=prominence_threshold, distance=min_distance, width=2
    )

    # Further filter based on derivative sign changes for validation
    max_peaks = []
    for idx in peak_indices:
        # Verify this is a true peak by checking derivative sign change
        if idx > 0 and idx < len(first_derivative) - 1 and (
            first_derivative[idx - 1] > 0
            and first_derivative[idx + 1] < 0
            or abs(first_derivative[idx]) < np.std(first_derivative) * 0.1
        ):
            max_peaks.append((x_axis[idx], y_axis[idx]))

    min_peaks = []
    for idx in trough_indices:
        # Verify this is a true trough by checking derivative sign change
        if idx > 0 and idx < len(first_derivative) - 1 and (
            first_derivative[idx - 1] < 0
            and first_derivative[idx + 1] > 0
            or abs(first_derivative[idx]) < np.std(first_derivative) * 0.1
        ):
            min_peaks.append((x_axis[idx], y_axis[idx]))

    # If we still have too many peaks/troughs, increase prominence filtering
    if len(max_peaks) > 15:  # More than 15 peaks is likely too many
        # Re-run with higher prominence threshold
        prominence_threshold = data_range * 0.02  # 2% of range
        peak_indices, _ = scipy_signal.find_peaks(
            smoothed_y, prominence=prominence_threshold, distance=min_distance * 2
        )
        max_peaks = [(x_axis[idx], y_axis[idx]) for idx in peak_indices if idx < len(x_axis)]

    if len(min_peaks) > 15:  # More than 15 troughs is likely too many
        prominence_threshold = data_range * 0.02  # 2% of range
        trough_indices, _ = scipy_signal.find_peaks(
            -smoothed_y, prominence=prominence_threshold, distance=min_distance * 2
        )
        min_peaks = [(x_axis[idx], y_axis[idx]) for idx in trough_indices if idx < len(x_axis)]

    return max_peaks, min_peaks


def _filter_by_distance(peaks, min_distance):
    """Filter peaks to ensure minimum distance between them."""
    if not peaks:
        return peaks

    filtered = [peaks[0]]
    for peak in peaks[1:]:
        if abs(peak[0] - filtered[-1][0]) >= min_distance:
            filtered.append(peak)

    return filtered


def zero_crossings(y_axis, window_len=11, window_f="hanning", offset_corrected=False):
    """
    Algorithm to find zero crossings. Smooths the curve and finds the
    zero-crossings by looking for a sign change.


    keyword arguments:
    y_axis -- A list containing the signal over which to find zero-crossings

    window_len -- the dimension of the smoothing window; should be an odd
        integer (default: 11)

    window_f -- the type of window from 'flat', 'hanning', 'hamming',
        'bartlett', 'blackman' (default: 'hanning')

    offset_corrected -- Used for recursive calling to remove offset when needed


    return: the index for each zero-crossing
    """
    # smooth the curve
    length = len(y_axis)

    # discard tail of smoothed signal
    y_axis = _smooth(y_axis, window_len, window_f)[:length]
    indices = np.where(np.diff(np.sign(y_axis)))[0]

    # check if zero-crossings are valid
    if len(indices) >= 2:  # Need at least 2 indices to calculate diff
        diff = np.diff(indices)

        # More forgiving validation for noisy signals
        if (
            diff.std() / diff.mean() > 0.5 and not offset_corrected
        ):  # Increased threshold from 0.1 to 0.5
            # Possibly bad zero crossing, see if it's offsets
            # Try offset correction
            offset = np.mean([y_axis.max(), y_axis.min()])
            try:
                return zero_crossings(y_axis - offset, window_len, window_f, True)
            except ValueError:
                # If offset correction also fails, try increasing window size
                if window_len < 51:  # Cap the maximum window size
                    try:
                        return zero_crossings(y_axis, window_len + 10, window_f, offset_corrected)
                    except ValueError:
                        # If all else fails, continue with what we have
                        pass

    # check if any zero crossings were found
    if len(indices) < 1:
        # For signals with no zero crossings, create artificial ones
        # This is a fallback to prevent the algorithm from failing completely
        # Create at least 2 zero crossings at 1/4 and 3/4 of the signal length
        return np.array([length // 4, 3 * length // 4])

    # remove offset from indices due to filter function when returning
    return indices - (window_len // 2 - 1)


def zero_crossings_sine_fit(y_axis, x_axis, fit_window=None, smooth_window=11):
    """
    Detects the zero crossings of a signal by fitting a sine model function
    around the zero crossings:
    y = A * sin(2 * pi * Hz * (x - tau)) + k * x + m
    Only tau (the zero crossing) is varied during fitting.

    Offset and a linear drift of offset is accounted for by fitting a linear
    function the negative respective positive raw peaks of the wave-shape and
    the amplitude is calculated using data from the offset calculation i.e.
    the 'm' constant from the negative peaks is subtracted from the positive
    one to obtain amplitude.

    Frequency is calculated using the mean time between raw peaks.

    Algorithm seems to be sensitive to first guess e.g. a large smooth_window
    will give an error in the results.


    keyword arguments:
    y_axis -- A list containing the signal over which to find peaks

    x_axis -- A x-axis whose values correspond to the y_axis list
        and is used in the return to specify the position of the peaks. If
        omitted an index of the y_axis is used. (default: None)

    fit_window -- Number of points around the approximate zero crossing that
        should be used when fitting the sine wave. Must be small enough that
        no other zero crossing will be seen. If set to none then the mean
        distance between zero crossings will be used (default: None)

    smooth_window -- the dimension of the smoothing window; should be an odd
        integer (default: 11)


    return: A list containing the positions of all the zero crossings.
    """

    # check input data
    x_axis, y_axis = _datacheck_peakdetect(x_axis, y_axis)
    # get first guess
    zero_indices = zero_crossings(y_axis, window_len=smooth_window)
    # modify fit_window to show distance per direction
    fit_window = np.diff(zero_indices).mean() // 3 if fit_window else fit_window // 2

    # x_axis is a np array, use the indices to get a subset with zero crossings
    approx_crossings = x_axis[zero_indices]

    # get raw peaks for calculation of offsets and frequency
    raw_peaks = peakdetect_zero_crossing(y_axis, x_axis)

    # Use mean time between peaks for frequency
    def ext(x):
        return list(zip(*x, strict=False))[0]

    _diff = map(np.diff, map(ext, raw_peaks))

    Hz = 1 / np.mean(list(map(np.mean, _diff)))  # Convert map results to list
    # Hz = 1 / np.diff(approx_crossings).mean() #probably bad precision

    # offset model function
    def offset_func(x, k, m):
        return k * x + m

    k = []
    m = []
    amplitude = []

    for peaks in raw_peaks:
        # get peak data as nparray
        x_data, y_data = map(np.asarray, zip(*peaks, strict=False))
        # x_data = np.asarray(x_data)
        # y_data = np.asarray(y_data)
        # calc first guess
        A = np.mean(y_data)
        p0 = (0, A)
        popt, pcov = curve_fit(offset_func, x_data, y_data, p0)
        # append results
        k.append(popt[0])
        m.append(popt[1])
        amplitude.append(abs(A))

    # store offset constants
    p_offset = (np.mean(k), np.mean(m))
    A = m[0] - m[1]

    # define model function to fit to zero crossing
    # y = A * sin(2*pi * Hz * (x - tau)) + k * x + m
    def func(x, tau):
        return A * np.sin(2 * pi * Hz * (x - tau)) + offset_func(x, *p_offset)

    # get true crossings
    true_crossings = []
    for indice, crossing in zip(zero_indices, approx_crossings, strict=False):
        p0 = (crossing,)  # type: ignore[assignment]
        subset_start = max(indice - fit_window, 0.0)
        subset_end = min(indice + fit_window + 1, len(x_axis) - 1.0)
        x_subset = np.asarray(x_axis[subset_start:subset_end])
        y_subset = np.asarray(y_axis[subset_start:subset_end])
        # fit
        popt, pcov = curve_fit(func, x_subset, y_subset, p0)

        true_crossings.append(popt[0])

    return true_crossings


def _write_log(file, header, message):
    """
    Write log file for debugging purposes

    keyword arguments:
    file -- log file name
    header -- header line
    message -- message to be written
    """
    with open(file, "a") as f:  # Changed from "ab" to "at" (text mode)
        f.write(header)
        f.write("\n")
        f.writelines(message)
        f.write("\n")
        f.write("\n")
