#!/usr/bin/env python3

import requests
import json
import sys
import time
from typing import List, Dict, Any, Optional

# Configuration - you can leave these empty now since we're using the Base64 token directly
API_KEY = ""  # Not needed for direct Base64 auth
API_SECRET = ""  # Not needed for direct Base64 auth
ACCOUNT_ID = "35ba62f4"  # From your URL

# The Base64 encoded auth value you provided
AUTH_TOKEN = "MzViYTYyZjQ6MzBiMzlmNGI3ODJmNmZjNA=="  # Base64 encoded API key:secret

BASE_URL = f"https://api.nexmo.com/accounts/{ACCOUNT_ID}/subaccounts"

# List of sub_api_keys to process
SUB_API_KEYS = [
    "effd325e", "d8793555", 
    "719bdccb", "e9930c32", "dd8e899f", "51a435c8", "c84b4907",
    "600cdfac", "21300440", "52848934", "7b299f0d", "fb573a64",
    "cb52dc01", "49b5b8b0", "4b1a4f2c", "cdb1f7ac", "c7914be9",
    "9acecc1a", "5c5bcdc1", "9c5a9284", "679a0c52", "ab05b349",
    "aee1e2ea", "d1d4ad11", "a2827aec", "467804b6", "4335939d",
    "6b865cc7", "f32a139a", "ab60bfac", "381cd765", "54ba999f",
    "cef2f095"
]

# Request payload
PAYLOAD = {
    "suspended": True
}

def check_auth_token() -> bool:
    """Verify that AUTH_TOKEN is not empty"""
    if not AUTH_TOKEN:
        print("\033[91mERROR: AUTH_TOKEN must be provided!\033[0m")
        print("Please edit the script and fill in this value.")
        return False
    return True

def suspend_subaccount(sub_api_key: str) -> Dict[str, Any]:
    """Suspend a specific subaccount by its API key"""
    url = f"{BASE_URL}/{sub_api_key}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {AUTH_TOKEN}"
    }
    
    # Store request details for potential debugging
    request_details = {
        "method": "PATCH",
        "url": url,
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Basic {AUTH_TOKEN[:10]}..."
        },
        "payload": PAYLOAD
    }
    
    try:
        print(f"  Making API call to: {url}")
        print(f"  With authorization header: Basic {AUTH_TOKEN[:5]}...")
        
        response = requests.patch(
            url,
            headers=headers,
            json=PAYLOAD,
            timeout=10
        )
        
        # Try to get JSON response if available
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"raw_text": response.text}
        
        result = {
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "data": response_data,
            "request": request_details
        }
        
        # For non-successful responses, print the response text
        if not result["success"]:
            print(f"  Response status: {response.status_code}")
            print(f"  Response text: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
        
        return result
        
    except requests.RequestException as e:
        print(f"  Request failed with error: {str(e)}")
        print("  Request details:")
        for key, value in request_details.items():
            if key != "headers":  # Don't show full auth header in logs
                print(f"    {key}: {value}")
            else:
                print(f"    {key}: {{'Content-Type': '{value['Content-Type']}', 'Authorization': '{value['Authorization']}'}}")
        
        return {
            "status_code": None,
            "success": False,
            "error": str(e),
            "request": request_details
        }

def process_all_subaccounts() -> None:
    """Process all subaccounts in the list"""
    if not check_auth_token():
        sys.exit(1)
        
    print(f"\n🔄 Starting to suspend {len(SUB_API_KEYS)} subaccounts...")
    
    results = {
        "success": [],
        "failed": []
    }
    
    for i, sub_key in enumerate(SUB_API_KEYS, 1):
        print(f"\n[{i}/{len(SUB_API_KEYS)}] Processing subaccount: {sub_key}...")
        
        result = suspend_subaccount(sub_key)
        
        if result["success"]:
            print(f"✅ Successfully suspended subaccount {sub_key} (Status: {result['status_code']})")
            results["success"].append(sub_key)
        else:
            error_msg = result.get("error", f"HTTP {result['status_code']}")
            print(f"❌ Failed to suspend subaccount {sub_key}: {error_msg}")
            
            # Print request details on failure for debugging
            print("  Debug info:")
            print(f"  Full endpoint URL: {result['request']['url']}")
            print(f"  HTTP method: {result['request']['method']}")
            print(f"  Payload: {json.dumps(result['request']['payload'])}")
            
            results["failed"].append((sub_key, error_msg))
        
        # Add a small delay to avoid rate limiting
        if i < len(SUB_API_KEYS):
            time.sleep(0.5)
    
    # Summary report
    print("\n" + "="*50)
    print(f"📊 SUMMARY REPORT")
    print("="*50)
    print(f"Total subaccounts processed: {len(SUB_API_KEYS)}")
    print(f"Successfully suspended: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results["failed"]:
        print("\n❌ Failed subaccounts:")
        for sub_key, error in results["failed"]:
            print(f"  - {sub_key}: {error}")
    
    print("\n✅ Process completed!")

if __name__ == "__main__":
    process_all_subaccounts()
