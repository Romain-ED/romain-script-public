#!/usr/bin/env python3
"""
Vonage Numbers Manager - Web Interface Setup Script
Automatically sets up the web interface and starts the server.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Print welcome banner."""
    print("=" * 60)
    print("🔥 VONAGE NUMBERS MANAGER - WEB INTERFACE SETUP 🔥")
    print("=" * 60)
    print("Setting up modern web interface for Vonage Numbers API...")
    print()

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")

def create_directories():
    """Create necessary directories."""
    directories = ['static', 'templates', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")

def install_dependencies():
    """Install required Python packages."""
    print("\n📦 Installing dependencies...")
    
    try:
        # Try to install packages
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'fastapi==0.104.1',
            'uvicorn[standard]==0.24.0',
            'jinja2==3.1.2',
            'python-multipart==0.0.6',
            'requests==2.31.0',
            'pydantic==2.5.0',
            'python-dotenv==1.0.0'
        ])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("   Please run: pip install -r requirements.txt")
        return False
    
    return True

def create_run_script():
    """Create platform-specific run scripts."""
    
    # Windows batch file
    windows_script = """@echo off
title Vonage Numbers Manager - Web Interface
echo Starting Vonage Numbers Manager Web Interface...
echo Open http://localhost:8000 in your browser
echo.
python main.py
pause
"""
    
    # Unix shell script
    unix_script = """#!/bin/bash
echo "Starting Vonage Numbers Manager Web Interface..."
echo "Open http://localhost:8000 in your browser"
echo ""
python3 main.py
"""
    
    try:
        if platform.system() == "Windows":
            with open("run_web_interface.bat", "w") as f:
                f.write(windows_script)
            print("✅ Created run_web_interface.bat")
        else:
            with open("run_web_interface.sh", "w") as f:
                f.write(unix_script)
            os.chmod("run_web_interface.sh", 0o755)
            print("✅ Created run_web_interface.sh")
    except Exception as e:
        print(f"⚠️ Could not create run script: {e}")

def create_sample_env():
    """Create sample environment file."""
    env_content = """# Vonage Numbers Manager - Environment Configuration
# Copy this to .env and customize as needed

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Logging
LOG_LEVEL=INFO

# Security (Optional - for production)
# SECRET_KEY=your-secret-key-here
"""
    
    try:
        if not os.path.exists('.env.example'):
            with open('.env.example', 'w') as f:
                f.write(env_content)
            print("✅ Created .env.example")
    except Exception as e:
        print(f"⚠️ Could not create .env.example: {e}")

def print_completion_message():
    """Print setup completion message."""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE! 🎉")
    print("=" * 60)
    print()
    print("Your Vonage Numbers Manager Web Interface is ready!")
    print()
    print("📋 TO START THE APPLICATION:")
    
    if platform.system() == "Windows":
        print("   • Double-click: run_web_interface.bat")
        print("   • Or run: python main.py")
    else:
        print("   • Run: ./run_web_interface.sh")
        print("   • Or run: python3 main.py")
    
    print()
    print("🌐 THEN OPEN IN YOUR BROWSER:")
    print("   • http://localhost:8000")
    print()
    print("📚 FEATURES:")
    print("   ✅ Modern, responsive web interface")
    print("   ✅ Real-time activity logging")
    print("   ✅ Secure credential management")
    print("   ✅ Bulk number operations")
    print("   ✅ Interactive purchase/cancellation dialogs")
    print("   ✅ Cross-platform compatibility")
    print()
    print("⚠️ IMPORTANT:")
    print("   • Keep your Vonage API credentials secure")
    print("   • Test in a safe environment first")
    print("   • This software is provided 'as-is' without warranty")
    print()
    print("🔗 Need help? Check the built-in help system in the web interface!")
    print("=" * 60)

def main():
    """Main setup function."""
    print_banner()
    
    # Check system requirements
    check_python_version()
    
    # Create directories
    print("\n📁 Creating directories...")
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create helper files
    print("\n🔧 Creating helper files...")
    create_run_script()
    create_sample_env()
    
    # Final message
    print_completion_message()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)