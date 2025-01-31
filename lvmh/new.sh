#!/usr/bin/env bash

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
if [[ $# -ne 2 ]]; then
    echo -e "\n${RED}Usage: $0 [--retrieve | --set-credit] <subaccounts_file>${NC}\n"
    exit 1
fi

OPTION="$1"
SUBACCOUNTS_FILE="$2"

# Validate input file
if [[ ! -f "$SUBACCOUNTS_FILE" || ! -s "$SUBACCOUNTS_FILE" ]]; then
    echo -e "\n${RED}Error: File '$SUBACCOUNTS_FILE' does not exist or is empty.${NC}\n"
    exit 1
fi

# Read subaccounts from file
SUBACCOUNTS=()
AMOUNTS=()
while IFS=" " read -r SUBKEY AMOUNT || [[ -n "$SUBKEY" ]]; do
    clean_key=$(echo "$SUBKEY" | tr -d '\r' | grep -oE '^[a-zA-Z0-9]+')
    clean_amount=$(echo "$AMOUNT" | tr -d '\r' | grep -oE '^[0-9]+')

    if [[ -n "$clean_key" ]]; then
        SUBACCOUNTS+=("$clean_key")
        if [[ "$OPTION" == "--set-credit" && -n "$clean_amount" ]]; then
            AMOUNTS+=("$clean_amount")
        else
            AMOUNTS+=("0") # Default value if amount is missing
        fi
    fi
done < "$SUBACCOUNTS_FILE"

# Function to retrieve subaccount information
retrieve_subaccount_info() {
    local SUBKEY="$1"
    local URL="${SUBACCOUNT_INFO_URL_TEMPLATE}${SUBKEY}"

    RESPONSE=$(curl -s -X GET -u "${NEXMO_API_KEY}:${NEXMO_API_SECRET}" \
        -H "Content-Type: application/json" \
        "$URL")

    API_KEY_RESPONSE=$(echo "$RESPONSE" | jq -r '.api_key' 2>/dev/null)
    CREDIT_LIMIT=$(echo "$RESPONSE" | jq -r '.credit_limit' 2>/dev/null)
    BALANCE=$(echo "$RESPONSE" | jq -r '.balance' 2>/dev/null)
    USE_PRIMARY_BALANCE=$(echo "$RESPONSE" | jq -r '.use_primary_account_balance' 2>/dev/null)

    echo -e "${CYAN}$API_KEY_RESPONSE  ${YELLOW}CL: ${CREDIT_LIMIT:-null}  ${GREEN}BL: ${BALANCE:-null}  ${RED}Use Primary: $USE_PRIMARY_BALANCE${NC}"
}

# Confirmation step before proceeding with modifications
confirm_changes() {
    echo -e "\n${BLUE}Retrieving Current Credit Limits...${NC}"
    echo "---------------------------------------------------"

    for SUBKEY in "${SUBACCOUNTS[@]}"; do
        retrieve_subaccount_info "$SUBKEY"
    done

    echo -e "\n${YELLOW}Do you want to proceed with the changes? Type 'yes' to continue:${NC}\n"
    read -r CONFIRMATION
    if [[ "$CONFIRMATION" != "yes" ]]; then
        echo -e "\n${RED}Operation canceled.${NC}\n"
        exit 1
    fi
}

# Function to modify `use_primary_account_balance` to false
modify_subaccount() {
    local SUBKEY="$1"
    local URL="${MODIFY_SUBACCOUNT_URL_TEMPLATE}${SUBKEY}"
    local PAYLOAD='{"use_primary_account_balance": false}'

    RESPONSE=$(curl -s -X PATCH -u "${NEXMO_API_KEY}:${NEXMO_API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$URL")

    echo -e "\n${YELLOW}Updated 'use_primary_account_balance' to false for ${CYAN}$SUBKEY${NC}\n"
}

# Function to set credit limit
set_credit_limit() {
    local SUBKEY="$1"
    local AMOUNT="$2"

    if [[ -z "$AMOUNT" || "$AMOUNT" -eq 0 ]]; then
        echo -e "\n${RED}Skipping credit transfer for $SUBKEY - Amount missing or zero.${NC}\n"
        return
    fi

    local CREDIT_TRANSFER_PAYLOAD="{\"from\":\"${NEXMO_API_KEY}\", \"to\":\"${SUBKEY}\", \"amount\": ${AMOUNT}}"

    RESPONSE=$(curl -s -X POST -u "${NEXMO_API_KEY}:${NEXMO_API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "${CREDIT_TRANSFER_PAYLOAD}" \
        "${CREDIT_TRANSFER_URL}")

    echo -e "\n${GREEN}Credit transfer successful for ${CYAN}$SUBKEY${NC}\n"
}

# Process options
case "$OPTION" in
    --set-credit)
        confirm_changes
        for i in "${!SUBACCOUNTS[@]}"; do
            SUBKEY="${SUBACCOUNTS[i]}"
            AMOUNT="${AMOUNTS[i]}"
            USE_PRIMARY_BALANCE=$(retrieve_subaccount_info "$SUBKEY")

            if [[ "$USE_PRIMARY_BALANCE" == "true" ]]; then
                modify_subaccount "$SUBKEY"
            fi

            set_credit_limit "$SUBKEY" "$AMOUNT"
        done

        echo -e "\n${BLUE}Final Account Details:${NC}"
        echo "---------------------------------------------------"
        for SUBKEY in "${SUBACCOUNTS[@]}"; do
            retrieve_subaccount_info "$SUBKEY" >> "$SUMMARY_REPORT"
        done
        cat "$SUMMARY_REPORT"
        ;;
    
    --retrieve)
        echo -e "\n${BLUE}Retrieving Current Credit Limits...${NC}"
        echo "---------------------------------------------------"
        for SUBKEY in "${SUBACCOUNTS[@]}"; do
            retrieve_subaccount_info "$SUBKEY"
        done
        ;;
    
    *)
        echo -e "\n${RED}Invalid option. Use --retrieve or --set-credit.${NC}\n"
        exit 1
        ;;
esac

