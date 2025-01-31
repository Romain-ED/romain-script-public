#!/usr/bin/env bash


curl -X PATCH -u 35ba62f4:30b39f4b782f6fc4 https://api.nexmo.com/accounts/35ba62f4/subaccounts/b6473eb9 \
     -H "Content-Type: application/json"  \
     -d $'{"use_primary_account_balance":false}'
