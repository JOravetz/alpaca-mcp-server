# Savitzky-Golay Filter Implementation for Peak Detection

## Overview
Implemented Savitzky-Golay filter for computing first derivatives as recommended for more accurate and smoother peak/trough detection in financial time series analysis.

## Key Changes

### 1. Core Implementation (`peakdetect.py`)
- Added `peakdetect_savgol()` function that uses `scipy.signal.savgol_filter()`
- Parameters:
  - `delta=1`: Spacing of samples
  - `window_length=3`: Minimal smoothing window
  - `polyorder=2`: Quadratic polynomial fit
  - `deriv=1`: First derivative computation

### 2. Standalone Volume Bars (`plot_volume_bars.py`)
- Updated `detect_peaks_troughs_derivative()` to use Savitzky-Golay filter
- Replaces simple `np.gradient()` with smoother derivative calculation
- Better noise reduction while preserving signal features

### 3. Main Plotting Script (`plot.py`)
- Added `--use-savgol` flag (default: True) for improved method
- Added `--use-classic` flag to revert to original peakdetect if needed
- Passes `use_savgol` parameter through processing pipeline

## Technical Benefits

### Why Savitzky-Golay?
1. **Smooth Derivatives**: Unlike finite differences, provides smooth derivatives without amplifying noise
2. **Feature Preservation**: Maintains peak shapes and positions better than simple smoothing
3. **Mathematical Rigor**: Based on local polynomial regression
4. **Proven in Signal Processing**: Standard method in spectroscopy and signal analysis

### Formula
The Savitzky-Golay filter fits a polynomial of degree `k` to a window of `2m+1` points:
```
first_derivative = signal.savgol_filter(
    data, delta=1, window_length=3, polyorder=2, deriv=1
)
```

### Peak Detection Logic
- **Peak**: First derivative changes from positive to negative
- **Trough**: First derivative changes from negative to positive
- Zero-crossings in the derivative indicate extrema

## Usage Examples

### Command Line
```bash
# Use improved Savitzky-Golay method (default)
python plot.py -s AAPL,TSLA -d 1 --use-savgol

# Use classic peakdetect method
python plot.py -s AAPL,TSLA -d 1 --use-classic
```

### Python API
```python
from peakdetect import peakdetect_savgol

# Detect peaks with Savitzky-Golay
max_peaks, min_peaks = peakdetect_savgol(
    y_axis=filtered_prices,
    x_axis=time_indices,
    window_length=3,
    polyorder=2,
    delta=1,
    min_distance=1
)
```

## Integration with Volume Bars

The Savitzky-Golay method works exceptionally well with volume bars because:
1. Volume bars have better statistical properties (less noise)
2. The smooth derivative captures institutional trading patterns
3. Reduces false signals from market microstructure noise

## Performance Comparison

| Method | Noise Sensitivity | Feature Preservation | Computation Speed |
|--------|------------------|---------------------|-------------------|
| np.gradient | High | Low | Fast |
| Classic peakdetect | Medium | Medium | Medium |
| Savitzky-Golay | Low | High | Fast |

## References
- Savitzky, A., & Golay, M. J. (1964). "Smoothing and Differentiation of Data by Simplified Least Squares Procedures"
- Press, W. H., et al. (2007). "Numerical Recipes: The Art of Scientific Computing"
- López de Prado, M. (2018). "Advances in Financial Machine Learning"