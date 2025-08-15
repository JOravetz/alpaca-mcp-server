#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <json-c/json.h>
#include <math.h>
#include <unistd.h>
#include <time.h>
#include <ctype.h>

#define MAX_LINE_LENGTH 256
#define MAX_URL_LENGTH 65536
#define MAX_RESPONSE_SIZE 10000*1024*1024
#define MAX_FILENAME 256
#define SYMBOLS_PER_BATCH 10000

typedef struct {
    char symbol[16];
    double price;
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

// Check if current time is during pre-market hours (4:00 AM - 9:30 AM ET)
int is_premarket() {
    time_t now;
    struct tm *et_time;

    // Get current time
    time(&now);

    // Convert to Eastern Time (UTC-5 or UTC-4 for DST)
    // For simplicity, we'll use localtime and assume the system is in ET
    // In production, you'd want to properly handle timezone conversion
    et_time = localtime(&now);

    int hour = et_time->tm_hour;
    int minute = et_time->tm_min;

    // Pre-market is 4:00 AM to 9:30 AM ET
    if (hour >= 4 && hour < 9) {
        return 1;
    } else if (hour == 9 && minute < 30) {
        return 1;
    }

    return 0;
}

// Convert string to uppercase
void str_to_upper(char *str) {
    for (int i = 0; str[i]; i++) {
        str[i] = toupper((unsigned char)str[i]);
    }
}

// Parse comma-separated symbols from string
int parse_symbols_from_string(const char* symbols_str, char ***symbols) {
    if (!symbols_str || strlen(symbols_str) == 0) {
        return -1;
    }

    // Make a copy of the string to tokenize
    char *str_copy = strdup(symbols_str);
    if (!str_copy) {
        return -1;
    }

    int count = 0;
    int capacity = 100;

    *symbols = malloc(capacity * sizeof(char*));
    if (!*symbols) {
        free(str_copy);
        return -1;
    }

    // Tokenize by comma
    char *token = strtok(str_copy, ",");
    while (token) {
        // Skip leading/trailing whitespace
        while (*token && isspace(*token)) token++;
        char *end = token + strlen(token) - 1;
        while (end > token && isspace(*end)) *end-- = '\0';

        if (strlen(token) > 0 && strlen(token) <= 10) {
            if (count >= capacity) {
                capacity *= 2;
                char **temp = realloc(*symbols, capacity * sizeof(char*));
                if (!temp) {
                    for (int i = 0; i < count; i++) free((*symbols)[i]);
                    free(*symbols);
                    free(str_copy);
                    return -1;
                }
                *symbols = temp;
            }

            (*symbols)[count] = malloc(16);
            if (!(*symbols)[count]) {
                for (int i = 0; i < count; i++) free((*symbols)[i]);
                free(*symbols);
                free(str_copy);
                return -1;
            }

            strncpy((*symbols)[count], token, 15);
            (*symbols)[count][15] = '\0';
            str_to_upper((*symbols)[count]);  // Convert to uppercase
            count++;
        }

        token = strtok(NULL, ",");
    }

    free(str_copy);
    return count;
}

// Read symbols from file
int read_symbols(const char* filename, char ***symbols) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        fprintf(stderr, "Error opening file: %s\n", filename);
        return -1;
    }

    char line[MAX_LINE_LENGTH];
    int count = 0;
    int capacity = 1000;

    *symbols = malloc(capacity * sizeof(char*));
    if (!*symbols) {
        fclose(file);
        return -1;
    }

    while (fgets(line, sizeof(line), file)) {
        char *token = strtok(line, " \t\n");
        if (token && strlen(token) <= 10) {
            if (count >= capacity) {
                capacity *= 2;
                char **temp = realloc(*symbols, capacity * sizeof(char*));
                if (!temp) {
                    for (int i = 0; i < count; i++) free((*symbols)[i]);
                    free(*symbols);
                    fclose(file);
                    return -1;
                }
                *symbols = temp;
            }

            (*symbols)[count] = malloc(16);
            if (!(*symbols)[count]) {
                for (int i = 0; i < count; i++) free((*symbols)[i]);
                free(*symbols);
                fclose(file);
                return -1;
            }

            strncpy((*symbols)[count], token, 15);
            (*symbols)[count][15] = '\0';
            count++;
        }
    }

    fclose(file);
    return count;
}

// Get stock snapshots from Alpaca API
int get_stock_snapshots(char **symbols, int symbol_count, StockData *results, int *result_count, double max_price, double min_percent_change, int min_trades, int all_symbols, int raw_output) {
    CURL *curl;
    CURLcode res;
    APIResponse response = {0};

    curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL\n");
        return -1;
    }

    // Build symbols parameter string
    char symbols_param[MAX_URL_LENGTH] = "";
    for (int i = 0; i < symbol_count; i++) {
        if (i > 0) strcat(symbols_param, ",");
        strcat(symbols_param, symbols[i]);
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

    // Output raw JSON if requested
    if (raw_output) {
        const char *raw_json_string = json_object_to_json_string_ext(json, JSON_C_TO_STRING_PRETTY);
        printf("=== RAW SNAPSHOT DATA ===\n%s\n=== END RAW DATA ===\n\n", raw_json_string);
    }

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

        // Skip filtering if all_symbols flag is set
        if (!all_symbols) {
            // Skip if price exceeds maximum threshold
            if (price > max_price) continue;

            // Skip if insufficient trades (minimum threshold)
            if (trades < min_trades) continue;
        }

        // Calculate percentage change and gradients
        double reference_price;

        // Check if we're in pre-market hours
        if (is_premarket()) {
            // During pre-market, use dailyBar.c as reference (yesterday's close)
            reference_price = day_close;
        } else {
            // During regular hours, use prevDailyBar.c as reference
            if (prev_daily_bar) {
                json_object *prev_close;
                if (json_object_object_get_ex(prev_daily_bar, "c", &prev_close)) {
                    reference_price = json_object_get_double(prev_close);
                } else {
                    reference_price = day_close; // Fallback if no prev_daily_bar
                }
            } else {
                reference_price = day_close; // Fallback if no prev_daily_bar
            }
        }

        double percent = ((price - reference_price) / reference_price) * 100.0;
        double gradient_full = percent / 2.0;
        double gradient_recent = ((price - day_close) / day_close) * 100.0;

        // Skip if percent change is below minimum threshold (only if not all_symbols mode)
        if (!all_symbols && percent <= min_percent_change) continue;

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
        result->day_close = day_close;
        result->percent = percent;
        result->gradient_full = gradient_full;
        result->gradient_recent = gradient_recent;
        result->gradient_change = gradient_recent - prev_gradient_recent;
        result->volume = volume;
        result->volume_change = volume - prev_volume;
        result->trades = trades;
        result->trades_change = trades - prev_trades;

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

// Generate JSON output for top N active stocks
void generate_json_output(StockData *results, int count, int max_output, int all_symbols) {
    // Sort by trades (descending)
    qsort(results, count, sizeof(StockData), compare_by_trades);

    // Determine output count: if -a flag is set, output all; otherwise limit to max_output
    int output_count;
    if (all_symbols) {
        output_count = count;  // Output all stocks when -a is specified
    } else {
        output_count = (count < max_output) ? count : max_output;  // Limit to requested number
    }

    json_object *json = json_object_new_object();
    json_object *stocks_array = json_object_new_array();

    json_object_object_add(json, "title", json_object_new_string("Most Active Stocks"));
    // When -a is specified, max_output should reflect the actual count being output
    json_object_object_add(json, "max_output", json_object_new_int(all_symbols ? output_count : max_output));
    json_object_object_add(json, "total_processed", json_object_new_int(count));
    json_object_object_add(json, "results_count", json_object_new_int(output_count));

    for (int i = 0; i < output_count; i++) {
        json_object *stock = json_object_new_object();

        json_object_object_add(stock, "rank", json_object_new_int(i + 1));
        json_object_object_add(stock, "symbol", json_object_new_string(results[i].symbol));
        json_object_object_add(stock, "price", json_object_new_double(results[i].price));
        json_object_object_add(stock, "day_close", json_object_new_double(results[i].day_close));
        json_object_object_add(stock, "percent_change", json_object_new_double(results[i].percent));
        json_object_object_add(stock, "gradient_full", json_object_new_double(results[i].gradient_full));
        json_object_object_add(stock, "gradient_recent", json_object_new_double(results[i].gradient_recent));
        json_object_object_add(stock, "gradient_change", json_object_new_double(results[i].gradient_change));
        json_object_object_add(stock, "volume", json_object_new_int(results[i].volume));
        json_object_object_add(stock, "volume_change", json_object_new_int(results[i].volume_change));
        json_object_object_add(stock, "trades", json_object_new_int(results[i].trades));
        json_object_object_add(stock, "trades_change", json_object_new_int(results[i].trades_change));
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

// Print usage information
void print_help(const char *program_name) {
    printf("Stock Analyzer - Real-time stock market analysis tool\n");
    printf("Connects to Alpaca API to analyze stock snapshots and detect high-activity stocks\n\n");
    printf("Usage: %s [OPTIONS]\n\n", program_name);
    printf("Options:\n");
    printf("  -n NUM        Maximum number of stocks to output (default: 5)\n");
    printf("  -a            Output ALL symbols without filtering (overrides -n, disables -p, -c, -t)\n");
    printf("  -r            Output raw snapshot JSON data in addition to processed results\n");
    printf("  -s SYMBOLS    Comma-separated list of symbols to analyze (e.g., \"AAPL,MSFT,GOOGL\")\n");
    printf("                Symbols are automatically converted to uppercase\n");
    printf("  -p PRICE      Maximum stock price filter in USD (default: 30.0)\n");
    printf("  -c PERCENT    Minimum percent change threshold (default: 20.0)\n");
    printf("  -t TRADES     Minimum number of trades threshold (default: 1000)\n");
    printf("  -f FILE       Symbol list file to use (default: combined.lis)\n");
    printf("  -h, --help    Show this help message and exit\n\n");
    printf("Environment Variables Required:\n");
    printf("  APCA_API_KEY_ID      Alpaca API key ID\n");
    printf("  APCA_API_SECRET_KEY  Alpaca API secret key\n\n");
    printf("Examples:\n");
    printf("  %s                           # Use default settings\n", program_name);
    printf("  %s -n 10 -p 50.0             # Show top 10 stocks under $50\n", program_name);
    printf("  %s -c 10.0 -t 500 -f sp500.lis  # 10%% change threshold, 500 trades minimum\n", program_name);
    printf("  %s -a                        # Output ALL stocks without any filtering\n", program_name);
    printf("  %s -s \"AAPL,MSFT,GOOGL\" -a   # Analyze and output ALL specified symbols\n", program_name);
    printf("\nOutput: JSON formatted list of most active stocks ranked by trading volume\n");
}

int main(int argc, char *argv[]) {
    int max_output = 5;
    double max_price = 30.0;
    double min_percent_change = 20.0;
    int min_trades = 1000;
    const char *symbol_file = "combined.lis";
    const char *symbol_string = NULL;
    int all_symbols = 0;  // Flag for outputting all symbols without filtering
    int raw_output = 0;   // Flag for outputting raw JSON snapshot data

    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_help(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {
            char *endptr;
            long val = strtol(argv[++i], &endptr, 10);
            if (*endptr != '\0' || val <= 0 || val > 10000) {
                fprintf(stderr, "Error: -n requires a positive integer (1-10000), got '%s'\n", argv[i]);
                return 1;
            }
            max_output = (int)val;
        } else if (strcmp(argv[i], "-a") == 0) {
            all_symbols = 1;  // Enable all symbols output (no filtering)
        } else if (strcmp(argv[i], "-r") == 0) {
            raw_output = 1;   // Enable raw JSON snapshot output
        } else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
            symbol_string = argv[++i];  // Get comma-separated symbols
        } else if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
            char *endptr;
            double val = strtod(argv[++i], &endptr);
            if (*endptr != '\0' || val <= 0 || val > 1000000) {
                fprintf(stderr, "Error: -p requires a positive price (0.01-1000000), got '%s'\n", argv[i]);
                return 1;
            }
            max_price = val;
        } else if (strcmp(argv[i], "-c") == 0 && i + 1 < argc) {
            char *endptr;
            double val = strtod(argv[++i], &endptr);
            if (*endptr != '\0' || val < -100 || val > 10000) {
                fprintf(stderr, "Error: -c requires a percent change (-100 to 10000), got '%s'\n", argv[i]);
                return 1;
            }
            min_percent_change = val;
        } else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) {
            char *endptr;
            long val = strtol(argv[++i], &endptr, 10);
            if (*endptr != '\0' || val < 0 || val > 1000000000) {
                fprintf(stderr, "Error: -t requires a non-negative integer (0-1000000000), got '%s'\n", argv[i]);
                return 1;
            }
            min_trades = (int)val;
        } else if (strcmp(argv[i], "-f") == 0 && i + 1 < argc) {
            symbol_file = argv[++i];
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            fprintf(stderr, "Use -h or --help for usage information\n");
            return 1;
        }
    }

    // Load API credentials
    if (load_credentials() != 0) {
        return 1;
    }

    // Initialize curl
    curl_global_init(CURL_GLOBAL_DEFAULT);

    char **symbols;
    int symbol_count;

    // Load symbols either from string or file
    if (symbol_string) {
        // Parse symbols from command line string
        symbol_count = parse_symbols_from_string(symbol_string, &symbols);
        if (symbol_count <= 0) {
            fprintf(stderr, "Error: No valid symbols in provided string\n");
            curl_global_cleanup();
            return 1;
        }
        fprintf(stderr, "Parsed %d symbols from command line\n", symbol_count);
    } else {
        // Read symbols from file
        symbol_count = read_symbols(symbol_file, &symbols);
        if (symbol_count <= 0) {
            fprintf(stderr, "Error: No symbols loaded from %s\n", symbol_file);
            curl_global_cleanup();
            return 1;
        }
        fprintf(stderr, "Loaded %d symbols from %s\n", symbol_count, symbol_file);
    }

    // Print status message
    if (all_symbols) {
        fprintf(stderr, "Processing %d symbols (ALL MODE - no filtering, outputting ALL stocks)\n",
                symbol_count);
    } else {
        fprintf(stderr, "Processing %d symbols (max price: $%.2f, min change: %.1f%%, min trades: %d, output: %d stocks)\n",
                symbol_count, max_price, min_percent_change, min_trades, max_output);
    }

    // Allocate memory for results
    StockData *results = malloc(symbol_count * sizeof(StockData));
    if (!results) {
        fprintf(stderr, "Error: Failed to allocate memory for results\n");
        for (int i = 0; i < symbol_count; i++) free(symbols[i]);
        free(symbols);
        curl_global_cleanup();
        return 1;
    }

    int result_count;

    // Get stock data from Alpaca API
    if (get_stock_snapshots(symbols, symbol_count, results, &result_count, max_price, min_percent_change, min_trades, all_symbols, raw_output) != 0) {
        fprintf(stderr, "Error: Failed to get stock snapshots\n");
        for (int i = 0; i < symbol_count; i++) free(symbols[i]);
        free(symbols);
        free(results);
        curl_global_cleanup();
        return 1;
    }

    fprintf(stderr, "Successfully processed %d stocks with sufficient trading activity\n", result_count);

    // Generate JSON output
    generate_json_output(results, result_count, max_output, all_symbols);

    // Cleanup
    for (int i = 0; i < symbol_count; i++) free(symbols[i]);
    free(symbols);
    free(results);
    curl_global_cleanup();

    return 0;
}
