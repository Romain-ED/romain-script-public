#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <input_file> <output_file> <filter_keyword>"
    exit 1
fi

# Define input and output file paths and filter keyword from script parameters
input_file="$1"
output_file="$2"
filter_keyword="$3"

# Check if input file exists
if [ ! -f "$input_file" ]; then
    echo "Input file not found: $input_file"
    exit 1
fi

# Count the total number of lines in the input file
total_lines_input=$(wc -l < "$input_file")

# Extract the required columns by indices
awk -F',' -v filter="$filter_keyword" -v total_lines="$total_lines_input" '
BEGIN {
    FPAT = '([^,]*)|("[^"]+")';
    OFS = ",";
}
NR == 1 {
    # Print the header line with required columns (B, F, G, H, I, J, K, M, P, Q, R, T, AA)
    print $2, $6, $7, $8, $9, $10, $11, $13, $16, $17, $18, $20, $27;
}
NR > 1 {
    if ($6 ~ filter) {
        print $2, $6, $7, $8, $9, $10, $11, $13, $16, $17, $18, $20, $27;
    }
}
END {
    print "Processing complete." > "/dev/stderr";
}' "$input_file" > "$output_file"

# Get the number of total lines in the output file
total_lines_output=$(wc -l < "$output_file")

# Get the number of columns in the input and output files
columns_input=$(head -n 1 "$input_file" | awk -F',' '{print NF}')
columns_output=$(head -n 1 "$output_file" | awk -F',' '{print NF}')
columns_removed=$((columns_input - columns_output))

# Get the size of the input and output files in MB
size_input=$(stat -f%z "$input_file")
size_output=$(stat -f%z "$output_file")
size_input_mb=$(echo "scale=2; $size_input / (1024 * 1024)" | bc)
size_output_mb=$(echo "scale=2; $size_output / (1024 * 1024)" | bc)

# Print the summary with improved formatting
echo "----------------------------------------"
echo "Summary of the file processing:"
echo "----------------------------------------"
echo "Total lines in original file : $total_lines_input"
echo "Total lines in filtered file : $total_lines_output"
echo "----------------------------------------"
echo "Original number of columns   : $columns_input"
echo "Number of columns removed    : $columns_removed"
echo "----------------------------------------"
echo "Size of original file        : $size_input_mb MB"
echo "Size of filtered file        : $size_output_mb MB"
echo "----------------------------------------"
echo "Filtered CSV file has been created: $output_file"
