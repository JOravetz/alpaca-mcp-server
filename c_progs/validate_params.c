// Helper function to validate sort keys
int is_valid_sort_key(const char *key) {
    const char *valid_keys[] = {
        "symbol", "price", "day_close", "percent_change", 
        "gradient_full", "gradient_recent", "gradient_change",
        "volume", "volume_change", "trades", "trades_change", NULL
    };
    
    for (int i = 0; valid_keys[i]; i++) {
        if (strcmp(key, valid_keys[i]) == 0) return 1;
    }
    return 0;
}

// Validate all sort keys in comma-separated string
int validate_sort_keys(const char *keys_str) {
    if (!keys_str || strlen(keys_str) == 0) return 0;
    
    char *str_copy = strdup(keys_str);
    if (!str_copy) return 0;
    
    int valid = 1;
    char *token = strtok(str_copy, ",");
    
    while (token && valid) {
        // Trim whitespace
        while (*token && isspace(*token)) token++;
        char *end = token + strlen(token) - 1;
        while (end > token && isspace(*end)) *end-- = '\0';
        
        if (!is_valid_sort_key(token)) {
            fprintf(stderr, "Error: Invalid sort key '%s'\n", token);
            fprintf(stderr, "Valid keys: symbol, price, day_close, percent_change, gradient_full,\n");
            fprintf(stderr, "            gradient_recent, gradient_change, volume, volume_change, trades, trades_change\n");
            valid = 0;
        }
        token = strtok(NULL, ",");
    }
    
    free(str_copy);
    return valid;
}

// Validate file exists and is readable
int validate_file(const char *filename) {
    if (access(filename, R_OK) != 0) {
        fprintf(stderr, "Error: Cannot read file '%s': %s\n", filename, strerror(errno));
        return 0;
    }
    return 1;
}