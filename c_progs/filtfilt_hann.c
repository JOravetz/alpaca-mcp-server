#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h> // For memcpy and memmove

#define PI 3.14159265358979323846

// Function to generate Hanning window coefficients
double* generateHanningWindow(int N) {
    double* window = (double*)malloc(N * sizeof(double));
    for (int i = 0; i < N; i++) {
        window[i] = 0.5 * (1.0 - cos(2.0 * PI * i / (N - 1)));
    }
    return window;
}

// FIR filter function
// This function applies the FIR filter to an input signal.
// It manages the filter's internal state (delay line).
void firFilter(double* coeffs, int filterLength, double* input, int inputLength, double* output, double* delayLine) {
    int n, k;
    double acc;

    // Apply the filter to each input sample
    for (n = 0; n < inputLength; n++) {
        // Shift input samples into the delay line
        for (k = filterLength - 2; k >= 0; k--) {
            delayLine[k + 1] = delayLine[k];
        }
        delayLine[0] = input[n];

        // Calculate output n
        acc = 0;
        for (k = 0; k < filterLength; k++) {
            acc += coeffs[k] * delayLine[k];
        }
        output[n] = acc;
    }
}

// Function to reverse a signal
void reverseSignal(double* signal, int length) {
    for (int i = 0; i < length / 2; i++) {
        double temp = signal[i];
        signal[i] = signal[length - 1 - i];
        signal[length - 1 - i] = temp;
    }
}

// filtfilt implementation with reflection padding
void filtfilt(double* input, int inputLength, double* hanningWindow, int windowLength, double* output) {
    int filterOrder = windowLength - 1;
    int padLength = 3 * filterOrder; // Typical padding length for reflection.

    // Calculate the length of the padded signal
    int paddedLength = inputLength + 2 * padLength;

    // Allocate memory for the padded signal
    double* paddedInput = (double*)malloc(paddedLength * sizeof(double));

    // 1. Create reflected padding at the beginning
    for (int i = 0; i < padLength; i++) {
        paddedInput[i] = input[padLength - 1 - i]; // Reflect the beginning
    }

    // 2. Copy the original signal
    memcpy(&paddedInput[padLength], input, inputLength * sizeof(double));

    // 3. Create reflected padding at the end
    for (int i = 0; i < padLength; i++) {
        paddedInput[padLength + inputLength + i] = input[inputLength - 1 - i]; // Reflect the end
    }

    // Allocate memory for temporary filtered signals
    double* tempOutput1 = (double*)malloc(paddedLength * sizeof(double));
    double* tempOutput2 = (double*)malloc(paddedLength * sizeof(double));

    // Allocate memory for filter delay lines
    double* delayLine1 = (double*)calloc(filterOrder, sizeof(double)); // Initialize to zeros
    double* delayLine2 = (double*)calloc(filterOrder, sizeof(double)); // Initialize to zeros

    // 4. Forward pass
    firFilter(hanningWindow, windowLength, paddedInput, paddedLength, tempOutput1, delayLine1);

    // 5. Reverse the output of the forward pass
    reverseSignal(tempOutput1, paddedLength);

    // 6. Backward pass
    firFilter(hanningWindow, windowLength, tempOutput1, paddedLength, tempOutput2, delayLine2);

    // 7. Reverse the final output
    reverseSignal(tempOutput2, paddedLength);

    // 8. Extract the relevant part (remove padding)
    memcpy(output, &tempOutput2[padLength], inputLength * sizeof(double));

    // Free memory
    free(paddedInput);
    free(tempOutput1);
    free(tempOutput2);
    free(delayLine1);
    free(delayLine2);
}

int main() {
    // Example usage
    int signalLength = 100;
    int windowLength = 11; // Odd length is typical for symmetric windows

    double* inputSignal = (double*)malloc(signalLength * sizeof(double));
    // Fill inputSignal with some data (e.g., sine wave with noise)
    for (int i = 0; i < signalLength; i++) {
        inputSignal[i] = sin(2.0 * PI * i / 20.0) + (double)rand() / RAND_MAX * 0.5;
    }

    double* hanningWindow = generateHanningWindow(windowLength);
    double* filteredSignal = (double*)malloc(signalLength * sizeof(double));

    filtfilt(inputSignal, signalLength, hanningWindow, windowLength, filteredSignal);

    // Now filteredSignal contains the zero-phase filtered data with improved edge handling

    // Free memory
    free(inputSignal);
    free(hanningWindow);
    free(filteredSignal);

    return 0;
}
