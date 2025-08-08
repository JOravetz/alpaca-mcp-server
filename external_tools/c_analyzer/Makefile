CC = gcc
CFLAGS = -Wall -Wno-format-truncation -O2
LIBS = -lcurl -ljson-c -lm
BIN_DIR = ../../bin

all: stock_analyzer_json

stock_analyzer_json: stock_analyzer_json.c
	@mkdir -p $(BIN_DIR)
	$(CC) $(CFLAGS) -o $(BIN_DIR)/stock_analyzer_json stock_analyzer_json.c $(LIBS)
	@echo "✅ Built stock_analyzer_json -> $(BIN_DIR)/stock_analyzer_json"

clean:
	rm -f $(BIN_DIR)/stock_analyzer_json

.PHONY: all clean
