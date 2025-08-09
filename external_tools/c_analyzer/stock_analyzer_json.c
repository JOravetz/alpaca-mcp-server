#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <json-c/json.h>
#include <math.h>
#include <unistd.h>
#include <time.h>
#include <getopt.h>

#define MAX_SYMBOLS 10000
#define MAX_LINE_LENGTH 256
#define MAX_URL_LENGTH 131072  // Doubled to 128KB
#define MAX_RESPONSE_SIZE 10*1024*1024
#define MAX_FILENAME 256
#define SYMBOLS_PER_BATCH 100
#define DEFAULT_SYMBOL_FILE "major-exchange-symbols.txt"

typedef struct {
    char symbol[16];
    double price;
    double prev_close;
    double day_close;
    double percent;
    double gradient_full;
    double gradient_recent;
    double gradient_change;
    int volume;
    int volume_change;
    int trades;
    int trades_change;
    char timestamp[64];
    char market_session[16];
} StockData;

typedef struct {
    char *data;
    size_t size;
} APIResponse;

// Global variables for API credentials
char API_KEY[256];
char API_SECRET[256];

// Function to write API response data
size_t WriteCallback(void *contents, size_t size, size_t nmemb, APIResponse *response) {
    size_t total_size = size * nmemb;
    char *ptr = realloc(response->data, response->size + total_size + 1);
    if (ptr == NULL) {
        printf("Not enough memory (realloc returned NULL)\n");
        return 0;
    }
    
    response->data = ptr;
    memcpy(&(response->data[response->size]), contents, total_size);
    response->size += total_size;
    response->data[response->size] = '\0';
    
    return total_size;
}

// Load API credentials from environment variables
int load_credentials() {
    const char* key = getenv("APCA_API_KEY_ID");
    const char* secret = getenv("APCA_API_SECRET_KEY");
    
    if (key == NULL || secret == NULL) {
        fprintf(stderr, "Error: APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables must be set\n");
        return -1;
    }
    
    strncpy(API_KEY, key, sizeof(API_KEY) - 1);
    strncpy(API_SECRET, secret, sizeof(API_SECRET) - 1);
    API_KEY[sizeof(API_KEY) - 1] = '\0';
    API_SECRET[sizeof(API_SECRET) - 1] = '\0';
    
    return 0;
}

// Get current NYC/ET time for market session detection
void get_et_time(struct tm *et_time) {
    time_t now;
    time(&now);
    
    // Set timezone to Eastern Time
    setenv("TZ", "America/New_York", 1);
    tzset();
    
    // Get local time in ET
    localtime_r(&now, et_time);
    
    // Reset timezone to system default
    unsetenv("TZ");
    tzset();
}

// Determine market session based on NYC/ET time
// Pre-market: 4:00 AM - 9:30 AM ET
// Regular: 9:30 AM - 4:00 PM ET  
// Post-market: 4:00 PM - 8:00 PM ET
// Closed: 8:00 PM - 4:00 AM ET
const char* get_market_session() {
    struct tm et_time;
    get_et_time(&et_time);
    
    int hour = et_time.tm_hour;
    int minute = et_time.tm_min;
    int total_minutes = hour * 60 + minute;
    
    // Define market sessions in minutes from midnight
    int premarket_start = 4 * 60;      // 4:00 AM = 240 minutes
    int regular_start = 9 * 60 + 30;   // 9:30 AM = 570 minutes
    int regular_end = 16 * 60;         // 4:00 PM = 960 minutes
    int postmarket_end = 20 * 60;      // 8:00 PM = 1200 minutes
    
    if (total_minutes >= premarket_start && total_minutes < regular_start) {
        return "pre-market";
    } else if (total_minutes >= regular_start && total_minutes < regular_end) {
        return "regular";
    } else if (total_minutes >= regular_end && total_minutes < postmarket_end) {
        return "post-market";
    } else {
        return "closed";
    }
}

// Read symbols from file
int read_symbols(const char* filename, char symbols[][16], int max_symbols) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        fprintf(stderr, "Error opening file: %s\n", filename);
        return -1;
    }
    
    char line[MAX_LINE_LENGTH];
    int count = 0;
    
    while (fgets(line, sizeof(line), file) && count < max_symbols) {
        char *token = strtok(line, " \t\n");
        if (token && strlen(token) <= 15) {
            strncpy(symbols[count], token, 15);
            symbols[count][15] = '\0';
            count++;
        }
    }
    
    fclose(file);
    return count;
}

// Get stock snapshots from Alpaca API
int get_stock_snapshots(char symbols[][16], int symbol_count, StockData *results, int *result_count) {
    CURL *curl;
    CURLcode res;
    APIResponse response = {0};
    
    curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL\n");
        return -1;
    }
    
    // Build symbols parameter string with bounds checking
    char symbols_param[MAX_URL_LENGTH] = "";
    int param_length = 0;
    const int base_url_len = 56; // Length of "https://data.alpaca.markets/v2/stocks/snapshots?symbols="
    
    for (int i = 0; i < symbol_count; i++) {
        int symbol_len = strlen(symbols[i]);
        int needed = symbol_len + (i > 0 ? 1 : 0); // +1 for comma if not first
        
        if (param_length + needed + base_url_len >= MAX_URL_LENGTH - 1) {
            fprintf(stderr, "Warning: URL would be too long, truncating symbol list at %d symbols\n", i);
            break;
        }
        
        if (i > 0) {
            strcat(symbols_param, ",");
            param_length++;
        }
        strcat(symbols_param, symbols[i]);
        param_length += symbol_len;
    }
    
    // Build URL for data endpoint
    char url[MAX_URL_LENGTH];
    snprintf(url, sizeof(url), "https://data.alpaca.markets/v2/stocks/snapshots?symbols=%s", symbols_param);
    
    // Set headers
    struct curl_slist *headers = NULL;
    char auth_header[512];
    snprintf(auth_header, sizeof(auth_header), "APCA-API-KEY-ID: %s", API_KEY);
    headers = curl_slist_append(headers, auth_header);
    
    snprintf(auth_header, sizeof(auth_header), "APCA-API-SECRET-KEY: %s", API_SECRET);
    headers = curl_slist_append(headers, auth_header);
    
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    
    res = curl_easy_perform(curl);
    
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "CURL failed: %s\n", curl_easy_strerror(res));
        if (response.data) free(response.data);
        return -1;
    }
    
    // Parse JSON response
    json_object *json = json_object_new_string(response.data);
    json_object *parsed_json = json_tokener_parse(response.data);
    if (!parsed_json) {
        fprintf(stderr, "Failed to parse JSON response\n");
        if (response.data) free(response.data);
        return -1;
    }
    json = parsed_json;
    
    *result_count = 0;
    
    // Load previous values from cache
    json_object *cache_json = NULL;
    FILE *cache_file = fopen("previous_results.json", "r");
    if (cache_file) {
        fseek(cache_file, 0, SEEK_END);
        long cache_size = ftell(cache_file);
        rewind(cache_file);
        
        char *cache_data = malloc(cache_size + 1);
        if (cache_data) {
            size_t bytes_read = fread(cache_data, 1, cache_size, cache_file);
            if (bytes_read != (size_t)cache_size) {
                fprintf(stderr, "Warning: Cache file read incomplete (%zu/%ld bytes)\n", bytes_read, cache_size);
            }
            cache_data[cache_size] = '\0';
            cache_json = json_tokener_parse(cache_data);
            free(cache_data);
        }
        fclose(cache_file);
    }
    
    // Process each symbol's snapshot data
    for (int i = 0; i < symbol_count; i++) {
        json_object *symbol_data;
        if (!json_object_object_get_ex(json, symbols[i], &symbol_data)) continue;
        
        json_object *latest_trade, *minute_bar, *daily_bar, *prev_daily_bar;
        if (!json_object_object_get_ex(symbol_data, "latestTrade", &latest_trade) ||
            !json_object_object_get_ex(symbol_data, "minuteBar", &minute_bar) ||
            !json_object_object_get_ex(symbol_data, "dailyBar", &daily_bar)) continue;
        json_object_object_get_ex(symbol_data, "prevDailyBar", &prev_daily_bar);
        
        // Extract price data
        json_object *price_json, *day_close_json, *trades_json, *volume_json, *timestamp_json;
        if (!json_object_object_get_ex(latest_trade, "p", &price_json) ||
            !json_object_object_get_ex(daily_bar, "c", &day_close_json) ||
            !json_object_object_get_ex(minute_bar, "n", &trades_json) ||
            !json_object_object_get_ex(minute_bar, "v", &volume_json)) continue;
        json_object_object_get_ex(latest_trade, "t", &timestamp_json);
        
        double price = json_object_get_double(price_json);
        double day_close = json_object_get_double(day_close_json);
        int trades = json_object_get_int(trades_json);
        int volume = json_object_get_int(volume_json);
        
        // Skip if insufficient trades (minimum threshold)
        if (trades < 50) continue;
        
        // Calculate percentage change using previous day's close (matching snapshot.py logic)
        double prev_close_price = 0.0;
        if (prev_daily_bar) {
            json_object *prev_close;
            if (json_object_object_get_ex(prev_daily_bar, "c", &prev_close)) {
                prev_close_price = json_object_get_double(prev_close);
            }
        }
        
        // If no previous close available, skip this symbol
        if (prev_close_price <= 0.0) continue;
        
        // Calculate percent change exactly as snapshot.py does:
        // percent_change = ((price - prev_close) / max(prev_close, 0.01)) * 100
        double percent = ((price - prev_close_price) / fmax(prev_close_price, 0.01)) * 100.0;
        double gradient_full = percent / 2.0;
        double gradient_recent = ((price - day_close) / day_close) * 100.0;
        
        // Get previous values from cache for change calculations
        double prev_gradient_recent = 0.0;
        int prev_volume = 0;
        int prev_trades = 0;
        
        if (cache_json) {
            json_object *cached_symbol;
            if (json_object_object_get_ex(cache_json, symbols[i], &cached_symbol)) {
                json_object *cached_gradient, *cached_vol, *cached_tr;
                if (json_object_object_get_ex(cached_symbol, "gradient_recent", &cached_gradient))
                    prev_gradient_recent = json_object_get_double(cached_gradient);
                if (json_object_object_get_ex(cached_symbol, "volume", &cached_vol))
                    prev_volume = json_object_get_int(cached_vol);
                if (json_object_object_get_ex(cached_symbol, "trades", &cached_tr))
                    prev_trades = json_object_get_int(cached_tr);
            }
        }
        
        // Store result
        StockData *result = &results[*result_count];
        strncpy(result->symbol, symbols[i], sizeof(result->symbol) - 1);
        result->symbol[sizeof(result->symbol) - 1] = '\0';
        result->price = price;
        result->prev_close = prev_close_price;
        result->day_close = day_close;
        result->percent = percent;
        result->gradient_full = gradient_full;
        result->gradient_recent = gradient_recent;
        result->gradient_change = gradient_recent - prev_gradient_recent;
        result->volume = volume;
        result->volume_change = volume - prev_volume;
        result->trades = trades;
        result->trades_change = trades - prev_trades;
        
        // Store market session
        strncpy(result->market_session, get_market_session(), sizeof(result->market_session) - 1);
        result->market_session[sizeof(result->market_session) - 1] = '\0';
        
        // Store timestamp
        if (timestamp_json) {
            const char *timestamp_str = json_object_get_string(timestamp_json);
            if (timestamp_str) {
                strncpy(result->timestamp, timestamp_str, sizeof(result->timestamp) - 1);
                result->timestamp[sizeof(result->timestamp) - 1] = '\0';
            }
        } else {
            strcpy(result->timestamp, "");
        }
        
        (*result_count)++;
    }
    
    // Save current results to cache
    json_object *new_cache = json_object_new_object();
    for (int i = 0; i < *result_count; i++) {
        json_object *stock_cache = json_object_new_object();
        json_object_object_add(stock_cache, "gradient_recent", json_object_new_double(results[i].gradient_recent));
        json_object_object_add(stock_cache, "volume", json_object_new_int(results[i].volume));
        json_object_object_add(stock_cache, "trades", json_object_new_int(results[i].trades));
        json_object_object_add(new_cache, results[i].symbol, stock_cache);
    }
    
    FILE *new_cache_file = fopen("previous_results.json", "w");
    if (new_cache_file) {
        const char *cache_string = json_object_to_json_string(new_cache);
        fputs(cache_string, new_cache_file);
        fclose(new_cache_file);
    }
    
    // Cleanup
    if (cache_json) json_object_put(cache_json);
    json_object_put(new_cache);
    json_object_put(json);
    if (response.data) free(response.data);
    
    return 0;
}

// Compare function for sorting by trades (descending)
int compare_by_trades(const void *a, const void *b) {
    const StockData *stock_a = (const StockData *)a;
    const StockData *stock_b = (const StockData *)b;
    return stock_b->trades - stock_a->trades;
}

// Print help message
void print_help(const char *program_name) {
    printf("Stock Analyzer JSON - Real-time stock market analysis tool\n");
    printf("Usage: %s [OPTIONS]\n\n", program_name);
    printf("Options:\n");
    printf("  -f, --file FILE         Symbol list file (default: %s)\n", DEFAULT_SYMBOL_FILE);
    printf("  -s, --symbols SYMBOLS   Comma-separated list of stock symbols\n");
    printf("                          (overrides file input)\n");
    printf("  -a, --all               Output all stocks (default: top 25 by trades)\n");
    printf("  -h, --help              Display this help message and exit\n");
    printf("\n");
    printf("Environment Variables:\n");
    printf("  APCA_API_KEY_ID         Alpaca API key (required)\n");
    printf("  APCA_API_SECRET_KEY     Alpaca API secret (required)\n");
    printf("\n");
    printf("Examples:\n");
    printf("  %s                                    # Use default file, top 25\n", program_name);
    printf("  %s -f combined.lis                    # Use custom symbol file, top 25\n", program_name);
    printf("  %s -s AAPL,GOOGL,MSFT                 # Analyze specific symbols\n", program_name);
    printf("  %s -a -f combined.lis                 # Output ALL stocks from file\n", program_name);
    printf("  echo \"TSLA\" | %s                      # Read symbols from stdin\n", program_name);
    printf("\n");
    printf("Output:\n");
    printf("  JSON formatted stocks to stdout (top 25 by default, all with -a)\n");
    printf("  Progress messages to stderr\n");
}

// Parse comma-separated symbols string
int parse_symbol_string(const char *symbol_string, char symbols[][16], int max_symbols) {
    char *str_copy = strdup(symbol_string);
    if (!str_copy) {
        fprintf(stderr, "Error: Memory allocation failed\n");
        return -1;
    }
    
    int count = 0;
    char *token = strtok(str_copy, ",");
    
    while (token != NULL && count < max_symbols) {
        // Remove leading/trailing whitespace
        while (*token == ' ' || *token == '\t') token++;
        int len = strlen(token);
        while (len > 0 && (token[len-1] == ' ' || token[len-1] == '\t' || token[len-1] == '\n')) {
            token[--len] = '\0';
        }
        
        if (len > 0 && len <= 15) {
            strncpy(symbols[count], token, 15);
            symbols[count][15] = '\0';
            count++;
        }
        
        token = strtok(NULL, ",");
    }
    
    free(str_copy);
    return count;
}

// Generate JSON output for stocks
void generate_json_output(StockData *results, int count, int output_all) {
    // Sort by trades (descending)
    qsort(results, count, sizeof(StockData), compare_by_trades);
    
    // Determine output count
    int output_count = output_all ? count : ((count < 25) ? count : 25);
    
    json_object *json = json_object_new_object();
    json_object *stocks_array = json_object_new_array();
    
    const char *title = output_all ? "All Processed Stocks" : "Top 25 Active Stocks";
    json_object_object_add(json, "title", json_object_new_string(title));
    json_object_object_add(json, "current_market_session", json_object_new_string(get_market_session()));
    json_object_object_add(json, "total_processed", json_object_new_int(count));
    json_object_object_add(json, "results_count", json_object_new_int(output_count));
    
    for (int i = 0; i < output_count; i++) {
        json_object *stock = json_object_new_object();
        
        json_object_object_add(stock, "rank", json_object_new_int(i + 1));
        json_object_object_add(stock, "symbol", json_object_new_string(results[i].symbol));
        json_object_object_add(stock, "price", json_object_new_double(results[i].price));
        json_object_object_add(stock, "prev_close", json_object_new_double(results[i].prev_close));
        json_object_object_add(stock, "day_close", json_object_new_double(results[i].day_close));
        json_object_object_add(stock, "percent_change", json_object_new_double(results[i].percent));
        json_object_object_add(stock, "gradient_full", json_object_new_double(results[i].gradient_full));
        json_object_object_add(stock, "gradient_recent", json_object_new_double(results[i].gradient_recent));
        json_object_object_add(stock, "gradient_change", json_object_new_double(results[i].gradient_change));
        json_object_object_add(stock, "volume", json_object_new_int(results[i].volume));
        json_object_object_add(stock, "volume_change", json_object_new_int(results[i].volume_change));
        json_object_object_add(stock, "trades", json_object_new_int(results[i].trades));
        json_object_object_add(stock, "trades_change", json_object_new_int(results[i].trades_change));
        json_object_object_add(stock, "market_session", json_object_new_string(results[i].market_session));
        json_object_object_add(stock, "timestamp", json_object_new_string(results[i].timestamp));
        
        json_object_array_add(stocks_array, stock);
    }
    
    json_object_object_add(json, "stocks", stocks_array);
    
    // Print JSON to stdout
    const char *json_string = json_object_to_json_string_ext(json, JSON_C_TO_STRING_PRETTY);
    printf("%s\n", json_string);
    
    // Cleanup
    json_object_put(json);
}

int main(int argc, char *argv[]) {
    char *symbol_file = NULL;
    char *symbol_string = NULL;
    int output_all = 0;  // Default is filtered (top 25)
    
    // Define long options
    static struct option long_options[] = {
        {"file",    required_argument, 0, 'f'},
        {"symbols", required_argument, 0, 's'},
        {"all",     no_argument,       0, 'a'},
        {"help",    no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };
    
    // Parse command line arguments
    int c;
    int option_index = 0;
    while ((c = getopt_long(argc, argv, "f:s:ah", long_options, &option_index)) != -1) {
        switch (c) {
            case 'f':
                symbol_file = optarg;
                break;
            case 's':
                symbol_string = optarg;
                break;
            case 'a':
                output_all = 1;
                break;
            case 'h':
                print_help(argv[0]);
                return 0;
            case '?':
                fprintf(stderr, "Unknown option. Use -h for help.\n");
                return 1;
            default:
                abort();
        }
    }
    
    // Load API credentials
    if (load_credentials() != 0) {
        return 1;
    }
    
    // Initialize curl
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    char symbols[MAX_SYMBOLS][16];
    int symbol_count = 0;
    
    // Determine input source and load symbols
    if (symbol_string != NULL) {
        // Use command-line symbols (highest priority)
        symbol_count = parse_symbol_string(symbol_string, symbols, MAX_SYMBOLS);
        if (symbol_count <= 0) {
            fprintf(stderr, "Error: No valid symbols in provided string\n");
            curl_global_cleanup();
            return 1;
        }
        fprintf(stderr, "Loaded %d symbols from command line\n", symbol_count);
    } else if (symbol_file == NULL && !isatty(fileno(stdin))) {
        // Check if input is being piped from stdin (only if no file specified)
        char line[MAX_LINE_LENGTH];
        symbol_count = 0;
        
        while (fgets(line, sizeof(line), stdin) && symbol_count < MAX_SYMBOLS) {
            // Check if line contains comma-separated symbols
            if (strchr(line, ',') != NULL) {
                int parsed = parse_symbol_string(line, &symbols[symbol_count], MAX_SYMBOLS - symbol_count);
                if (parsed > 0) {
                    symbol_count += parsed;
                }
            } else {
                // Single symbol per line
                char *token = strtok(line, " \t\n");
                if (token && strlen(token) <= 15) {
                    strncpy(symbols[symbol_count], token, 15);
                    symbols[symbol_count][15] = '\0';
                    symbol_count++;
                }
            }
        }
        
        if (symbol_count > 0) {
            fprintf(stderr, "Loaded %d symbols from stdin\n", symbol_count);
        } else {
            fprintf(stderr, "Error: No valid symbols read from stdin\n");
            curl_global_cleanup();
            return 1;
        }
    } else {
        // Use file input (default or specified)
        if (symbol_file == NULL) {
            symbol_file = DEFAULT_SYMBOL_FILE;
        }
        
        symbol_count = read_symbols(symbol_file, symbols, MAX_SYMBOLS);
        if (symbol_count <= 0) {
            fprintf(stderr, "Error: No symbols loaded from %s\n", symbol_file);
            curl_global_cleanup();
            return 1;
        }
        fprintf(stderr, "Loaded %d symbols from %s (limited to first %d for processing)\n", 
                symbol_count, symbol_file, MAX_SYMBOLS);
    }
    
    // Allocate memory for results
    StockData *results = malloc(symbol_count * sizeof(StockData));
    if (!results) {
        fprintf(stderr, "Error: Failed to allocate memory for results\n");
        curl_global_cleanup();
        return 1;
    }
    
    int result_count;
    
    // Get stock data from Alpaca API
    if (get_stock_snapshots(symbols, symbol_count, results, &result_count) != 0) {
        fprintf(stderr, "Error: Failed to get stock snapshots\n");
        free(results);
        curl_global_cleanup();
        return 1;
    }
    
    fprintf(stderr, "Successfully processed %d stocks with sufficient trading activity\n", result_count);
    
    // Generate JSON output
    generate_json_output(results, result_count, output_all);
    
    // Cleanup
    free(results);
    curl_global_cleanup();
    
    return 0;
}