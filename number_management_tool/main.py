#!/usr/bin/env python3
"""
Vonage Numbers Manager - Web Interface Backend
FastAPI backend for the Vonage Numbers Manager web application.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from pydantic import BaseModel
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import configparser
import base64
import requests
import threading
import queue

# Import the existing API client classes (slightly modified)
class CredentialManager:
    """Manages saving and loading of API credentials with basic security."""
    
    def __init__(self):
        self.config_file = "vonage_numbers_credentials.ini"
        self.config = configparser.ConfigParser()
        
    def _encode_credential(self, credential: str) -> str:
        """Encode credential with base64 for basic obfuscation."""
        return base64.b64encode(credential.encode()).decode()
    
    def _decode_credential(self, encoded_credential: str) -> str:
        """Decode credential from base64."""
        try:
            return base64.b64decode(encoded_credential.encode()).decode()
        except Exception:
            return ""
    
    def save_credentials(self, api_key: str, api_secret: str) -> bool:
        """Save credentials to local file with basic encoding."""
        try:
            self.config['CREDENTIALS'] = {
                'api_key': self._encode_credential(api_key),
                'api_secret': self._encode_credential(api_secret),
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)
            
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False
    
    def load_credentials(self) -> Dict[str, str]:
        """Load credentials from local file."""
        try:
            if not os.path.exists(self.config_file):
                return {}
            
            self.config.read(self.config_file)
            
            if 'CREDENTIALS' not in self.config:
                return {}
            
            creds = self.config['CREDENTIALS']
            return {
                'api_key': self._decode_credential(creds.get('api_key', '')),
                'api_secret': self._decode_credential(creds.get('api_secret', '')),
                'saved_at': creds.get('saved_at', '')
            }
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return {}
    
    def delete_credentials(self) -> bool:
        """Delete saved credentials."""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            return True
        except Exception as e:
            print(f"Error deleting credentials: {e}")
            return False
    
    def has_saved_credentials(self) -> bool:
        """Check if credentials are saved."""
        return os.path.exists(self.config_file)


class VonageNumbersAPIClient:
    """Handles all Vonage Numbers API interactions with proper authentication and logging."""
    
    def __init__(self, log_queue=None):
        self.base_url = "https://rest.nexmo.com"
        self.api_key = None
        self.api_secret = None
        self.auth_header = None
        self.log_queue = log_queue
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for API interactions."""
        logger = logging.getLogger('VonageNumbersAPI')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # File handler for general logs
        file_handler = logging.FileHandler(f'logs/vonage_numbers_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _log_message(self, message: str, level: str = "INFO"):
        """Add message to both file log and WebSocket queue."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        
        # Log to file
        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # Add to queue for WebSocket transmission
        if self.log_queue:
            try:
                self.log_queue.put_nowait({
                    "timestamp": timestamp,
                    "level": level,
                    "message": message
                })
            except:
                pass  # Queue might be full, skip
    
    def set_credentials(self, api_key: str, api_secret: str) -> None:
        """Set and encode API credentials."""
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Create base64 encoded auth header
        credentials = f"{api_key}:{api_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"
        
        self._log_message(f"Credentials set for API key: {api_key[:8]}...")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Vonage Numbers API."""
        # Determine base URL based on endpoint
        if endpoint.startswith('/accounts/'):
            base_url = "https://api.nexmo.com"  # Subaccounts API uses api.nexmo.com
        else:
            base_url = self.base_url  # Numbers API uses rest.nexmo.com
            
        url = f"{base_url}{endpoint}"
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json'
        }
        
        self._log_message(f"Making {method} request to {url}")
        if params:
            self._log_message(f"Parameters: {params}")
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            self._log_message(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self._log_message("Request successful")
                return {'success': True, 'data': result}
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                self._log_message(error_msg, "ERROR")
                return {'success': False, 'error': error_msg, 'status_code': response.status_code}
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout - please check your connection"
            self._log_message(error_msg, "ERROR")
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error - please check your internet connection"
            self._log_message(error_msg, "ERROR")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._log_message(error_msg, "ERROR")
            return {'success': False, 'error': error_msg}
    
    def get_owned_numbers(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Retrieve all inbound numbers associated with your Vonage account."""
        return self._make_request('GET', '/account/numbers', params)
    
    def search_available_numbers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for available numbers."""
        return self._make_request('GET', '/number/search', params)
    
    def get_subaccounts(self) -> Dict[str, Any]:
        """Retrieve list of subaccounts."""
        endpoint = f"/accounts/{self.api_key}/subaccounts"
        return self._make_request('GET', endpoint)
    
    def buy_number(self, country: str, msisdn: str, target_api_key: Optional[str] = None) -> Dict[str, Any]:
        """Buy a specific number."""
        url = f"{self.base_url}/number/buy"
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'country': country,
            'msisdn': msisdn
        }
        
        if target_api_key:
            data['target_api_key'] = target_api_key
        
        self._log_message(f"Making POST request to {url}")
        self._log_message(f"Buying number: {msisdn} in {country}")
        if target_api_key:
            self._log_message(f"Target API key: {target_api_key}")
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            
            self._log_message(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self._log_message("Purchase request successful")
                return {'success': True, 'data': result}
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                self._log_message(error_msg, "ERROR")
                return {'success': False, 'error': error_msg, 'status_code': response.status_code}
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._log_message(error_msg, "ERROR")
            return {'success': False, 'error': error_msg}
    
    def cancel_number(self, country: str, msisdn: str) -> Dict[str, Any]:
        """Cancel a specific number."""
        url = f"{self.base_url}/number/cancel"
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'country': country,
            'msisdn': msisdn
        }
        
        self._log_message(f"Making POST request to {url}")
        self._log_message(f"Cancelling number: {msisdn} in {country}")
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            
            self._log_message(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self._log_message("Cancellation request successful")
                return {'success': True, 'data': result}
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                self._log_message(error_msg, "ERROR")
                return {'success': False, 'error': error_msg, 'status_code': response.status_code}
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._log_message(error_msg, "ERROR")
            return {'success': False, 'error': error_msg}


# Pydantic models for API requests
class CredentialsRequest(BaseModel):
    api_key: str
    api_secret: str
    save_credentials: bool = False

class SearchRequest(BaseModel):
    country: str
    type: Optional[str] = None
    features: Optional[str] = None
    size: int = 30

class PurchaseRequest(BaseModel):
    numbers: List[Dict[str, Any]]
    target_api_key: Optional[str] = None

class CancelRequest(BaseModel):
    numbers: List[Dict[str, Any]]

# FastAPI app initialization
app = FastAPI(title="Vonage Numbers Manager", description="Web interface for managing Vonage phone numbers")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global instances
credential_manager = CredentialManager()
log_queue = asyncio.Queue()
api_client = None
connected_websockets = []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/credentials/load")
async def load_credentials():
    """Load saved credentials."""
    try:
        credentials = credential_manager.load_credentials()
        if credentials and credentials.get('api_key') and credentials.get('api_secret'):
            return {
                "success": True,
                "data": {
                    "api_key": credentials['api_key'],
                    "api_secret": credentials['api_secret'],
                    "saved_at": credentials.get('saved_at', '')
                }
            }
        else:
            return {"success": False, "error": "No saved credentials found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/credentials/save")
async def save_credentials(request: CredentialsRequest):
    """Save credentials."""
    try:
        success = credential_manager.save_credentials(request.api_key, request.api_secret)
        if success:
            return {"success": True, "message": "Credentials saved successfully"}
        else:
            return {"success": False, "error": "Failed to save credentials"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/credentials")
async def clear_credentials():
    """Clear saved credentials."""
    try:
        success = credential_manager.delete_credentials()
        if success:
            return {"success": True, "message": "Credentials cleared successfully"}
        else:
            return {"success": False, "error": "Failed to clear credentials"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/connect")
async def connect_account(request: CredentialsRequest):
    """Connect to account and retrieve owned numbers."""
    global api_client
    
    try:
        # Create API client instance with log queue
        api_client = VonageNumbersAPIClient(log_queue=log_queue)
        api_client.set_credentials(request.api_key, request.api_secret)
        
        # Get owned numbers
        result = api_client.get_owned_numbers()
        
        if result['success']:
            # Auto-save credentials if requested
            if request.save_credentials:
                credential_manager.save_credentials(request.api_key, request.api_secret)
            
            return {
                "success": True,
                "data": result['data'],
                "message": f"Connected successfully - {len(result['data'].get('numbers', []))} numbers found"
            }
        else:
            return {"success": False, "error": result.get('error', 'Connection failed')}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/numbers/owned")
async def get_owned_numbers():
    """Get owned numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="Not connected to account")
    
    try:
        result = api_client.get_owned_numbers()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/numbers/search")
async def search_numbers(request: SearchRequest):
    """Search for available numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="Not connected to account")
    
    try:
        params = {'country': request.country.upper()}
        
        if request.type:
            params['type'] = request.type
        if request.features and request.features != 'Any':
            params['features'] = request.features
        if request.size:
            params['size'] = request.size
            
        result = api_client.search_available_numbers(params)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/subaccounts")
async def get_subaccounts():
    """Get subaccounts for purchase assignment."""
    if not api_client:
        raise HTTPException(status_code=400, detail="Not connected to account")
    
    try:
        result = api_client.get_subaccounts()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/numbers/buy")
async def buy_numbers(request: PurchaseRequest):
    """Buy selected numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="Not connected to account")
    
    try:
        results = []
        
        for number in request.numbers:
            country = number.get('country', '')
            msisdn = number.get('msisdn', '')
            
            if country and msisdn:
                result = api_client.buy_number(country, msisdn, request.target_api_key)
                results.append({
                    'number': msisdn,
                    'country': country,
                    'success': result['success'],
                    'error': result.get('error') if not result['success'] else None
                })
            else:
                results.append({
                    'number': msisdn,
                    'country': country,
                    'success': False,
                    'error': 'Invalid number data'
                })
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        return {
            "success": True,
            "data": {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "results": results
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/numbers/cancel")
async def cancel_numbers(request: CancelRequest):
    """Cancel selected numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="Not connected to account")
    
    try:
        results = []
        
        for number in request.numbers:
            country = number.get('country', '')
            msisdn = number.get('msisdn', '')
            
            if country and msisdn:
                result = api_client.cancel_number(country, msisdn)
                results.append({
                    'number': msisdn,
                    'country': country,
                    'success': result['success'],
                    'error': result.get('error') if not result['success'] else None
                })
            else:
                results.append({
                    'number': msisdn,
                    'country': country,
                    'success': False,
                    'error': 'Invalid number data'
                })
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        return {
            "success": True,
            "data": {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "results": results
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time activity logs."""
    await websocket.accept()
    connected_websockets.append(websocket)
    
    try:
        while True:
            # Get log messages from queue
            try:
                log_message = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                await websocket.send_text(json.dumps(log_message))
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({"type": "ping"}))
            except Exception as e:
                print(f"Error sending log message: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    
    # Create necessary directories
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("Starting Vonage Numbers Manager Web Interface...")
    print("Open http://localhost:8000 in your browser")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")