#!/usr/bin/env bash

# Set API credentials
API_KEY="35ba62f4"
API_SECRET="30b39f4b782f6fc4"

# API endpoint and payload
SUBACCOUNT_ID="lvmh_credit_disable_shared_balance_v2"
API_URL="https://api.nexmo.com/accounts/${API_KEY}/subaccounts/${SUBACCOUNT_ID}"
PAYLOAD='{"use_primary_account_balance":false}'

# Execute PATCH request
response=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH -u "${API_KEY}:${API_SECRET}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}" \
    "${API_URL}")

# Check response status
if [[ "$response" == "200" ]]; then
    echo "Subaccount updated successfully."
else
    echo "Failed to update subaccount. HTTP Status: $response"
fi


