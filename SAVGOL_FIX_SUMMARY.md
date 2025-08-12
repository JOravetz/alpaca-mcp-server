# Savitzky-Golay Peak Detection Fix Summary

## Problem
The initial Savitzky-Golay implementation was detecting too many peaks and troughs (26 each) due to overly sensitive zero-crossing detection in the first derivative. This resulted in detection of minor fluctuations rather than significant market movements.

## Solution
Implemented a prominence-based filtering approach using `scipy.signal.find_peaks` combined with Savitzky-Golay derivatives for validation.

## Key Changes

### 1. `alpaca_mcp_server/tools/peakdetect.py`
**Function**: `peakdetect_savgol()`

**Old Approach**:
- Detected every zero-crossing in the first derivative
- Used simple threshold based on derivative standard deviation
- Result: 26 peaks and 26 troughs detected

**New Approach**:
- Pre-smoothing with larger Savitzky-Golay window (31 samples)
- Using `scipy.signal.find_peaks` with prominence filtering
- Prominence threshold: 1% of data range (2% if still too many)
- Validation with derivative sign changes
- Result: 6 peaks and 6 troughs detected

### 2. `plot_volume_bars.py`
**Function**: `detect_peaks_troughs_derivative()`

Updated to use the same prominence-based approach:
- Pre-smoothing before derivative calculation
- Prominence-based peak detection
- Automatic threshold adjustment if too many peaks detected

## Technical Implementation

### Core Algorithm
```python
# 1. Pre-smooth the already filtered data
smoothed_data = signal.savgol_filter(data, window_length=31, polyorder=3)

# 2. Calculate first derivative as specified
first_derivative = signal.savgol_filter(
    smoothed_data, 
    window_length=3,  # As specified by user
    polyorder=2,      # As specified by user
    deriv=1,          # First derivative
    delta=1.0         # Sample spacing
)

# 3. Use prominence-based peak detection
prominence_threshold = np.ptp(smoothed_data) * 0.01  # 1% of range
peaks = signal.find_peaks(smoothed_data, prominence=prominence_threshold)

# 4. Validate with derivative sign changes
# Peak: derivative goes from positive to negative
# Trough: derivative goes from negative to positive
```

## Results

### Before Fix
- SPY with Hanning window=31: **26 peaks, 26 troughs**
- Detected every minor fluctuation
- Unusable for trading signals

### After Fix
- SPY with Hanning window=31: **6 peaks, 6 troughs**
- Only significant market movements detected
- Appropriate for trading signals

## Key Insights

1. **Pre-smoothing is Essential**: Applying Savitzky-Golay to already-filtered data requires additional smoothing to eliminate minor fluctuations.

2. **Prominence-Based Filtering**: Using scipy's `find_peaks` with prominence provides robust detection of significant extrema.

3. **Adaptive Thresholds**: The algorithm automatically adjusts thresholds if too many peaks are detected (>15).

4. **Derivative Validation**: Combining prominence detection with derivative sign-change validation ensures accuracy.

## Usage

### With plot.py
```bash
python plot.py -s SPY -w 31 --use-savgol
# Result: 6 peaks, 6 troughs
```

### With plot_volume_bars.py
```bash
python plot_volume_bars.py -s SPY -n 1 --savgol-window 5 --savgol-poly 3
# Result: 2 peaks, 2 troughs for volume bars
```

## References
- Savitzky, A., & Golay, M. J. (1964). "Smoothing and Differentiation of Data"
- López de Prado, M. (2018). "Advances in Financial Machine Learning"
- SciPy Documentation: `scipy.signal.find_peaks` and `scipy.signal.savgol_filter`