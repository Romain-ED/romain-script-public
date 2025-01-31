#!/usr/bin/env bash

# Set API credentials
API_KEY="35ba62f4"
API_SECRET="30b39f4b782f6fc4"

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# API Endpoint template
SUBACCOUNT_INFO_URL_TEMPLATE="https://api.nexmo.com/accounts/${API_KEY}/subaccounts/"

# Log file setup (same folder as script execution)
LOG_FILE="$(pwd)/api_responses.log"
echo -e "${YELLOW}Logging API responses to: $LOG_FILE${NC}"
echo "==========================================" >> "$LOG_FILE"
echo "$(date +"%Y-%m-%d %H:%M:%S") - Script started" >> "$LOG_FILE"

# Ensure a filename is provided
if [[ $# -ne 1 ]]; then
    echo -e "${RED}Usage: $0 <subaccounts_file>${NC}"
    exit 1
fi

SUBACCOUNTS_FILE="$1"

# Validate that the file exists and is not empty
if [[ ! -f "$SUBACCOUNTS_FILE" || ! -s "$SUBACCOUNTS_FILE" ]]; then
    echo -e "${RED}Error: File '$SUBACCOUNTS_FILE' does not exist or is empty.${NC}"
    exit 1
fi

# Read subaccounts from file into an array (compatible with older Bash versions)
SUBACCOUNTS=()
while IFS= read -r line || [[ -n "$line" ]]; do
    clean_line=$(echo "$line" | tr -d '\r' | grep -oE '^[a-zA-Z0-9]+')
    if [[ -n "$clean_line" ]]; then
        SUBACCOUNTS+=("$clean_line")
    fi
done < "$SUBACCOUNTS_FILE"

# Retrieve credit limits for each subaccount
echo -e "${BLUE}Retrieving Credit Limits for Subaccounts...${NC}"
echo "---------------------------------------------------"
for SUBKEY in "${SUBACCOUNTS[@]}"; do
    RESPONSE=$(curl -s -X GET -u "${API_KEY}:${API_SECRET}" \
        -H "Content-Type: application/json" \
        "${SUBACCOUNT_INFO_URL_TEMPLATE}${SUBKEY}")

    # Extract relevant fields from the response
    API_KEY_RESPONSE=$(echo "$RESPONSE" | jq -r '.api_key' 2>/dev/null)
    CREDIT_LIMIT=$(echo "$RESPONSE" | jq -r '.credit_limit' 2>/dev/null)
    BALANCE=$(echo "$RESPONSE" | jq -r '.balance' 2>/dev/null)

    # Log full API response for debugging
    echo "$(date +"%Y-%m-%d %H:%M:%S") - Subaccount: $SUBKEY" >> "$LOG_FILE"
    echo "$RESPONSE" >> "$LOG_FILE"
    echo "---------------------------------------------------" >> "$LOG_FILE"

    # Print results to console
    if [[ "$CREDIT_LIMIT" == "null" || -z "$CREDIT_LIMIT" ]]; then
        echo -e "${RED}Failed to retrieve credit limit for $SUBKEY.${NC}"
    else
        echo -e "${GREEN}$API_KEY_RESPONSE  ${BLUE}CL: $CREDIT_LIMIT  ${YELLOW}BL: $BALANCE${NC}"
    fi
done

echo "$(date +"%Y-%m-%d %H:%M:%S") - Script finished" >> "$LOG_FILE"

