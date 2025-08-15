        } else if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {
            char *endptr;
            long val = strtol(argv[++i], &endptr, 10);
            if (*endptr \!= '\0' || val <= 0 || val > 10000) {
                fprintf(stderr, "Error: -n requires a positive integer (1-10000), got '%s'\n", argv[i]);
                return 1;
            }
            max_output = (int)val;
        } else if (strcmp(argv[i], "-a") == 0) {
            all_symbols = 1;
        } else if (strcmp(argv[i], "-r") == 0) {
            raw_output = 1;
        } else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
            symbol_string = argv[++i];
        } else if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
            char *endptr;
            double val = strtod(argv[++i], &endptr);
            if (*endptr \!= '\0' || val <= 0 || val > 1000000) {
                fprintf(stderr, "Error: -p requires a positive price (0.01-1000000), got '%s'\n", argv[i]);
                return 1;
            }
            max_price = val;
        } else if (strcmp(argv[i], "-c") == 0 && i + 1 < argc) {
            char *endptr;
            double val = strtod(argv[++i], &endptr);
            if (*endptr \!= '\0' || val < -100 || val > 10000) {
                fprintf(stderr, "Error: -c requires a percent change (-100 to 10000), got '%s'\n", argv[i]);
                return 1;
            }
            min_percent_change = val;
        } else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) {
            char *endptr;
            long val = strtol(argv[++i], &endptr, 10);
            if (*endptr \!= '\0' || val < 0 || val > 1000000000) {
                fprintf(stderr, "Error: -t requires a non-negative integer (0-1000000000), got '%s'\n", argv[i]);
                return 1;
            }
            min_trades = (int)val;
        } else if (strcmp(argv[i], "-f") == 0 && i + 1 < argc) {
            symbol_file = argv[++i];
            // File validation will be done when we try to open it
        } else if (strcmp(argv[i], "-k") == 0 && i + 1 < argc) {
            sort_keys = argv[++i];
            // Sort key validation can be done here or later
        } else {
