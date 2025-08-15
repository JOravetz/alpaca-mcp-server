#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <curl/curl.h>
#include <json-c/json.h>
#include <argp.h>
#include <ctype.h>

#define PI 3.14159265358979323846
#define ALPACA_BASE_URL "https://data.alpaca.markets/v2"
#define ALPACA_CALENDAR_URL "https://paper-api.alpaca.markets/v2/calendar"

// Structure to hold the response from libcurl
typedef struct {
    char *memory;
    size_t size;
} MemoryStruct;

// Expanded to hold all data from the Alpaca bars response
typedef struct {
    char *symbol;
    size_t count;
    char **timestamps;
    double *open_prices;
    double *high_prices;
    double *low_prices;
    double *close_prices;
    long *volumes;
    long *trade_counts;
    double *vwaps;
    double *filtered_values; // Generic name for the filtered data
    // Peak/trough detection data
    size_t peak_count;
    size_t trough_count;
    int *peak_indices;
    int *trough_indices;
} SymbolData;

typedef struct {
    SymbolData *symbols;
    size_t count;
} AllData;

// Added 'filter_key' to store the user's choice of what to filter
// Added 'input_file' for reading existing data instead of fetching from API
// Added 'print_signals' for -p option to print last trade signals
typedef struct {
    char *symbols_str;
    char *symbols_file;
    char *timeframe;
    char *output_file;
    char *input_file;  // NEW: Input file containing existing bar data
    char *feed;
    char *filter_key; // Key to filter on (e.g., "close", "vwap")
    int days;
    int window_length;
    int print_signals;  // NEW: Flag for -p option to print last trade signals
} Arguments;

// --- libcurl Callback ---
static size_t WriteMemoryCallback(void *contents, size_t size, size_t nmemb, void *userp) {
    size_t realsize = size * nmemb;
    MemoryStruct *mem = (MemoryStruct *)userp;
    // <--- DYNAMIC ALLOCATION: The libcurl buffer grows as data is received.
    char *ptr = realloc(mem->memory, mem->size + realsize + 1);
    if (!ptr) {
        fprintf(stderr, "error: not enough memory (realloc returned NULL)\n");
        return 0;
    }
    mem->memory = ptr;
    memcpy(&(mem->memory[mem->size]), contents, realsize);
    mem->size += realsize;
    mem->memory[mem->size] = 0;
    return realsize;
}

// --- Filtering Functions (Unchanged) ---
double* generateHanningWindow(int N) { /* ... unchanged ... */
    double* window = (double*)malloc(N * sizeof(double));
    if (!window) return NULL;
    for (int i = 0; i < N; i++) {
        window[i] = 0.5 * (1.0 - cos(2.0 * PI * i / (N - 1)));
    }
    return window;
}
void normalizeCoefficients(double* coeffs, int length) { /* ... unchanged ... */
    double sum = 0.0;
    for (int i = 0; i < length; i++) { sum += coeffs[i]; }
    if (sum != 0.0) {
        for (int i = 0; i < length; i++) { coeffs[i] /= sum; }
    }
}
void firFilter(double* coeffs, int filterLength, double* input, int inputLength, double* output, double* delayLine) { /* ... unchanged ... */
    for (int n = 0; n < inputLength; n++) {
        memmove(&delayLine[1], &delayLine[0], (filterLength - 1) * sizeof(double));
        delayLine[0] = input[n];
        double acc = 0.0;
        for (int k = 0; k < filterLength; k++) { acc += coeffs[k] * delayLine[k]; }
        output[n] = acc;
    }
}
void reverseSignal(double* signal, int length) { /* ... unchanged ... */
    for (int i = 0; i < length / 2; i++) {
        double temp = signal[i];
        signal[i] = signal[length - 1 - i];
        signal[length - 1 - i] = temp;
    }
}
void filtfilt(double* input, int inputLength, double* hanningWindow, int windowLength, double* output) { /* ... unchanged ... */
    if (inputLength <= windowLength) {
        memcpy(output, input, inputLength * sizeof(double));
        return;
    }
    int filterOrder = windowLength - 1;
    int padLength = 3 * filterOrder;
    int paddedLength = inputLength + 2 * padLength;
    double* paddedInput = (double*)malloc(paddedLength * sizeof(double));
    double* tempOutput1 = (double*)malloc(paddedLength * sizeof(double));
    double* tempOutput2 = (double*)malloc(paddedLength * sizeof(double));
    double* delayLine1 = (double*)calloc(windowLength, sizeof(double));
    double* delayLine2 = (double*)calloc(windowLength, sizeof(double));
    if (!paddedInput || !tempOutput1 || !tempOutput2 || !delayLine1 || !delayLine2) {
        free(paddedInput); free(tempOutput1); free(tempOutput2); free(delayLine1); free(delayLine2);
        memcpy(output, input, inputLength * sizeof(double));
        return;
    }
    for (int i = 0; i < padLength; i++) { paddedInput[i] = input[padLength - 1 - i]; }
    memcpy(&paddedInput[padLength], input, inputLength * sizeof(double));
    for (int i = 0; i < padLength; i++) { paddedInput[padLength + inputLength + i] = input[inputLength - 1 - i]; }
    firFilter(hanningWindow, windowLength, paddedInput, paddedLength, tempOutput1, delayLine1);
    reverseSignal(tempOutput1, paddedLength);
    firFilter(hanningWindow, windowLength, tempOutput1, paddedLength, tempOutput2, delayLine2);
    reverseSignal(tempOutput2, paddedLength);
    memcpy(output, &tempOutput2[padLength], inputLength * sizeof(double));
    free(paddedInput); free(tempOutput1); free(tempOutput2); free(delayLine1); free(delayLine2);
}

// --- Peak/Trough Detection Functions ---
void calculateFirstDerivative(double* input, int inputLength, double* derivative) {
    if (inputLength < 2) return;

    // Forward difference for first point
    derivative[0] = input[1] - input[0];

    // Central difference for middle points
    for (int i = 1; i < inputLength - 1; i++) {
        derivative[i] = (input[i + 1] - input[i - 1]) / 2.0;
    }

    // Backward difference for last point
    derivative[inputLength - 1] = input[inputLength - 1] - input[inputLength - 2];
}

void detectPeaksAndTroughs(double* derivative, int length, int** peaks, size_t* peak_count, int** troughs, size_t* trough_count) {
    if (length < 2) {
        *peaks = NULL; *peak_count = 0;
        *troughs = NULL; *trough_count = 0;
        return;
    }

    // Temporary arrays to store indices (allocate max possible size)
    int* temp_peaks = malloc(length * sizeof(int));
    int* temp_troughs = malloc(length * sizeof(int));
    size_t temp_peak_count = 0;
    size_t temp_trough_count = 0;

    // Look for zero crossings in the derivative
    for (int i = 0; i < length - 1; i++) {
        double current = derivative[i];
        double next = derivative[i + 1];

        // Skip if either value is exactly zero (to avoid false positives)
        if (current == 0.0 || next == 0.0) continue;

        // Check for sign change
        if ((current > 0 && next < 0)) {
            // Positive to negative = peak at index i+1
            temp_peaks[temp_peak_count++] = i + 1;
        } else if ((current < 0 && next > 0)) {
            // Negative to positive = trough at index i+1
            temp_troughs[temp_trough_count++] = i + 1;
        }
    }

    // Allocate final arrays with exact size needed
    if (temp_peak_count > 0) {
        *peaks = malloc(temp_peak_count * sizeof(int));
        memcpy(*peaks, temp_peaks, temp_peak_count * sizeof(int));
        *peak_count = temp_peak_count;
    } else {
        *peaks = NULL;
        *peak_count = 0;
    }

    if (temp_trough_count > 0) {
        *troughs = malloc(temp_trough_count * sizeof(int));
        memcpy(*troughs, temp_troughs, temp_trough_count * sizeof(int));
        *trough_count = temp_trough_count;
    } else {
        *troughs = NULL;
        *trough_count = 0;
    }

    free(temp_peaks);
    free(temp_troughs);
}

// --- NEW: Input File Reading Function ---
int load_data_from_file(const char *input_file, AllData *all_data) {
    FILE *file = fopen(input_file, "r");
    if (!file) {
        fprintf(stderr, "Error: Cannot open input file '%s'\n", input_file);
        return -1;
    }

    // Get file size
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    // Read entire file
    char *file_content = malloc(file_size + 1);
    if (!file_content) {
        fclose(file);
        return -1;
    }

    size_t bytes_read = fread(file_content, 1, file_size, file);
    file_content[bytes_read] = '\0';
    fclose(file);

    // Parse JSON
    json_object *root = json_tokener_parse(file_content);
    free(file_content);

    if (!root) {
        fprintf(stderr, "Error: Invalid JSON in input file\n");
        return -1;
    }

    // Initialize data structure
    all_data->symbols = NULL;
    all_data->count = 0;

    // Parse each symbol in the JSON
    json_object_object_foreach(root, symbol_key, symbol_obj) {
        // Allocate space for new symbol
        all_data->symbols = realloc(all_data->symbols, (all_data->count + 1) * sizeof(SymbolData));
        SymbolData *s = &all_data->symbols[all_data->count++];

        // Initialize symbol
        s->symbol = strdup(symbol_key);
        s->count = 0;
        s->timestamps = NULL;
        s->open_prices = NULL;
        s->high_prices = NULL;
        s->low_prices = NULL;
        s->close_prices = NULL;
        s->volumes = NULL;
        s->trade_counts = NULL;
        s->vwaps = NULL;
        s->filtered_values = NULL;
        s->peak_indices = NULL;
        s->trough_indices = NULL;
        s->peak_count = 0;
        s->trough_count = 0;

        // Parse arrays
        json_object *timestamps_arr, *open_arr, *high_arr, *low_arr, *close_arr, *volume_arr, *trade_count_arr, *vwap_arr;

        if (json_object_object_get_ex(symbol_obj, "timestamps", &timestamps_arr) &&
            json_object_object_get_ex(symbol_obj, "open", &open_arr) &&
            json_object_object_get_ex(symbol_obj, "high", &high_arr) &&
            json_object_object_get_ex(symbol_obj, "low", &low_arr) &&
            json_object_object_get_ex(symbol_obj, "close", &close_arr) &&
            json_object_object_get_ex(symbol_obj, "volume", &volume_arr) &&
            json_object_object_get_ex(symbol_obj, "trade_count", &trade_count_arr) &&
            json_object_object_get_ex(symbol_obj, "vwap", &vwap_arr)) {

            size_t array_length = json_object_array_length(timestamps_arr);
            s->count = array_length;

            // Allocate arrays
            s->timestamps = malloc(array_length * sizeof(char*));
            s->open_prices = malloc(array_length * sizeof(double));
            s->high_prices = malloc(array_length * sizeof(double));
            s->low_prices = malloc(array_length * sizeof(double));
            s->close_prices = malloc(array_length * sizeof(double));
            s->volumes = malloc(array_length * sizeof(long));
            s->trade_counts = malloc(array_length * sizeof(long));
            s->vwaps = malloc(array_length * sizeof(double));

            // Fill arrays
            for (size_t i = 0; i < array_length; i++) {
                json_object *ts_obj = json_object_array_get_idx(timestamps_arr, i);
                json_object *o_obj = json_object_array_get_idx(open_arr, i);
                json_object *h_obj = json_object_array_get_idx(high_arr, i);
                json_object *l_obj = json_object_array_get_idx(low_arr, i);
                json_object *c_obj = json_object_array_get_idx(close_arr, i);
                json_object *v_obj = json_object_array_get_idx(volume_arr, i);
                json_object *n_obj = json_object_array_get_idx(trade_count_arr, i);
                json_object *vw_obj = json_object_array_get_idx(vwap_arr, i);

                s->timestamps[i] = strdup(json_object_get_string(ts_obj));
                s->open_prices[i] = json_object_get_double(o_obj);
                s->high_prices[i] = json_object_get_double(h_obj);
                s->low_prices[i] = json_object_get_double(l_obj);
                s->close_prices[i] = json_object_get_double(c_obj);
                s->volumes[i] = json_object_get_int64(v_obj);
                s->trade_counts[i] = json_object_get_int64(n_obj);
                s->vwaps[i] = json_object_get_double(vw_obj);
            }

            printf("Loaded %zu bars for symbol %s from input file\n", array_length, symbol_key);
        }
    }

    json_object_put(root);
    return 0;
}

// --- Original Alpaca API Functions (unchanged but now optional) ---
int get_trading_days(int num_days, const char *api_key, const char *api_secret, char **start_date, char **end_date) { /* ... unchanged ... */
    CURL *curl; CURLcode res; MemoryStruct chunk; chunk.memory = malloc(1); chunk.size = 0; time_t now = time(NULL);
    int calendar_days_to_fetch = num_days * 2; if (num_days > 20) calendar_days_to_fetch = (int)(num_days * 1.7); if (calendar_days_to_fetch < 30) calendar_days_to_fetch = 30;
    time_t start_time = now - calendar_days_to_fetch * 86400; char start_str[11], end_str[11];
    strftime(start_str, sizeof(start_str), "%Y-%m-%d", localtime(&start_time)); strftime(end_str, sizeof(end_str), "%Y-%m-%d", localtime(&now));
    // Dynamically allocate URL buffer
    size_t url_size = strlen(ALPACA_CALENDAR_URL) + strlen(start_str) + strlen(end_str) + 20; // Extra for ?start=&end=
    char *url = malloc(url_size);
    if (!url) {
        free(chunk.memory);
        return -1;
    }
    snprintf(url, url_size, "%s?start=%s&end=%s", ALPACA_CALENDAR_URL, start_str, end_str);
    curl = curl_easy_init();
    if(curl) {
        struct curl_slist *headers = NULL;
        // Dynamically allocate API header buffers
        size_t key_header_size = strlen(api_key) + 30;
        size_t secret_header_size = strlen(api_secret) + 30;
        char *api_key_header = malloc(key_header_size);
        char *api_secret_header = malloc(secret_header_size);
        if (!api_key_header || !api_secret_header) {
            free(api_key_header); free(api_secret_header);
            free(chunk.memory); free(url);
            return -1;
        }
        snprintf(api_key_header, key_header_size, "APCA-API-KEY-ID: %s", api_key);
        snprintf(api_secret_header, secret_header_size, "APCA-API-SECRET-KEY: %s", api_secret);
        headers = curl_slist_append(headers, api_key_header); headers = curl_slist_append(headers, api_secret_header);
        free(api_key_header); free(api_secret_header);  // Free headers after adding to list
        curl_easy_setopt(curl, CURLOPT_URL, url); curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers); curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteMemoryCallback); curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)&chunk);
        res = curl_easy_perform(curl); curl_easy_cleanup(curl); curl_slist_free_all(headers);
        free(url);  // Free the dynamically allocated URL
        if (res != CURLE_OK) { free(chunk.memory); return -1; }
        json_object *root = json_tokener_parse(chunk.memory); free(chunk.memory); if (!root) return -1;
        if (json_object_get_type(root) != json_type_array) { json_object_put(root); return -1; }
        size_t array_size = json_object_array_length(root);
        if (array_size < (size_t)num_days) { fprintf(stderr, "Warning: Requested %d days, but calendar API only returned %zu.\n", num_days, array_size); }
        size_t start_index = (array_size > (size_t)num_days) ? (array_size - num_days) : 0;
        json_object *start_obj = json_object_array_get_idx(root, start_index); json_object *end_obj = json_object_array_get_idx(root, array_size - 1);
        if (start_obj && end_obj) {
            json_object *start_date_json, *end_date_json;
            if (json_object_object_get_ex(start_obj, "date", &start_date_json) && json_object_object_get_ex(end_obj, "date", &end_date_json)) {
                *start_date = strdup(json_object_get_string(start_date_json)); *end_date = strdup(json_object_get_string(end_date_json));
            }
        }
        json_object_put(root); return 0;
    }
    free(url);  // Free URL if curl_easy_init failed
    return -1;
}

int fetch_bars(Arguments *args, const char *api_key, const char *api_secret, const char *start_date, const char *end_date, AllData *all_data) {
    CURL *curl; char *page_token = NULL;
    do {
        // Dynamically allocate URL based on actual content size
        size_t url_size = strlen(ALPACA_BASE_URL) + strlen(args->symbols_str) + strlen(args->timeframe) +
                         strlen(start_date) + strlen(end_date) + strlen(args->feed) + 200;
        if (page_token) {
            url_size += strlen(page_token) + 20;
        }
        char *url = malloc(url_size);
        if (!url) {
            if (page_token) free(page_token);
            return -1;
        }

        if (page_token) {
            snprintf(url, url_size, "%s/stocks/bars?symbols=%s&timeframe=%s&start=%s&end=%s&limit=10000&adjustment=split&feed=%s&sort=asc&page_token=%s", ALPACA_BASE_URL, args->symbols_str, args->timeframe, start_date, end_date, args->feed, page_token);
            free(page_token); page_token = NULL;
        } else {
            snprintf(url, url_size, "%s/stocks/bars?symbols=%s&timeframe=%s&start=%s&end=%s&limit=10000&adjustment=split&feed=%s&sort=asc", ALPACA_BASE_URL, args->symbols_str, args->timeframe, start_date, end_date, args->feed);
        }
        MemoryStruct chunk = { .memory = malloc(1), .size = 0 }; curl = curl_easy_init();
        if(!curl) { free(chunk.memory); free(url); return -1; }
        struct curl_slist *headers = NULL;
        // Dynamically allocate API header buffers
        size_t key_header_size = strlen(api_key) + 30;
        size_t secret_header_size = strlen(api_secret) + 30;
        char *api_key_header = malloc(key_header_size);
        char *api_secret_header = malloc(secret_header_size);
        if (!api_key_header || !api_secret_header) {
            free(api_key_header); free(api_secret_header);
            free(chunk.memory); free(url);
            return -1;
        }
        snprintf(api_key_header, key_header_size, "APCA-API-KEY-ID: %s", api_key);
        snprintf(api_secret_header, secret_header_size, "APCA-API-SECRET-KEY: %s", api_secret);
        headers = curl_slist_append(headers, api_key_header); headers = curl_slist_append(headers, api_secret_header);
        free(api_key_header); free(api_secret_header);  // Free headers after adding to list
        curl_easy_setopt(curl, CURLOPT_URL, url); curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers); curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteMemoryCallback); curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)&chunk);
        CURLcode res = curl_easy_perform(curl); curl_easy_cleanup(curl); curl_slist_free_all(headers);
        if (res != CURLE_OK) { free(chunk.memory); free(url); return -1; }
        free(url);  // Free URL after successful use
        json_object *root = json_tokener_parse(chunk.memory); free(chunk.memory); if (!root) { return -1; }
        json_object *bars_obj;
        if (json_object_object_get_ex(root, "bars", &bars_obj)) {
            json_object_object_foreach(bars_obj, symbol_key, bars_array) {
                int symbol_idx = -1;
                for (size_t i = 0; i < all_data->count; i++) { if (strcmp(all_data->symbols[i].symbol, symbol_key) == 0) { symbol_idx = i; break; } }
                if (symbol_idx == -1) {
                    // <--- DYNAMIC ALLOCATION: Growing the list of symbols
                    all_data->symbols = realloc(all_data->symbols, (all_data->count + 1) * sizeof(SymbolData));
                    symbol_idx = all_data->count++;
                    SymbolData *s = &all_data->symbols[symbol_idx];
                    s->symbol = strdup(symbol_key); s->count = 0;
                    s->timestamps = NULL; s->open_prices = NULL; s->high_prices = NULL; s->low_prices = NULL;
                    s->close_prices = NULL; s->volumes = NULL; s->trade_counts = NULL; s->vwaps = NULL;
                }
                SymbolData *s = &all_data->symbols[symbol_idx];
                size_t num_bars = json_object_array_length(bars_array); size_t old_count = s->count; size_t new_count = old_count + num_bars;

                // <--- DYNAMIC ALLOCATION: Using realloc to grow the data arrays for each page of API results.
                s->timestamps = realloc(s->timestamps, new_count * sizeof(char*));
                s->open_prices = realloc(s->open_prices, new_count * sizeof(double));
                s->high_prices = realloc(s->high_prices, new_count * sizeof(double));
                s->low_prices = realloc(s->low_prices, new_count * sizeof(double));
                s->close_prices = realloc(s->close_prices, new_count * sizeof(double));
                s->volumes = realloc(s->volumes, new_count * sizeof(long));
                s->trade_counts = realloc(s->trade_counts, new_count * sizeof(long));
                s->vwaps = realloc(s->vwaps, new_count * sizeof(double));

                for (size_t i = 0; i < num_bars; i++) {
                    json_object *bar = json_object_array_get_idx(bars_array, i);
                    json_object *t_obj, *o_obj, *h_obj, *l_obj, *c_obj, *v_obj, *n_obj, *vw_obj;
                    json_object_object_get_ex(bar, "t", &t_obj); json_object_object_get_ex(bar, "o", &o_obj); json_object_object_get_ex(bar, "h", &h_obj);
                    json_object_object_get_ex(bar, "l", &l_obj); json_object_object_get_ex(bar, "c", &c_obj); json_object_object_get_ex(bar, "v", &v_obj);
                    json_object_object_get_ex(bar, "n", &n_obj); json_object_object_get_ex(bar, "vw", &vw_obj);
                    // <--- DYNAMIC ALLOCATION: strdup creates a new memory block for each timestamp string.
                    s->timestamps[old_count + i] = strdup(json_object_get_string(t_obj));
                    s->open_prices[old_count + i] = json_object_get_double(o_obj); s->high_prices[old_count + i] = json_object_get_double(h_obj);
                    s->low_prices[old_count + i] = json_object_get_double(l_obj); s->close_prices[old_count + i] = json_object_get_double(c_obj);
                    s->volumes[old_count + i] = json_object_get_int64(v_obj); s->trade_counts[old_count + i] = json_object_get_int64(n_obj);
                    s->vwaps[old_count + i] = json_object_get_double(vw_obj);
                }
                s->count = new_count;
            }
        }
        json_object *next_page_token_obj;
        if (json_object_object_get_ex(root, "next_page_token", &next_page_token_obj) && json_object_get_type(next_page_token_obj) == json_type_string) {
            page_token = strdup(json_object_get_string(next_page_token_obj));
        }
        json_object_put(root);
    } while (page_token != NULL);
    return 0;
}

// Convert string to uppercase
void str_to_upper(char *str) {
    if (!str) return;
    for (int i = 0; str[i]; i++) {
        str[i] = toupper((unsigned char)str[i]);
    }
}

char* read_symbols_from_file(const char* filename) {
    FILE* file = fopen(filename, "r"); if (!file) { return NULL; } fseek(file, 0, SEEK_END); long length = ftell(file); fseek(file, 0, SEEK_SET);
    char* buffer = malloc(length + 1); if (!buffer) { fclose(file); return NULL; } size_t bytes_read = fread(buffer, 1, length, file); fclose(file);
    buffer[bytes_read] = '\0';
    for (size_t i = 0; i < bytes_read; i++) {
        if (buffer[i] == '\n' || buffer[i] == '\r' || buffer[i] == ' ')
            buffer[i] = ',';
    }
    // Convert to uppercase
    str_to_upper(buffer);
    return buffer;
}

// Print help message
void print_help(const char *program_name) {
    printf("filter_bars_input - Process stock bar data with Hanning filter and peak/trough detection\n");
    printf("\nUsage: %s [OPTIONS]\n", program_name);
    printf("\nDescription:\n");
    printf("  Fetches stock data from Alpaca API or loads from JSON file, applies zero-phase\n");
    printf("  Hanning filtering, and detects peaks/troughs for trading signals.\n");
    printf("\nOptions:\n");
    printf("  -h              Show this help message and exit\n");
    printf("  -i FILE         Input JSON file with existing bar data (skips API fetch)\n");
    printf("  -o FILE         Output JSON file (default: stdout)\n");
    printf("  -s SYMBOLS      Comma-separated list of stock symbols (e.g., \"AAPL,MSFT,GOOGL\")\n");
    printf("  -f FILE         File containing symbols, one per line\n");
    printf("  -n NUM          Number of trading days to fetch (default: 1)\n");
    printf("  -t TIMEFRAME    Timeframe: 1Min, 5Min, 15Min, 1Hour, 1Day, etc. (default: 1Min)\n");
    printf("  -w LENGTH       Hanning window length, must be odd > 1 (default: 11)\n");
    printf("  -k KEY          Data field to filter: open, high, low, close, vwap (default: close)\n");
    printf("  -p              Output last trade signals as JSON (sorted by signal type and samples ago)\n");
    printf("  --feed FEED     Data feed source: sip, iex, otc (default: sip)\n");
    printf("\nEnvironment Variables (required for API mode):\n");
    printf("  APCA_API_KEY_ID      Alpaca API key ID\n");
    printf("  APCA_API_SECRET_KEY  Alpaca API secret key\n");
    printf("\nExamples:\n");
    printf("  # Process existing data file (streaming mode)\n");
    printf("  %s -i data.json -w 21 -k close -o processed.json\n", program_name);
    printf("\n  # Fetch from API and process\n");
    printf("  %s -s AAPL,MSFT -n 5 -t 5Min -w 21 -o output.json\n", program_name);
    printf("\n  # Read symbols from file, use 1-hour bars\n");
    printf("  %s -f symbols.txt -t 1Hour -w 15 -k vwap\n", program_name);
    printf("\nOutput: JSON with original data, filtered values, and detected peaks/troughs\n");
}

// --- Updated Argp Parser ---
static char doc[] = "Fetch Alpaca stock data or load from file, apply a Hanning filter to a specified data field, and output as JSON.";
static char args_doc[] = "";
static struct argp_option options[] = {
    {.name = "help", .key = 'h', .doc = "Show help message and exit"},
    {.name = "days", .key = 'n', .arg = "NUM", .doc = "Number of trading days to fetch (default: 1)"},
    {.name = "timeframe", .key = 't', .arg = "TF", .doc = "Timeframe (e.g., 1Min, 1H, 1D). Default: 1Min"},
    {.name = "symbols", .key = 's', .arg = "SYMBOLS", .doc = "Comma-separated list of stock symbols"},
    {.name = "file", .key = 'f', .arg = "FILE", .doc = "File with symbols, one per line"},
    {.name = "input", .key = 'i', .arg = "FILE", .doc = "Input JSON file with existing bar data (skips API fetch)"},
    {.name = "output", .key = 'o', .arg = "FILE", .doc = "Output file for JSON data (stdout if not specified)"},
    {.name = "window", .key = 'w', .arg = "LEN", .doc = "Hanning window length (odd number > 1). Default: 11"},
    {.name = "filter-on", .key = 'k', .arg = "KEY", .doc = "Data key to filter. One of: open, high, low, close, vwap. (default: close)"},
    {.name = "print-signals", .key = 'p', .doc = "Output last trade signals as JSON"},
    {.name = "feed", .key = 600, .arg = "FEED", .doc = "Data feed: 'sip', 'iex', 'otc' (default: sip)"},
    {0}
};
static error_t parse_opt(int key, char *arg, struct argp_state *state) {
    Arguments *arguments = state->input;
    switch (key) {
        case 'h': print_help(state->name); exit(0); break;
        case 'n': arguments->days = atoi(arg); break; case 't': arguments->timeframe = arg; break; case 's': arguments->symbols_str = arg; break;
        case 'f': arguments->symbols_file = arg; break; case 'i': arguments->input_file = arg; break; case 'o': arguments->output_file = arg; break; case 'w': arguments->window_length = atoi(arg); break;
        case 'k': arguments->filter_key = arg; break; case 'p': arguments->print_signals = 1; break; case 600: arguments->feed = arg; break;
        case ARGP_KEY_ARG: return ARGP_ERR_UNKNOWN; default: return ARGP_ERR_UNKNOWN;
    }
    return 0;
}
static struct argp argp = { .options = options, .parser = parse_opt, .args_doc = args_doc, .doc = doc };

// Structure for signal summary data
typedef struct {
    char symbol[16];
    char last_signal[16];
    double signal_price;
    double current_price;
    double percent_diff;
    int samples_ago;
} SignalSummary;

// Comparison function for sorting by last_signal (Resistance before Support), then by samples_ago
int compare_signals(const void *a, const void *b) {
    const SignalSummary *sig_a = (const SignalSummary *)a;
    const SignalSummary *sig_b = (const SignalSummary *)b;

    // First sort by signal type (Resistance before Support)
    int signal_cmp = strcmp(sig_a->last_signal, sig_b->last_signal);
    if (signal_cmp != 0) {
        return signal_cmp;
    }

    // Then sort by samples_ago (ascending)
    return sig_a->samples_ago - sig_b->samples_ago;
}

// Function to convert UTC timestamp to ET timezone string
void convert_to_et_time(const char *utc_timestamp, char *et_buffer, size_t buffer_size) {
    // Parse the UTC timestamp (format: "2024-01-01T12:00:00Z")
    struct tm utc_tm = {0};
    int year, month, day, hour, minute, second;

    if (sscanf(utc_timestamp, "%d-%d-%dT%d:%d:%dZ",
               &year, &month, &day, &hour, &minute, &second) == 6) {
        utc_tm.tm_year = year - 1900;
        utc_tm.tm_mon = month - 1;
        utc_tm.tm_mday = day;
        utc_tm.tm_hour = hour;
        utc_tm.tm_min = minute;
        utc_tm.tm_sec = second;

        // Convert to time_t
        time_t utc_time = timegm(&utc_tm);

        // Convert to ET (EST = UTC-5, EDT = UTC-4)
        // Simplified: using -5 hours for EST (would need proper DST handling in production)
        // For accurate DST handling, would need to check if date falls in DST period
        int is_dst = 0;
        // Simple DST check (2nd Sunday in March to 1st Sunday in November)
        if (month > 3 && month < 11) {
            is_dst = 1;
        } else if (month == 3 || month == 11) {
            // More complex logic needed for March and November edge cases
            is_dst = (month == 3 && day >= 10) || (month == 11 && day < 3);
        }

        int offset_hours = is_dst ? 4 : 5;
        time_t et_time = utc_time - (offset_hours * 3600);

        struct tm *et_tm = gmtime(&et_time);
        strftime(et_buffer, buffer_size, "%Y-%m-%d %H:%M:%S ET", et_tm);
    } else {
        strncpy(et_buffer, utc_timestamp, buffer_size - 1);
        et_buffer[buffer_size - 1] = '\0';
    }
}

// Function to print last trade signal summary as JSON with parameters
void print_signal_summary(AllData *all_data, const char *filter_key, Arguments *args) {
    // Get current time in ET
    time_t now = time(NULL);
    struct tm *utc_tm = gmtime(&now);

    // Convert to ET (simplified - production would need proper timezone library)
    // Determine if we're in DST
    int month = utc_tm->tm_mon + 1;
    int day = utc_tm->tm_mday;
    int is_dst = 0;
    if (month > 3 && month < 11) {
        is_dst = 1;
    } else if (month == 3 || month == 11) {
        is_dst = (month == 3 && day >= 10) || (month == 11 && day < 3);
    }

    int offset_hours = is_dst ? 4 : 5;
    time_t et_now = now - (offset_hours * 3600);
    struct tm *et_tm = gmtime(&et_now);

    char current_time_et[64];
    strftime(current_time_et, sizeof(current_time_et), "%Y-%m-%d %H:%M:%S ET", et_tm);

    // Allocate array for signal summaries with expanded structure
    typedef struct {
        char symbol[16];
        char last_signal[16];
        double signal_price;
        double current_price;
        double percent_diff;
        int samples_ago;
        char signal_timestamp[256];
        char signal_time_et[64];
    } ExtendedSignalSummary;

    ExtendedSignalSummary *summaries = malloc(all_data->count * sizeof(ExtendedSignalSummary));
    int summary_count = 0;

    // Process each symbol
    for (size_t i = 0; i < all_data->count; i++) {
        SymbolData *s = &all_data->symbols[i];

        if (s->count == 0 || !s->filtered_values) continue;

        // Find the last signal (peak or trough)
        int last_signal_idx = -1;
        const char *signal_type = NULL;

        // Check peaks and troughs to find the most recent one
        // Peaks are resistance levels, troughs are support levels
        for (size_t p = 0; p < s->peak_count; p++) {
            if (s->peak_indices[p] > last_signal_idx) {
                last_signal_idx = s->peak_indices[p];
                signal_type = "Resistance";
            }
        }

        for (size_t t = 0; t < s->trough_count; t++) {
            if (s->trough_indices[t] > last_signal_idx) {
                last_signal_idx = s->trough_indices[t];
                signal_type = "Support";
            }
        }

        // If no signal found, skip this symbol
        if (last_signal_idx < 0) {
            continue;
        }

        // Get the RAW price at the signal location (not the filtered value)
        double signal_price = 0.0;
        if (strcmp(filter_key, "open") == 0 && s->open_prices) {
            signal_price = s->open_prices[last_signal_idx];
        } else if (strcmp(filter_key, "high") == 0 && s->high_prices) {
            signal_price = s->high_prices[last_signal_idx];
        } else if (strcmp(filter_key, "low") == 0 && s->low_prices) {
            signal_price = s->low_prices[last_signal_idx];
        } else if (strcmp(filter_key, "close") == 0 && s->close_prices) {
            signal_price = s->close_prices[last_signal_idx];
        } else if (strcmp(filter_key, "vwap") == 0 && s->vwaps) {
            signal_price = s->vwaps[last_signal_idx];
        }

        // Get the actual current price based on filter_key
        double current_price = 0.0;
        if (strcmp(filter_key, "open") == 0 && s->open_prices) {
            current_price = s->open_prices[s->count - 1];
        } else if (strcmp(filter_key, "high") == 0 && s->high_prices) {
            current_price = s->high_prices[s->count - 1];
        } else if (strcmp(filter_key, "low") == 0 && s->low_prices) {
            current_price = s->low_prices[s->count - 1];
        } else if (strcmp(filter_key, "close") == 0 && s->close_prices) {
            current_price = s->close_prices[s->count - 1];
        } else if (strcmp(filter_key, "vwap") == 0 && s->vwaps) {
            current_price = s->vwaps[s->count - 1];
        }

        // Calculate percent difference
        double percent_diff = ((current_price - signal_price) / signal_price) * 100.0;

        // Calculate samples ago
        int samples_ago = s->count - last_signal_idx;

        // Store in summary array
        ExtendedSignalSummary *summary = &summaries[summary_count++];
        strncpy(summary->symbol, s->symbol, sizeof(summary->symbol) - 1);
        summary->symbol[sizeof(summary->symbol) - 1] = '\0';
        strncpy(summary->last_signal, signal_type, sizeof(summary->last_signal) - 1);
        summary->last_signal[sizeof(summary->last_signal) - 1] = '\0';
        summary->signal_price = signal_price;
        summary->current_price = current_price;
        summary->percent_diff = percent_diff;
        summary->samples_ago = samples_ago;

        // Store the signal timestamp
        strncpy(summary->signal_timestamp, s->timestamps[last_signal_idx], sizeof(summary->signal_timestamp) - 1);
        summary->signal_timestamp[sizeof(summary->signal_timestamp) - 1] = '\0';

        // Convert signal timestamp to ET
        convert_to_et_time(s->timestamps[last_signal_idx], summary->signal_time_et, sizeof(summary->signal_time_et));
    }

    // Sort the summaries - need custom compare for extended structure
    int compare_extended(const void *a, const void *b) {
        const ExtendedSignalSummary *sig_a = (const ExtendedSignalSummary *)a;
        const ExtendedSignalSummary *sig_b = (const ExtendedSignalSummary *)b;
        int signal_cmp = strcmp(sig_a->last_signal, sig_b->last_signal);
        if (signal_cmp != 0) return signal_cmp;
        return sig_a->samples_ago - sig_b->samples_ago;
    }
    qsort(summaries, summary_count, sizeof(ExtendedSignalSummary), compare_extended);

    // Create JSON output
    json_object *root = json_object_new_object();

    // Add parameters section
    json_object *params = json_object_new_object();
    json_object_object_add(params, "window_length", json_object_new_int(args->window_length));
    json_object_object_add(params, "filter_key", json_object_new_string(filter_key));
    json_object_object_add(params, "timeframe", json_object_new_string(args->timeframe));
    json_object_object_add(params, "days", json_object_new_int(args->days));
    json_object_object_add(params, "feed", json_object_new_string(args->feed));
    json_object_object_add(params, "current_time_et", json_object_new_string(current_time_et));
    json_object_object_add(root, "parameters", params);

    // Add signals array
    json_object *signals_array = json_object_new_array();

    for (int i = 0; i < summary_count; i++) {
        json_object *signal_obj = json_object_new_object();
        json_object_object_add(signal_obj, "symbol", json_object_new_string(summaries[i].symbol));
        json_object_object_add(signal_obj, "last_signal", json_object_new_string(summaries[i].last_signal));
        json_object_object_add(signal_obj, "signal_price", json_object_new_double(summaries[i].signal_price));
        json_object_object_add(signal_obj, "current_price", json_object_new_double(summaries[i].current_price));
        json_object_object_add(signal_obj, "percent_diff", json_object_new_double(summaries[i].percent_diff));
        json_object_object_add(signal_obj, "samples_ago", json_object_new_int(summaries[i].samples_ago));
        json_object_object_add(signal_obj, "signal_timestamp_utc", json_object_new_string(summaries[i].signal_timestamp));
        json_object_object_add(signal_obj, "signal_time_et", json_object_new_string(summaries[i].signal_time_et));
        json_object_array_add(signals_array, signal_obj);
    }

    json_object_object_add(root, "signals", signals_array);
    json_object_object_add(root, "count", json_object_new_int(summary_count));

    // Print JSON
    const char *json_string = json_object_to_json_string_ext(root, JSON_C_TO_STRING_PRETTY);
    printf("%s\n", json_string);

    // Cleanup
    json_object_put(root);
    free(summaries);
}

// --- Main Execution ---
int main(int argc, char **argv) {
    Arguments arguments;
    arguments.days = 1; arguments.timeframe = "1Min"; arguments.symbols_str = NULL; arguments.symbols_file = NULL;
    arguments.input_file = NULL; arguments.output_file = NULL; arguments.window_length = 11; arguments.feed = "sip"; arguments.filter_key = "close";
    arguments.print_signals = 0;  // Default: don't print signal summary
    argp_parse(&argp, argc, argv, 0, 0, &arguments);

    if (strcmp(arguments.filter_key, "open") != 0 && strcmp(arguments.filter_key, "high") != 0 && strcmp(arguments.filter_key, "low") != 0 && strcmp(arguments.filter_key, "close") != 0 && strcmp(arguments.filter_key, "vwap") != 0) {
        fprintf(stderr, "Error: Invalid key for --filter-on. Must be one of: open, high, low, close, vwap.\n"); exit(1);
    }

    AllData all_data = { .symbols = NULL, .count = 0 };

    // NEW: Check if input file is provided
    if (arguments.input_file) {
        printf("Loading data from input file: %s\n", arguments.input_file);
        if (load_data_from_file(arguments.input_file, &all_data) != 0) {
            fprintf(stderr, "Error: Failed to load data from input file\n");
            exit(1);
        }
    } else {
        // Original API fetching logic
        char *symbols_from_file = NULL;
        if (arguments.symbols_file) { symbols_from_file = read_symbols_from_file(arguments.symbols_file); }
        if (!arguments.symbols_str && symbols_from_file) {
            arguments.symbols_str = symbols_from_file;
        } else if (arguments.symbols_str && symbols_from_file) {
            char *combined = malloc(strlen(arguments.symbols_str) + strlen(symbols_from_file) + 2);
            sprintf(combined, "%s,%s", arguments.symbols_str, symbols_from_file);
            free(symbols_from_file);
            arguments.symbols_str = combined;
        } else if (arguments.symbols_str) {
            // Make a copy and convert to uppercase
            char *upper_symbols = strdup(arguments.symbols_str);
            str_to_upper(upper_symbols);
            arguments.symbols_str = upper_symbols;
        }
        if (!arguments.symbols_str) { fprintf(stderr, "Error: No symbols provided.\n"); exit(1); }

        // Convert all symbols to uppercase (if not already done)
        if (arguments.symbols_str) {
            str_to_upper(arguments.symbols_str);
        }

        const char *api_key = getenv("APCA_API_KEY_ID"); const char *api_secret = getenv("APCA_API_SECRET_KEY");
        if (!api_key || !api_secret) { fprintf(stderr, "Error: API keys not set in environment.\n"); exit(1); }
        curl_global_init(CURL_GLOBAL_ALL);
        char *start_date = NULL, *end_date = NULL;
        if (get_trading_days(arguments.days, api_key, api_secret, &start_date, &end_date) != 0) { exit(1); }
        printf("Data range: from %s to %s\n", start_date, end_date);
        if (fetch_bars(&arguments, api_key, api_secret, start_date, end_date, &all_data) != 0) { exit(1); }
        free(start_date);
        free(end_date);
        curl_global_cleanup();
    }

    // Validate parameters
    if (arguments.window_length < 3 || arguments.window_length > 1000) {
        fprintf(stderr, "Error: Window length must be between 3 and 1000, got %d\n", arguments.window_length);
        exit(1);
    }
    if (arguments.window_length % 2 == 0) {
        fprintf(stderr, "Error: Window length must be odd for proper filtering, got %d\n", arguments.window_length);
        exit(1);
    }
    if (arguments.days < 1 || arguments.days > 365) {
        fprintf(stderr, "Error: Days must be between 1 and 365, got %d\n", arguments.days);
        exit(1);
    }

    // Validate filter key
    const char *valid_keys[] = {"open", "high", "low", "close", "vwap", NULL};
    int valid_key = 0;
    for (int i = 0; valid_keys[i]; i++) {
        if (strcmp(arguments.filter_key, valid_keys[i]) == 0) {
            valid_key = 1;
            break;
        }
    }
    if (!valid_key) {
        fprintf(stderr, "Error: Invalid filter key '%s'. Valid keys: open, high, low, close, vwap\n", arguments.filter_key);
        exit(1);
    }

    // Validate timeframe
    const char *valid_timeframes[] = {"1Min", "5Min", "15Min", "30Min", "1Hour", "1Day", NULL};
    int valid_tf = 0;
    for (int i = 0; valid_timeframes[i]; i++) {
        if (strcmp(arguments.timeframe, valid_timeframes[i]) == 0) {
            valid_tf = 1;
            break;
        }
    }
    if (!valid_tf) {
        fprintf(stderr, "Error: Invalid timeframe '%s'. Valid timeframes: 1Min, 5Min, 15Min, 30Min, 1Hour, 1Day\n", arguments.timeframe);
        exit(1);
    }

    printf("Applying zero-phase Hanning filter (window=%d) on '%s' data...\n", arguments.window_length, arguments.filter_key);
    double *hanning_window = generateHanningWindow(arguments.window_length);
    normalizeCoefficients(hanning_window, arguments.window_length);
    for (size_t i = 0; i < all_data.count; i++) {
        SymbolData *s = &all_data.symbols[i]; double *source_data = NULL;
        if (strcmp(arguments.filter_key, "open") == 0) source_data = s->open_prices;
        else if (strcmp(arguments.filter_key, "high") == 0) source_data = s->high_prices;
        else if (strcmp(arguments.filter_key, "low") == 0) source_data = s->low_prices;
        else if (strcmp(arguments.filter_key, "close") == 0) source_data = s->close_prices;
        else if (strcmp(arguments.filter_key, "vwap") == 0) source_data = s->vwaps;
        if (source_data && s->count > 0) {
            s->filtered_values = malloc(s->count * sizeof(double));
            filtfilt(source_data, s->count, hanning_window, arguments.window_length, s->filtered_values);

            // Perform peak/trough detection on filtered data
            if (s->count > 2) {
                double *derivative = malloc(s->count * sizeof(double));
                calculateFirstDerivative(s->filtered_values, s->count, derivative);
                detectPeaksAndTroughs(derivative, s->count, &s->peak_indices, &s->peak_count, &s->trough_indices, &s->trough_count);
                free(derivative);
                printf("Symbol %s: Found %zu peaks and %zu troughs\n", s->symbol, s->peak_count, s->trough_count);
            } else {
                s->peak_indices = NULL; s->peak_count = 0;
                s->trough_indices = NULL; s->trough_count = 0;
            }
        }
    }
    free(hanning_window);
    json_object *root = json_object_new_object();
    for (size_t i = 0; i < all_data.count; i++) {
        SymbolData *s = &all_data.symbols[i]; json_object *symbol_obj = json_object_new_object();
        json_object *ts_arr = json_object_new_array(); json_object *o_arr = json_object_new_array(); json_object *h_arr = json_object_new_array(); json_object *l_arr = json_object_new_array();
        json_object *c_arr = json_object_new_array(); json_object *v_arr = json_object_new_array(); json_object *n_arr = json_object_new_array(); json_object *vw_arr = json_object_new_array(); json_object *filt_arr = json_object_new_array();
        for (size_t j = 0; j < s->count; j++) {
            json_object_array_add(ts_arr, json_object_new_string(s->timestamps[j])); json_object_array_add(o_arr, json_object_new_double(s->open_prices[j]));
            json_object_array_add(h_arr, json_object_new_double(s->high_prices[j])); json_object_array_add(l_arr, json_object_new_double(s->low_prices[j]));
            json_object_array_add(c_arr, json_object_new_double(s->close_prices[j])); json_object_array_add(v_arr, json_object_new_int64(s->volumes[j]));
            json_object_array_add(n_arr, json_object_new_int64(s->trade_counts[j])); json_object_array_add(vw_arr, json_object_new_double(s->vwaps[j]));
            if (s->filtered_values) { json_object_array_add(filt_arr, json_object_new_double(s->filtered_values[j])); }
        }
        json_object_object_add(symbol_obj, "timestamps", ts_arr); json_object_object_add(symbol_obj, "open", o_arr); json_object_object_add(symbol_obj, "high", h_arr);
        json_object_object_add(symbol_obj, "low", l_arr); json_object_object_add(symbol_obj, "close", c_arr); json_object_object_add(symbol_obj, "volume", v_arr);
        json_object_object_add(symbol_obj, "trade_count", n_arr); json_object_object_add(symbol_obj, "vwap", vw_arr);
        if (s->filtered_values) {
            char filtered_key_name[64]; snprintf(filtered_key_name, sizeof(filtered_key_name), "filtered_%s", arguments.filter_key);
            json_object_object_add(symbol_obj, filtered_key_name, filt_arr);
        }

        // Add peak and trough data
        if (s->peak_count > 0) {
            json_object *peaks_arr = json_object_new_array();
            for (size_t p = 0; p < s->peak_count; p++) {
                json_object *peak_obj = json_object_new_object();
                int idx = s->peak_indices[p];
                json_object_object_add(peak_obj, "index", json_object_new_int(idx));
                json_object_object_add(peak_obj, "timestamp", json_object_new_string(s->timestamps[idx]));
                json_object_object_add(peak_obj, "value", json_object_new_double(s->filtered_values[idx]));
                json_object_array_add(peaks_arr, peak_obj);
            }
            json_object_object_add(symbol_obj, "peaks", peaks_arr);
        }

        if (s->trough_count > 0) {
            json_object *troughs_arr = json_object_new_array();
            for (size_t t = 0; t < s->trough_count; t++) {
                json_object *trough_obj = json_object_new_object();
                int idx = s->trough_indices[t];
                json_object_object_add(trough_obj, "index", json_object_new_int(idx));
                json_object_object_add(trough_obj, "timestamp", json_object_new_string(s->timestamps[idx]));
                json_object_object_add(trough_obj, "value", json_object_new_double(s->filtered_values[idx]));
                json_object_array_add(troughs_arr, trough_obj);
            }
            json_object_object_add(symbol_obj, "troughs", troughs_arr);
        }
        json_object_object_add(root, s->symbol, symbol_obj);
    }
    const char *json_output_str = json_object_to_json_string_ext(root, JSON_C_TO_STRING_PRETTY);

    // Output JSON if not in signal summary mode, or if output file specified
    if (!arguments.print_signals || arguments.output_file) {
        if (arguments.output_file) {
            FILE *outfile = fopen(arguments.output_file, "w");
            if(outfile) {
                fprintf(outfile, "%s\n", json_output_str);
                fclose(outfile);
            }
        } else if (!arguments.print_signals) {
            printf("%s\n", json_output_str);
        }
    }

    // Print signal summary table if requested
    if (arguments.print_signals) {
        print_signal_summary(&all_data, arguments.filter_key, &arguments);
    }

    // <--- COMPREHENSIVE CLEANUP: Freeing all dynamically allocated memory.
    json_object_put(root);

    // Free the symbols string if it was dynamically allocated
    if (arguments.symbols_str) {
        // Check if it was allocated via strdup or malloc
        // (it could be from symbols_from_file, combined, or upper_symbols)
        free(arguments.symbols_str);
    }

    for (size_t i = 0; i < all_data.count; i++) {
        SymbolData *s = &all_data.symbols[i];
        // 1. Free each individual timestamp string
        for (size_t j = 0; j < s->count; j++) {
            free(s->timestamps[j]);
        }
        // 2. Free the data arrays within the struct
        free(s->symbol);
        free(s->timestamps);
        free(s->open_prices);
        free(s->high_prices);
        free(s->low_prices);
        free(s->close_prices);
        free(s->volumes);
        free(s->trade_counts);
        free(s->vwaps);
        free(s->filtered_values);
        free(s->peak_indices);
        free(s->trough_indices);
    }
    // 3. Free the top-level array of structs
    free(all_data.symbols);

    return 0;
}
