# Compiler and compilation flags
CC = gcc
CFLAGS = -O3 -Wall -Wextra -g

# Linker flags for external libraries.
# -lcurl for the cURL library (networking)
# -ljson-c for the json-c library (JSON processing)
# -lm for the math library (needed for filter_bars.c)
LDFLAGS = -lcurl -ljson-c -lm

# --- Program 1: stock_analyzer_json ---
TARGET1 = stock_analyzer_json
SRC1 = stock_analyzer_json.c

# --- Program 2: filter_bars ---
TARGET2 = filter_bars
SRC2 = filter_bars.c

# --- Program 3: filter_bars_input ---
TARGET3 = filter_bars_input
SRC3 = filter_bars_input.c

# --- Program 4: test_stock_analyzer ---
TARGET4 = test_stock_analyzer
SRC4 = test_stock_analyzer.c


# The 'all' rule is the default goal.
# Running 'make' will build all target executables.
all: $(TARGET1) $(TARGET2) $(TARGET3)

# Rule to build the first program
$(TARGET1): $(SRC1)
	@echo "Compiling $< -> $@"
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Rule to build the second program
$(TARGET2): $(SRC2)
	@echo "Compiling $< -> $@"
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Rule to build the third program
$(TARGET3): $(SRC3)
	@echo "Compiling $< -> $@"
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Rule to build the test program
# Links with necessary functions from stock_analyzer_json.c and includes debug symbols
$(TARGET4): $(SRC4) stock_analyzer_json.c
	@echo "Compiling test executable $< -> $@"
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Test targets
test_stock_analyzer: $(TARGET4)
	@echo "Test executable $(TARGET4) compiled successfully"

test: $(TARGET4)
	@echo "Running all tests..."
	@if [ -x "./$(TARGET4)" ]; then \
		echo "Executing ./$(TARGET4)"; \
		./$(TARGET4); \
	else \
		echo "Error: $(TARGET4) not found or not executable"; \
		exit 1; \
	fi

# Rule to clean up all compiled files
clean:
	@echo "Cleaning up compiled executables and test artifacts..."
	rm -f $(TARGET1) $(TARGET2) $(TARGET3) $(TARGET4) *.o

# Phony targets are not files; 'all' and 'clean' are commands.
.PHONY: all clean test_stock_analyzer test
