#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_file>"
    exit 1
fi

# Define input and output file paths and filter keyword from script parameters
input_file="$1"
output_file="$2"

# Check if input file exists
if [ ! -f "$input_file" ]; then
    echo "Input file not found: $input_file"
    exit 1
fi

# Remove first line of file
sed -i '1d' $1 > $2


# Use csvcut to extract the desired columns
# Columns: A, B, F, G, H, I, J, K, M, P, Q, R, T, AA (1, 2, 6, 7, 8, 9, 10, 11, 13, 16, 17, 18, 20, 27)
csvcut -c 2,4,7,13,16,17  "$input_file" > "$output_file"




# Get the number of total lines in the input and output files
total_lines_input=$(wc -l < "$input_file")
total_lines_output=$(wc -l < "$output_file")

# Print the summary
echo "----------------------------------------"
echo "Summary of the file processing:"
echo "----------------------------------------"
echo "Total lines in original file : $total_lines_input"
echo "Total lines in filtered file : $total_lines_output"
echo "----------------------------------------"
echo "Filtered CSV file has been created: $output_file"


# Columns and index in raw report file from report_api
: '
account_id  	1
message_id  	2
account_ref 	3
client_ref  	4
direction	    5
from	        6
to          	7
forced_from	  8
network	      9
network_name	10
country	      11
country_name	12
date_received	13
date_finalized	14
latency	      15
status	      16
error_code	  17
error_code_description	18
currency	    19
total_price	  20
id	          21
dcs	          22
validity_period	23
ip_address	  24
changed_from	25
udh	          26
gateway	      27
gateway_id	  28
gateway_error_code	29
routing_rule_seq	30
channel	      31
srr	          32
hlr_lookup_cost	33
date_submitted	34
route_cost	  35
protocol_id	  36
'
