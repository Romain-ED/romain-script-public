#!/usr/bin/env python3
"""
Vonage Numbers Manager - Web Interface
Secure FastAPI backend ready for online hosting (Render, Railway, Fly.io, etc.)
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from pydantic import BaseModel
import json
import asyncio
import logging
import secrets
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import base64
import requests

# Security
security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic authentication for the application."""
    correct_username = secrets.compare_digest(
        credentials.username, 
        os.getenv("APP_USERNAME", "admin")
    )
    correct_password = secrets.compare_digest(
        credentials.password, 
        os.getenv("APP_PASSWORD", "changeme123")
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class VonageNumbersAPIClient:
    """Handles all Vonage Numbers API interactions with proper authentication and logging."""
    
    def __init__(self, log_queue=None):
        self.base_url = "https://rest.nexmo.com"
        # Get credentials from environment variables
        self.api_key = os.getenv("VONAGE_API_KEY")
        self.api_secret = os.getenv("VONAGE_API_SECRET")
        self.auth_header = None
        self.log_queue = log_queue
        self.logger = self._setup_logger()
        
        # Set auth header if credentials are available
        if self.api_key and self.api_secret:
            self.set_credentials(self.api_key, self.api_secret)
    
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
        if not self.auth_header:
            return {'success': False, 'error': 'API credentials not configured'}
            
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
        if not self.api_key:
            return {'success': False, 'error': 'API key not configured'}
        endpoint = f"/accounts/{self.api_key}/subaccounts"
        return self._make_request('GET', endpoint)
    
    def buy_number(self, country: str, msisdn: str, target_api_key: Optional[str] = None) -> Dict[str, Any]:
        """Buy a specific number."""
        if not self.auth_header:
            return {'success': False, 'error': 'API credentials not configured'}
            
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
        if not self.auth_header:
            return {'success': False, 'error': 'API credentials not configured'}
            
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
app = FastAPI(
    title="Vonage Numbers Manager", 
    description="Secure web interface for managing Vonage phone numbers",
    docs_url=None,  # Disable docs in production
    redoc_url=None
)

# CORS configuration for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("DEBUG", "false").lower() == "true" else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global instances
log_queue = asyncio.Queue()
api_client = None
connected_websockets = []

async def startup_event():
    """Initialize API client on startup."""
    global api_client
    
    # Check if credentials are configured
    if not os.getenv("VONAGE_API_KEY") or not os.getenv("VONAGE_API_SECRET"):
        print("⚠️ WARNING: VONAGE_API_KEY and VONAGE_API_SECRET environment variables not set!")
        print("   The application will not be able to connect to Vonage APIs.")
        print("   Please set these environment variables in your hosting platform.")
    
    api_client = VonageNumbersAPIClient(log_queue=log_queue)

# Add startup event to FastAPI
app.add_event_handler("startup", startup_event)

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def read_root(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/connect", dependencies=[Depends(get_current_user)])
async def connect_account():
    """Connect to account and retrieve owned numbers."""
    global api_client
    
    try:
        if not api_client.api_key or not api_client.api_secret:
            return {"success": False, "error": "API credentials not configured in environment variables"}
        
        # Get owned numbers
        result = api_client.get_owned_numbers()
        
        if result['success']:
            return {
                "success": True,
                "data": result['data'],
                "message": f"Connected successfully - {len(result['data'].get('numbers', []))} numbers found"
            }
        else:
            return {"success": False, "error": result.get('error', 'Connection failed')}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/numbers/owned", dependencies=[Depends(get_current_user)])
async def get_owned_numbers():
    """Get owned numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="API client not initialized")
    
    try:
        result = api_client.get_owned_numbers()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/numbers/search", dependencies=[Depends(get_current_user)])
async def search_numbers(request: SearchRequest):
    """Search for available numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="API client not initialized")
    
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

@app.get("/api/subaccounts", dependencies=[Depends(get_current_user)])
async def get_subaccounts():
    """Get subaccounts for purchase assignment."""
    if not api_client:
        raise HTTPException(status_code=400, detail="API client not initialized")
    
    try:
        result = api_client.get_subaccounts()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/numbers/buy", dependencies=[Depends(get_current_user)])
async def buy_numbers(request: PurchaseRequest):
    """Buy selected numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="API client not initialized")
    
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

@app.post("/api/numbers/cancel", dependencies=[Depends(get_current_user)])
async def cancel_numbers(request: CancelRequest):
    """Cancel selected numbers."""
    if not api_client:
        raise HTTPException(status_code=400, detail="API client not initialized")
    
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
    
    # Print startup information
    print("=" * 60)
    print("🔥 VONAGE NUMBERS MANAGER - WEB INTERFACE 🔥")
    print("=" * 60)
    
    # Check environment variables
    vonage_key = os.getenv("VONAGE_API_KEY")
    vonage_secret = os.getenv("VONAGE_API_SECRET")
    app_username = os.getenv("APP_USERNAME", "admin")
    app_password = os.getenv("APP_PASSWORD", "changeme123")
    
    print(f"Vonage API Key: {'✅ Set' if vonage_key else '❌ Missing'}")
    print(f"Vonage API Secret: {'✅ Set' if vonage_secret else '❌ Missing'}")
    print(f"App Username: {app_username}")
    print(f"App Password: {'✅ Set' if app_password != 'changeme123' else '⚠️ Using default (CHANGE THIS!)'}")
    print()
    
    if not vonage_key or not vonage_secret:
        print("⚠️ WARNING: Vonage API credentials not configured!")
        print("   Set environment variables:")
        print("   • VONAGE_API_KEY=your_api_key")
        print("   • VONAGE_API_SECRET=your_api_secret")
        print()
    
    if app_password == "changeme123":
        print("🚨 SECURITY WARNING: Using default password!")
        print("   Set environment variable:")
        print("   • APP_PASSWORD=your_secure_password")
        print()
    
    # Create necessary directories
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Get port from environment (for hosting platforms)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting server on {host}:{port}")
    print("🌐 Access URL: http://localhost:8000" if port == 8000 else f"🌐 Access URL: http://localhost:{port}")
    print("👤 Login with username/password you configured")
    print("=" * 60)
    
    uvicorn.run(app, host=host, port=port, log_level="info")