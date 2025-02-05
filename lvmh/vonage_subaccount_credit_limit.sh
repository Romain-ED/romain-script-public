#!/usr/bin/env bash

# =============================================================================
# Vonage Subaccount Management Script
# Version: 2.0.3
# Author: Romain EDIN (Vonage)
# =============================================================================
#
# DESCRIPTION:
#   This script manages Vonage (formerly Nexmo) subaccounts, allowing you to:
#   - Retrieve information about subaccounts (balance, credit limit, settings)
#   - Set credit limits for multiple subaccounts
#   - Modify subaccount settings
#
# PREREQUISITES:
#   - Bash shell
#   - curl
#   - jq (for JSON processing)
#   - Valid Vonage API credentials (API key and secret)
#
# ENVIRONMENT VARIABLES REQUIRED:
#   - NEXMO_API_KEY: Your Vonage API key
#   - NEXMO_API_SECRET: Your Vonage API secret
#
# USAGE:
# ./script.sh [--debug] [--retrieve | --set-credit] <subaccounts_file>
#
# OPTIONS:
#   --debug         Enable debug mode with detailed execution information
#   --retrieve      Get information about listed subaccounts
#   --set-credit   Set credit limits for listed subaccounts
#
# INPUT FILE FORMAT:
#   For --retrieve:
#     <subaccount_key>
#     <subaccount_key>
#   ...
#
#   For --set-credit:
#     <subaccount_key> <amount>  # Space or tab separated
#     <subaccount_key> <amount>
#   ...
#
# OUTPUT FILES:
#   - api_responses.log: Detailed API response logs
#   - api_calls.log: Record of all API calls made
#   - summary_report.log: Summary of operations performed
#
# VERSION HISTORY:
#   1.0.0 - Initial version with basic subaccount management
#   1.1.0 - Added logging functionality
#   2.0.0 - Added debug mode and improved error handling
#   2.0.1 - Fixed file reading to handle both space and tab separators
#   2.0.2 - Added before/after balance verification for credit updates
#   2.0.3 - Improved credit limit setting to adjust based on current limit
#
# =============================================================================

# Ensure API credentials are set as environment variables
if [[ -z "$NEXMO_API_KEY" || -z "$NEXMO_API_SECRET" ]]; then
    echo -e "\n\033[0;31mError: NEXMO_API_KEY and NEXMO_API_SECRET must be set as environment variables.\033[0m\n"
    exit 1
fi

# Define color codes
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

# Debug mode flag
DEBUG=false

# Debug function
debug() {
    if [[ "$DEBUG" == true ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*" >&2
    fi
}

# Function to dump variable content
dump_var() {
    local var_name="$1"
    local var_value="${!var_name}"
    debug "Variable ${YELLOW}${var_name}${NC} = ${GREEN}${var_value}${NC}"
}

# API Endpoints
SUBACCOUNT_INFO_URL_TEMPLATE="https://api.nexmo.com/accounts/${NEXMO_API_KEY}/subaccounts/"
MODIFY_SUBACCOUNT_URL_TEMPLATE="https://api.nexmo.com/accounts/${NEXMO_API_KEY}/subaccounts/"
CREDIT_TRANSFER_URL="https://api.nexmo.com/accounts/${NEXMO_API_KEY}/credit-transfers"

# Log files setup (overwrite content each time script runs)
LOG_FILE="$(pwd)/api_responses.log"
API_CALLS_LOG="$(pwd)/api_calls.log"
SUMMARY_REPORT="$(pwd)/summary_report.log"

echo -e "\n${YELLOW}Logging API responses to: $LOG_FILE${NC}\n"
echo "==========================================" > "$LOG_FILE"
echo -e "$(date +"%Y-%m-%d %H:%M:%S") - Script started\n" >> "$LOG_FILE"

echo "==========================================" > "$API_CALLS_LOG"
echo -e "$(date +"%Y-%m-%d %H:%M:%S") - API Calls Log\n" >> "$API_CALLS_LOG"

echo "==========================================" > "$SUMMARY_REPORT"
echo -e "$(date +"%Y-%m-%d %H:%M:%S") - Summary Report\n" >> "$SUMMARY_REPORT"

# Ensure correct usage
if [[ $# -lt 2 ]]; then
    echo -e "\n${RED}Usage: $0 [--debug] [--retrieve | --set-credit] <subaccounts_file>${NC}\n"
    exit 1
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)
            DEBUG=true
            debug "Debug mode enabled"
            shift
          ;;
        --retrieve|--set-credit)
            OPTION="$1"
            debug "Operation mode: $OPTION"
            shift
          ;;
        *)
            SUBACCOUNTS_FILE="$1"
            debug "Subaccounts file: $SUBACCOUNTS_FILE"
            shift
          ;;
    esac
done

# Validate input file

if [[ ! -f "$SUBACCOUNTS_FILE" ]]; then
    echo -e "\n${RED}Error: File '$SUBACCOUNTS_FILE' does not exist.${NC}\n"
    exit 1
fi

if [[ ! -s "$SUBACCOUNTS_FILE" ]]; then
    echo -e "\n${RED}Error: File '$SUBACCOUNTS_FILE' is empty.${NC}\n"
    exit 1
fi


# Read subaccounts from file
SUBACCOUNTS=()
AMOUNTS=()
debug "Reading subaccounts from file: $SUBACCOUNTS_FILE"

while read -r line || [[ -n "$line" ]]; do
    debug "Processing line: '$line'"
    
    # First try to split by tab, then by space if no tab is found
    if [[ "$line" == *$'\t'* ]]; then
        # Split by tab
        SUBKEY=$(echo "$line" | cut -f1)
        AMOUNT=$(echo "$line" | cut -f2)
    else
        # Split by space
        SUBKEY=$(echo "$line" | awk '{print $1}')
        AMOUNT=$(echo "$line" | awk '{print $2}')
    fi

    clean_key=$(echo "$SUBKEY" | tr -d '\r' | grep -oE '^[a-zA-Z0-9]+')
    clean_amount=$(echo "$AMOUNT" | tr -d '\r' | grep -oE '^[0-9]+')

    debug "Split values - SUBKEY: '$SUBKEY', AMOUNT: '$AMOUNT'"
    debug "Cleaned values - SUBKEY: '$clean_key', AMOUNT: '$clean_amount'"

    if [[ -n "$clean_key" ]]; then
        SUBACCOUNTS+=("$clean_key")
        if [[ "$OPTION" == "--set-credit" && -n "$clean_amount" ]]; then
            AMOUNTS+=("$clean_amount")
            debug "Added subaccount: ${clean_key} with amount: ${clean_amount}"
        else
            AMOUNTS+=("0")
            debug "Added subaccount: ${clean_key} with default amount: 0"
        fi
    fi
done < "$SUBACCOUNTS_FILE"

debug "Loaded ${#SUBACCOUNTS[@]} subaccounts"
if [[ "$DEBUG" == true ]]; then
    for i in "${!SUBACCOUNTS[@]}"; do
        debug "Subaccount[$i]: ${SUBACCOUNTS[$i]}, Amount: ${AMOUNTS[$i]}"
    done
fi

# Function to retrieve subaccount information

retrieve_subaccount_info() {
    local SUBKEY="$1"
    debug "Retrieving info for subaccount: $SUBKEY"
    local URL="${SUBACCOUNT_INFO_URL_TEMPLATE}${SUBKEY}"
    debug "API URL: $URL"

    debug "Making API call to retrieve subaccount info..."
    RESPONSE=$(curl -s -X GET -u "${NEXMO_API_KEY}:${NEXMO_API_SECRET}" \
        -H "Content-Type: application/json" \
        "$URL")
    debug "Raw API Response: $RESPONSE"

    # Check for unauthorized IP error
    if echo "$RESPONSE" | jq -e '.title == "Unauthorized"' > /dev/null 2>&1; then
        echo -e "\n${RED}Error: Your IP address is not whitelisted. Please contact your Nexmo/Vonage administrator to allow your IP.${NC}\n"
        return
    fi

    API_KEY_RESPONSE=$(echo "$RESPONSE" | jq -r '.api_key' 2>/dev/null)
    CREDIT_LIMIT=$(echo "$RESPONSE" | jq -r '.credit_limit' 2>/dev/null)
    BALANCE=$(echo "$RESPONSE" | jq -r '.balance' 2>/dev/null)
    USE_PRIMARY_BALANCE=$(echo "$RESPONSE" | jq -r '.use_primary_account_balance' 2>/dev/null)

    # If CREDIT_LIMIT is null, set it to 0
    if [[ "$CREDIT_LIMIT" == "null" ]]; then
        CREDIT_LIMIT=0
    fi

    debug "Parsed Response:"
    debug "  API Key: $API_KEY_RESPONSE"
    debug "  Credit Limit: $CREDIT_LIMIT"
    debug "  Balance: $BALANCE"
    debug "  Use Primary Balance: $USE_PRIMARY_BALANCE"

    echo -e "${CYAN}$API_KEY_RESPONSE  ${YELLOW}CL: ${CREDIT_LIMIT:-null}  ${GREEN}BL: ${BALANCE:-null}  ${RED}Use Primary: ${USE_PRIMARY_BALANCE:-null}${NC}"
}

# Function to modify subaccount settings
modify_subaccount() {
    local SUBKEY="$1"
    debug "Modifying subaccount: $SUBKEY"
    local URL="${MODIFY_SUBACCOUNT_URL_TEMPLATE}${SUBKEY}"
    local PAYLOAD='{"use_primary_account_balance": false}'
    
    debug "API URL: $URL"
    debug "Request Payload: $PAYLOAD"

    debug "Making API call to modify subaccount..."
    local RESPONSE=$(curl -s -X PATCH -u "${NEXMO_API_KEY}:${NEXMO_API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$URL")
    debug "API Response: $RESPONSE"
}

# Function to set credit limit

# Function to set credit limit
set_credit_limit() {
    local SUBKEY="$1"
    local AMOUNT="$2"
    debug "Setting credit limit for subaccount: $SUBKEY, Amount: $AMOUNT"

    if [[ "$AMOUNT" -eq 0 ]]; then
        debug "Skipping credit limit update (amount is 0)"
        return
    fi

    # Retrieve current credit limit
    debug "Retrieving current credit limit for $SUBKEY"
    retrieve_subaccount_info "$SUBKEY"
    CURRENT_CREDIT_LIMIT=$(echo "$RESPONSE" | jq -r '.credit_limit')

    # Remove everything from the decimal point onwards
    CURRENT_CREDIT_LIMIT=$(echo "$CURRENT_CREDIT_LIMIT" | cut -d '.' -f 1)

    # Take the absolute value of CURRENT_CREDIT_LIMIT
    CURRENT_CREDIT_LIMIT=$((CURRENT_CREDIT_LIMIT > 0? CURRENT_CREDIT_LIMIT: CURRENT_CREDIT_LIMIT * -1))
    debug "Current credit limit (without decimals and absolute): ${RED}$CURRENT_CREDIT_LIMIT${NC}"

    # Determine transfer direction
    local FROM_ACCOUNT=""
    local TO_ACCOUNT=""
    if [[ "$CURRENT_CREDIT_LIMIT" -ge "$AMOUNT" ]]; then
        FROM_ACCOUNT="${SUBKEY}"
        TO_ACCOUNT="${NEXMO_API_KEY}"
    else
        FROM_ACCOUNT="${NEXMO_API_KEY}"
        TO_ACCOUNT="${SUBKEY}"
    fi

    # Calculate the difference (always positive)
    local DIFFERENCE=$((AMOUNT - CURRENT_CREDIT_LIMIT))
    DIFFERENCE=$((DIFFERENCE > 0? DIFFERENCE: DIFFERENCE * -1))
    debug "Amount: ${RED}$AMOUNT${NC}, Difference to apply: ${RED}$DIFFERENCE${NC}"

    # Skip API call if DIFFERENCE is 0
    if [[ "$DIFFERENCE" -eq 0 ]]; then
        debug "Skipping credit transfer as the difference is 0"
        return
    fi

    local PAYLOAD="{\"from\":\"${FROM_ACCOUNT}\", \"to\":\"${TO_ACCOUNT}\", \"amount\": ${DIFFERENCE}}"
    debug "API URL: $CREDIT_TRANSFER_URL"
    debug "Request Payload: $PAYLOAD"

    debug "Making API call to set credit limit..."
    local RESPONSE=$(curl -s -X POST -u "${NEXMO_API_KEY}:${NEXMO_API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$CREDIT_TRANSFER_URL")
    debug "API Response: $RESPONSE"
}

# Process options
debug "Processing operation mode: $OPTION"
case "$OPTION" in
    --set-credit)
        debug "Starting credit setting process for ${#SUBACCOUNTS[@]} subaccounts"
        for i in "${!SUBACCOUNTS[@]}"; do
            debug "Processing subaccount ${i+1}/${#SUBACCOUNTS[@]}"
            
            # Display initial state
            echo -e "\n${YELLOW}Before credit update for subaccount ${SUBACCOUNTS[i]}:${NC}"
            retrieve_subaccount_info "${SUBACCOUNTS[i]}" # This sets USE_PRIMARY_BALANCE
            
            # Modify subaccount only if USE_PRIMARY_BALANCE is true
            if [[ "$USE_PRIMARY_BALANCE" == "true" ]]; then
                modify_subaccount "${SUBACCOUNTS[i]}"
            fi
            
            set_credit_limit "${SUBACCOUNTS[i]}" "${AMOUNTS[i]}"
            
            # Wait a moment for the credit update to propagate
            sleep 2
            
            # Display final state
            echo -e "\n${YELLOW}After credit update for subaccount ${SUBACCOUNTS[i]}:${NC}"
            retrieve_subaccount_info "${SUBACCOUNTS[i]}"
            echo -e "${GREEN}----------------------------------------${NC}\n"
        done
      ;;
      
      --retrieve)
        debug "Starting retrieval process for ${#SUBACCOUNTS[@]} subaccounts"
        for SUBKEY in "${SUBACCOUNTS[@]}"; do
            retrieve_subaccount_info "$SUBKEY"
        done
      ;;
    *)
        echo -e "\n${RED}Invalid option. Use --retrieve or --set-credit.${NC}\n"
        exit 1
      ;;
esac

debug "Script execution completed"
