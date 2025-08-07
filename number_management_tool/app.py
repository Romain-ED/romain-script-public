#!/usr/bin/env python3
"""
Simple Vonage Numbers Manager - Render Compatible
"""

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Simple app for testing deployment
app = FastAPI(title="Vonage Numbers Manager", description="Web interface for managing Vonage phone numbers")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Vonage Numbers Manager is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "vonage-numbers-manager"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)