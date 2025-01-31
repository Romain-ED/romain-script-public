#!/usr/bin/env bash

# Set API credentials
API_KEY="35ba62f4"
API_SECRET="30b39f4b782f6fc4"

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Debug mode flag
DEBUG=false
if [[ "$1" == "-d" ]]; then
    DEBUG=true
    echo -e "${YELLOW}Debug mode enabled${NC}"
fi

# API Endpoints
UPDATE_BALANCE_URL_TEMPLATE="https://api.nexmo.com/accounts/${API_KEY}/subaccounts/"
CREDIT_TRANSFER_URL="https://api.nexmo.com/accounts/${API_KEY}/credit-transfers"

# Read the list of subkeys and amounts from input
INPUT_LIST=(
    "45ac92c6,8000"
    "4dffb1c6,2000"
    "b6473eb9,20000"
    "fcd9dde5,3000"
    "d3af0e11,2000"
    "37cadf30,2000"
    "efeedaa1,2000"
)

# Function to pretty-print JSON responses
pretty_print_json() {
    echo "$1" | jq '.' 2>/dev/null || echo "$1"
}

# Summary array (Use simple indexed array)
SUMMARY=()

# Loop through each entry and process
for entry in "${INPUT_LIST[@]}"; do
    IFS="," read -r SUBKEY AMOUNT <<< "$entry"
    UPDATE_BALANCE_URL="${UPDATE_BALANCE_URL_TEMPLATE}${SUBKEY}"
    UPDATE_BALANCE_PAYLOAD='{"use_primary_account_balance":false}'
    CREDIT_TRANSFER_PAYLOAD="{\"from\":\"${SUBKEY}\", \"to\":\"${API_KEY}\", \"amount\": ${AMOUNT}}"

    echo -e "${BLUE}Processing SUBKEY: $SUBKEY${NC}"
    echo "--------------------------------------"
    
    if [ "$DEBUG" = true ]; then
        echo -e "${YELLOW}DEBUG: Updating balance URL: ${UPDATE_BALANCE_URL}${NC}"
        echo -e "${YELLOW}DEBUG: Payload: ${UPDATE_BALANCE_PAYLOAD}${NC}"
    fi
    
    # Step 1: Disabling subkey balance sharing setting
    echo -e "${YELLOW}Updating balance setting...${NC}"
    update_response=$(curl -s -X PATCH -u "${API_KEY}:${API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "${UPDATE_BALANCE_PAYLOAD}" \
        "${UPDATE_BALANCE_URL}")
    
    echo -e "Response:" && pretty_print_json "$update_response"
    if [[ "$update_response" != *"200"* && "$update_response" != *"success"* ]]; then
        echo -e "${RED}Failed to disable balance sharing for $SUBKEY.${NC}"
        echo "--------------------------------------"
    else
        echo -e "${GREEN}Balance updated successfully for $SUBKEY.${NC}"
    fi
    
    if [ "$DEBUG" = true ]; then
        echo -e "${YELLOW}DEBUG: Credit transfer URL: ${CREDIT_TRANSFER_URL}${NC}"
        echo -e "${YELLOW}DEBUG: Payload: ${CREDIT_TRANSFER_PAYLOAD}${NC}"
    fi
    
    # Step 2: Setting credit limit (proceeds even if step 1 fails)
    echo -e "${YELLOW}Setting credit to $AMOUNT...${NC}"
    transfer_response=$(curl -s -X POST -u "${API_KEY}:${API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "${CREDIT_TRANSFER_PAYLOAD}" \
        "${CREDIT_TRANSFER_URL}")
    
    echo -e "Response:" && pretty_print_json "$transfer_response"
    if [[ "$transfer_response" != *"200"* && "$transfer_response" != *"success"* ]]; then
        echo -e "${RED}Failed to transfer credit to $SUBKEY.${NC}"
    else
        echo -e "${GREEN}Credit transfer successful for $SUBKEY.${NC}"
        # Store the key-value pair in a simple array
        SUMMARY+=("$SUBKEY:$AMOUNT")
    fi
    echo "======================================"
done

# Print Summary
echo -e "${BLUE}Summary of Credit Transfers:${NC}"
echo "--------------------------------------"
for entry in "${SUMMARY[@]}"; do
    IFS=":" read -r key amount <<< "$entry"
    echo -e "${GREEN}SUBKEY: $key - Amount Transferred: $amount${NC}"
done
echo "======================================"

