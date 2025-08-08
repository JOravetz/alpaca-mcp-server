#!/bin/bash

# ===============================================
# run_avo_compare.sh
# Script to compare two execution runs and determine ranking changes.
# ===============================================

# ================================
# Example Use Cases
# ================================

# Default run (using combined.lis)
# ./run_avo_compare.sh

# Run with custom symbols file
# ./run_avo_compare.sh -symbols_file custom.lis

# Compare with different timeframes and custom symbols file
# ./run_avo_compare.sh -compare -ndays 5 -ndays_short 3 -symbols_file my_symbols.lis

# ================================
# Default Values
# ================================
NUM_SYMBOLS=20
COMPARE=0
NDAYS=3
NDAYS_SHORT=2
SYMBOLS_FILE="./data/combined.lis"

# ================================
# Function to Display Usage
# ================================
usage() {
    echo "Usage: $0 [-compare] [-num_symbols N] [-ndays N] [-ndays_short N] [-symbols_file FILE]"
    echo "Defaults: num_symbols=20, ndays=3, ndays_short=2, symbols_file=combined.lis"
    exit 1
}

# ================================
# Clear DB tables at startup
# ================================
echo "Clearing DB tables..."
if ! uv run ./external_tools/fft_analysis/clear_db_data.py; then
    echo "Warning: Failed to clear DB tables. Continuing anyway..."
fi

# ================================
# Parse Command Line Arguments
# ================================
while [[ $# -gt 0 ]]; do
    case $1 in
        -compare)
            COMPARE=1
            shift
            ;;
        -num_symbols)
            if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                NUM_SYMBOLS="$2"
                shift 2
            else
                echo "Error: -num_symbols requires a positive integer argument."
                usage
            fi
            ;;
        -ndays)
            if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                NDAYS="$2"
                shift 2
            else
                echo "Error: -ndays requires a positive integer argument."
                usage
            fi
            ;;
        -ndays_short)
            if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                NDAYS_SHORT="$2"
                shift 2
            else
                echo "Error: -ndays_short requires a positive integer argument."
                usage
            fi
            ;;
        -symbols_file)
            if [[ -n "$2" ]]; then
                SYMBOLS_FILE="$2"
                shift 2
            else
                echo "Error: -symbols_file requires a filename argument."
                usage
            fi
            ;;
        *)
            echo "Unknown parameter: $1"
            usage
            ;;
    esac
done

# Validate that symbols file exists
if [ ! -f "${SYMBOLS_FILE}" ]; then
    echo "Error: Symbols file '${SYMBOLS_FILE}' not found."
    exit 1
fi

# Validate that ndays_short is less than ndays
if [ "${NDAYS_SHORT}" -ge "${NDAYS}" ]; then
    echo "Error: -ndays_short (${NDAYS_SHORT}) should be less than -ndays (${NDAYS})."
    exit 1
fi

# ================================
# Generate Timestamps and File Names
# ================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="output.avo.${TIMESTAMP}.dat"
PREVIOUS_FILE=$(ls -t output.avo.*.dat 2>/dev/null | grep -v "output.avo.${TIMESTAMP}.dat" | head -n1)

# ================================
# Execute Python Script and Sort Output
# ================================
SORTED_PYTHON_OUTPUT="combined.sorted.${TIMESTAMP}.lis"

echo "Running Python script with symbols file: ${SYMBOLS_FILE}"
grep -v -wf bad.lis ./data/combined.lis > bub ; mv bub ./data/combined.lis
if ! python ./external_tools/fft_analysis/daily_bars.sqlite.latest_bars_class.py -l "${SYMBOLS_FILE}" -n "${NDAYS}" | sort -k14n > "${SORTED_PYTHON_OUTPUT}"; then
    echo "Error: Python script failed."
    exit 1
fi
echo "Sorted output saved to ${SORTED_PYTHON_OUTPUT}."

# Backup original symbols file
cp "${SYMBOLS_FILE}" "${SYMBOLS_FILE}.bak.${TIMESTAMP}"
echo "Backup of ${SYMBOLS_FILE} created."

# ================================
# Run lsq_fft.gsl with Symbols File
# ================================
echo "Running lsq_fft.gsl..."
if ! /home/jjoravet/cwp/bin/lsq_fft.gsl file="${SYMBOLS_FILE}" ndays="${NDAYS}" ndays_short="${NDAYS_SHORT}" sort_col=4 descending=1 > "${OUTPUT_FILE}"; then
    echo "Error: lsq_fft.gsl failed."
    exit 1
fi
echo "Output saved to ${OUTPUT_FILE}."

# ================================
# Compare with Previous Run if Requested
# ================================
if [ "${COMPARE}" -eq 1 ]; then
    if [ -z "${PREVIOUS_FILE}" ]; then
        echo "Warning: No previous output file found. Skipping comparison."
    else
        echo -e "\nRanking changes (${PREVIOUS_FILE} -> ${OUTPUT_FILE}):"

        # Extract relevant fields
        grep -E '^\s*[0-9]+' "${PREVIOUS_FILE}" | awk '{print $2, $1, $5}' | sort -k1 > previous_extracted.tmp
        grep -E '^\s*[0-9]+' "${OUTPUT_FILE}" | awk '{print $2, $1, $5}' | sort -k1 > current_extracted.tmp

        # Join on Symbol
        join -j1 1 previous_extracted.tmp current_extracted.tmp > joined_rankings.tmp

        # Check if join was successful
        if [ $? -ne 0 ]; then
            echo "Error: Failed to join files. Ensure that the 'Symbol' field is present in both files."
            rm -f previous_extracted.tmp current_extracted.tmp joined_rankings.tmp
            exit 1
        fi

        # Calculate changes
        awk '{
            symbol = $1;
            prev_rank = $2;
            curr_rank = $4;
            if (prev_rank ~ /^[0-9]+$/ && curr_rank ~ /^[0-9]+$/) {
                change = prev_rank - curr_rank;
                if (change > 0) {
                    change_str = sprintf("+%d", change);
                } else if (change < 0) {
                    change_str = sprintf("%d", change);
                } else {
                    change_str = "0";
                }
            } else {
                change_str = "0";
            }
            slope_short = $5;
            printf "%s|%s|%s|%s|%s\n", symbol, prev_rank, curr_rank, change_str, slope_short;
        }' joined_rankings.tmp > rank_changes.tmp

        # Clean up
        rm -f previous_extracted.tmp current_extracted.tmp joined_rankings.tmp

        # Display Improvers
        echo -e "\nTop ${NUM_SYMBOLS} Improvers:"
        printf -- "%-10s | %9s | %9s | %7s | %13s\n" "Symbol" "PrevRank" "CurrRank" "Change" "Slope_Short"
        printf -- "-----------+----------+----------+---------+--------------\n"
        awk -F'|' '$4 ~ /^\+/ {printf "%-10s | %9s | %9s | %7s | %13s\n", $1, $2, $3, $4, $5}' rank_changes.tmp | sort -k4 -r | head -n "${NUM_SYMBOLS}"

        # Display Decliners
        echo -e "\nTop ${NUM_SYMBOLS} Decliners:"
        printf -- "%-10s | %9s | %9s | %7s | %13s\n" "Symbol" "PrevRank" "CurrRank" "Change" "Slope_Short"
        printf -- "-----------+----------+----------+---------+--------------\n"
        awk -F'|' '$4 ~ /^-/ {printf "%-10s | %9s | %9s | %7s | %13s\n", $1, $2, $3, $4, $5}' rank_changes.tmp | sort -k4 | head -n "${NUM_SYMBOLS}"

        # Display Top Slope_Short
        echo -e "\nTop ${NUM_SYMBOLS} by Slope_Short:"
        printf -- "%-10s | %9s | %9s | %7s | %13s\n" "Symbol" "PrevRank" "CurrRank" "Change" "Slope_Short"
        printf -- "-----------+----------+----------+---------+--------------\n"
        sort -t'|' -k5 -nr rank_changes.tmp | awk -F'|' '{printf "%-10s | %9s | %9s | %7s | %13s\n", $1, $2, $3, $4, $5}' | head -n "${NUM_SYMBOLS}"

        # Save full comparison
        mv rank_changes.tmp "rank_changes.${TIMESTAMP}.txt"
        echo -e "\nFull comparison saved to: rank_changes.${TIMESTAMP}.txt"
    fi
fi

# ================================
# Create a Symlink to the Latest Output File
# ================================
ln -sf "${OUTPUT_FILE}" output.avo.latest.dat
echo "Symlink 'output.avo.latest.dat' created."

# ================================
# Print Top N from Current Run as QC Check
# ================================
echo -e "\nQC Check - Current Top ${NUM_SYMBOLS} Rankings:"
echo "------------------------------"
head -n 2 "${OUTPUT_FILE}"
sed -n "3,$((NUM_SYMBOLS + 2))p" "${OUTPUT_FILE}"
