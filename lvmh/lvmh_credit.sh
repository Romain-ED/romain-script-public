#!/usr/bin/env bash

# Set API credentials
API_KEY="35ba62f4"
API_SECRET="30b39f4b782f6fc4"

# API endpoint and payload
FROM_ACCOUNT="35ba62f4"
TO_ACCOUNT="fcd9dde5"
AMOUNT="1000"
API_URL="https://api.nexmo.com/accounts/${API_KEY}/credit-transfers"
PAYLOAD="{\"from\":\"${FROM_ACCOUNT}\", \"to\":\"${TO_ACCOUNT}\", \"amount\": ${AMOUNT}}"

# Execute POST request
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST -u "${API_KEY}:${API_SECRET}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}" \
    "${API_URL}")

# Check response status
if [[ "$response" == "200" ]]; then
    echo "Credit transfer successful."
else
    echo "Failed to transfer credit. HTTP Status: $response"
fi

