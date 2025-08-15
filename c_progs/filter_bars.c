#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <curl/curl.h>
#include <json-c/json.h>
#include <argp.h>

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
typedef struct {
    char *symbols_str;
    char *symbols_file;
    char *timeframe;
    char *output_file;
    char *feed;
    char *filter_key; // Key to filter on (e.g., "close", "vwap")
    int days;
    int window_length;
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

// --- Alpaca API & Data Handling ---
int get_trading_days(int num_days, const char *api_key, const char *api_secret, char **start_date, char **end_date) { /* ... unchanged ... */ 
    CURL *curl; CURLcode res; MemoryStruct chunk; chunk.memory = malloc(1); chunk.size = 0; time_t now = time(NULL);
    int calendar_days_to_fetch = num_days * 2; if (num_days > 20) calendar_days_to_fetch = (int)(num_days * 1.7); if (calendar_days_to_fetch < 30) calendar_days_to_fetch = 30;
    time_t start_time = now - calendar_days_to_fetch * 86400; char start_str[11], end_str[11];
    strftime(start_str, sizeof(start_str), "%Y-%m-%d", localtime(&start_time)); strftime(end_str, sizeof(end_str), "%Y-%m-%d", localtime(&now));
    char url[256]; snprintf(url, sizeof(url), "%s?start=%s&end=%s", ALPACA_CALENDAR_URL, start_str, end_str);
    curl = curl_easy_init();
    if(curl) {
        struct curl_slist *headers = NULL; char api_key_header[128], api_secret_header[128];
        snprintf(api_key_header, sizeof(api_key_header), "APCA-API-KEY-ID: %s", api_key); snprintf(api_secret_header, sizeof(api_secret_header), "APCA-API-SECRET-KEY: %s", api_secret);
        headers = curl_slist_append(headers, api_key_header); headers = curl_slist_append(headers, api_secret_header);
        curl_easy_setopt(curl, CURLOPT_URL, url); curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers); curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteMemoryCallback); curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)&chunk);
        res = curl_easy_perform(curl); curl_easy_cleanup(curl); curl_slist_free_all(headers);
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
    return -1;
}

int fetch_bars(Arguments *args, const char *api_key, const char *api_secret, const char *start_date, const char *end_date, AllData *all_data) {
    CURL *curl; char url[1024]; char *page_token = NULL;
    do {
        if (page_token) {
            snprintf(url, sizeof(url), "%s/stocks/bars?symbols=%s&timeframe=%s&start=%s&end=%s&limit=10000&adjustment=split&feed=%s&sort=asc&page_token=%s", ALPACA_BASE_URL, args->symbols_str, args->timeframe, start_date, end_date, args->feed, page_token);
            free(page_token); page_token = NULL;
        } else {
            snprintf(url, sizeof(url), "%s/stocks/bars?symbols=%s&timeframe=%s&start=%s&end=%s&limit=10000&adjustment=split&feed=%s&sort=asc", ALPACA_BASE_URL, args->symbols_str, args->timeframe, start_date, end_date, args->feed);
        }
        MemoryStruct chunk = { .memory = malloc(1), .size = 0 }; curl = curl_easy_init();
        if(!curl) { free(chunk.memory); return -1; }
        struct curl_slist *headers = NULL; char api_key_header[128], api_secret_header[128];
        snprintf(api_key_header, sizeof(api_key_header), "APCA-API-KEY-ID: %s", api_key); snprintf(api_secret_header, sizeof(api_secret_header), "APCA-API-SECRET-KEY: %s", api_secret);
        headers = curl_slist_append(headers, api_key_header); headers = curl_slist_append(headers, api_secret_header);
        curl_easy_setopt(curl, CURLOPT_URL, url); curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers); curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteMemoryCallback); curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)&chunk);
        CURLcode res = curl_easy_perform(curl); curl_easy_cleanup(curl); curl_slist_free_all(headers);
        if (res != CURLE_OK) { free(chunk.memory); return -1; }
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

char* read_symbols_from_file(const char* filename) { /* ... unchanged ... */ 
    FILE* file = fopen(filename, "r"); if (!file) { return NULL; } fseek(file, 0, SEEK_END); long length = ftell(file); fseek(file, 0, SEEK_SET);
    char* buffer = malloc(length + 1); if (!buffer) { fclose(file); return NULL; } size_t bytes_read = fread(buffer, 1, length, file); fclose(file);
    buffer[bytes_read] = '\0'; for (size_t i = 0; i < bytes_read; i++) { if (buffer[i] == '\n' || buffer[i] == '\r' || buffer[i] == ' ') buffer[i] = ','; }
    return buffer;
}

// --- Argp Parser ---
static char doc[] = "Fetch Alpaca stock data, apply a Hanning filter to a specified data field, and output as JSON.";
static char args_doc[] = "";
static struct argp_option options[] = {
    {.name = "days", .key = 'n', .arg = "NUM", .doc = "Number of trading days to fetch (default: 1)"},
    {.name = "timeframe", .key = 't', .arg = "TF", .doc = "Timeframe (e.g., 1Min, 1H, 1D). Default: 1Min"},
    {.name = "symbols", .key = 's', .arg = "SYMBOLS", .doc = "Comma-separated list of stock symbols"},
    {.name = "file", .key = 'f', .arg = "FILE", .doc = "File with symbols, one per line"},
    {.name = "output", .key = 'o', .arg = "FILE", .doc = "Output file for JSON data (stdout if not specified)"},
    {.name = "window", .key = 'w', .arg = "LEN", .doc = "Hanning window length (odd number > 1). Default: 11"},
    {.name = "filter-on", .key = 'k', .arg = "KEY", .doc = "Data key to filter. One of: open, high, low, close, vwap. (default: close)"},
    {.name = "feed", .key = 600, .arg = "FEED", .doc = "Data feed: 'sip', 'iex', 'otc' (default: sip)"},
    {0}
};
static error_t parse_opt(int key, char *arg, struct argp_state *state) {
    Arguments *arguments = state->input;
    switch (key) {
        case 'n': arguments->days = atoi(arg); break; case 't': arguments->timeframe = arg; break; case 's': arguments->symbols_str = arg; break;
        case 'f': arguments->symbols_file = arg; break; case 'o': arguments->output_file = arg; break; case 'w': arguments->window_length = atoi(arg); break;
        case 'k': arguments->filter_key = arg; break; case 600: arguments->feed = arg; break;
        case ARGP_KEY_ARG: return ARGP_ERR_UNKNOWN; default: return ARGP_ERR_UNKNOWN;
    }
    return 0;
}
static struct argp argp = { .options = options, .parser = parse_opt, .args_doc = args_doc, .doc = doc };

// --- Main Execution ---
int main(int argc, char **argv) {
    Arguments arguments;
    arguments.days = 1; arguments.timeframe = "1Min"; arguments.symbols_str = NULL; arguments.symbols_file = NULL;
    arguments.output_file = NULL; arguments.window_length = 11; arguments.feed = "sip"; arguments.filter_key = "close";
    argp_parse(&argp, argc, argv, 0, 0, &arguments);
    if (strcmp(arguments.filter_key, "open") != 0 && strcmp(arguments.filter_key, "high") != 0 && strcmp(arguments.filter_key, "low") != 0 && strcmp(arguments.filter_key, "close") != 0 && strcmp(arguments.filter_key, "vwap") != 0) {
        fprintf(stderr, "Error: Invalid key for --filter-on. Must be one of: open, high, low, close, vwap.\n"); exit(1);
    }
    char *symbols_from_file = NULL;
    if (arguments.symbols_file) { symbols_from_file = read_symbols_from_file(arguments.symbols_file); }
    if (!arguments.symbols_str && symbols_from_file) { arguments.symbols_str = symbols_from_file; }
    else if (arguments.symbols_str && symbols_from_file) {
        char *combined = malloc(strlen(arguments.symbols_str) + strlen(symbols_from_file) + 2);
        sprintf(combined, "%s,%s", arguments.symbols_str, symbols_from_file);
        free(symbols_from_file); arguments.symbols_str = combined;
    }
    if (!arguments.symbols_str) { fprintf(stderr, "Error: No symbols provided.\n"); exit(1); }
    const char *api_key = getenv("APCA_API_KEY_ID"); const char *api_secret = getenv("APCA_API_SECRET_KEY");
    if (!api_key || !api_secret) { fprintf(stderr, "Error: API keys not set in environment.\n"); exit(1); }
    curl_global_init(CURL_GLOBAL_ALL);
    char *start_date = NULL, *end_date = NULL;
    if (get_trading_days(arguments.days, api_key, api_secret, &start_date, &end_date) != 0) { exit(1); }
    printf("Data range: from %s to %s\n", start_date, end_date);
    AllData all_data = { .symbols = NULL, .count = 0 };
    if (fetch_bars(&arguments, api_key, api_secret, start_date, end_date, &all_data) != 0) { exit(1); }
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
    if (arguments.output_file) {
        FILE *outfile = fopen(arguments.output_file, "w"); if(outfile) { fprintf(outfile, "%s\n", json_output_str); fclose(outfile); }
    } else { printf("%s\n", json_output_str); }

    // <--- COMPREHENSIVE CLEANUP: Freeing all dynamically allocated memory.
    json_object_put(root);
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
    // 4. Free other miscellaneous allocations
    free(start_date);
    free(end_date);
    if (symbols_from_file) free(arguments.symbols_str);
    curl_global_cleanup();

    return 0;
}
