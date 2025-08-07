# 🌐 Vonage Numbers Manager - Web Interface

A modern, responsive web interface for managing Vonage phone numbers. This replaces the tkinter desktop application with a beautiful web-based solution that works on any platform with a web browser.

![Vonage Numbers Manager](https://img.shields.io/badge/Version-1.0-blue) ![Platform](https://img.shields.io/badge/Platform-Web-green) ![Python](https://img.shields.io/badge/Python-3.7%2B-brightgreen)

## ✨ Features

### 🔐 **Secure Credential Management**
- Local storage of API credentials with base64 encoding
- Auto-load saved credentials on startup
- Clear security warnings and best practices

### 📱 **Complete Number Management**
- **View Owned Numbers**: Real-time display of all your phone numbers
- **Search Available Numbers**: Advanced filtering by country, type, and features
- **Purchase Numbers**: Bulk purchase with subaccount assignment
- **Cancel Numbers**: Safe cancellation with multiple confirmation dialogs

### 🎨 **Modern User Interface**
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Real-time Updates**: Live activity logging via WebSocket
- **Interactive Modals**: Beautiful confirmation dialogs with detailed summaries
- **Professional Styling**: Modern gradients, animations, and visual feedback

### 🚀 **Advanced Functionality**
- **Bulk Operations**: Select multiple numbers for batch purchase/cancellation
- **Cost Calculation**: Automatic totaling of initial and monthly costs
- **Subaccount Integration**: Direct assignment to subaccounts during purchase
- **Error Handling**: Comprehensive error reporting and recovery
- **Activity Logging**: Complete audit trail of all operations

## 🛠 Quick Setup

### Option 1: Automated Setup (Recommended)

1. **Download the files** to a new directory
2. **Run the setup script**:
   ```bash
   python setup.py
   ```
3. **Start the application**:
   - **Windows**: Double-click `run_web_interface.bat`
   - **macOS/Linux**: Run `./run_web_interface.sh`
4. **Open your browser** to: http://localhost:8000

### Option 2: Manual Setup

1. **Install Python 3.7+** if not already installed
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Create directories**:
   ```bash
   mkdir static templates logs
   ```
4. **Place files in correct locations**:
   ```
   project_directory/
   ├── main.py                 # FastAPI backend
   ├── templates/
   │   └── index.html         # Main HTML template
   ├── static/
   │   ├── styles.css         # CSS styles
   │   └── app.js            # JavaScript application
   ├── requirements.txt       # Python dependencies
   └── logs/                 # Auto-created log directory
   ```
5. **Start the server**:
   ```bash
   python main.py
   ```

## 📋 Usage Guide

### 1. **Connect Your Account**
1. Enter your **Vonage API Key** and **API Secret**
2. Check **"Save credentials"** to store them locally (optional)
3. Click **"Connect Account"**
4. Your phone numbers will load automatically

### 2. **View Your Numbers**
- All owned numbers appear in the **"Your Phone Numbers"** section
- View details: country, phone number, type, features, application ID
- Use checkboxes to select numbers for cancellation
- Click **"Refresh"** to update the list

### 3. **Search for New Numbers**
1. Enter **country code** (e.g., US, GB, FR)
2. Select **number type**: Landline, Mobile, or Toll-free (optional)
3. Choose **features**: SMS, VOICE, MMS combinations (optional)
4. Set **results limit** (1-100, default: 30)
5. Click **"Search Available Numbers"**

### 4. **Purchase Numbers**
1. **Select desired numbers** using checkboxes in search results
2. Click **"Buy Selected Numbers"**
3. **Review purchase details**:
   - Number of selected numbers
   - Total initial cost
   - Total monthly cost
   - Option to assign to subaccount
4. **Confirm purchase** in the dialog
5. **View results** showing successful/failed purchases

### 5. **Cancel Numbers** ⚠️
1. **Select numbers to cancel** in your owned numbers table
2. Click **"Cancel Selected"**
3. **Read the warning carefully** - this action is IRREVERSIBLE
4. **Review the numbers** to be cancelled
5. **Confirm cancellation** (requires double confirmation)
6. **View results** showing successful/failed cancellations

## 🏗 Architecture

### **Backend (FastAPI)**
- **RESTful API** endpoints for all operations
- **WebSocket** for real-time logging
- **Proper error handling** and validation
- **Credential management** with local storage
- **Logging system** with file and real-time output

### **Frontend (Vanilla JavaScript)**
- **Modern ES6+** JavaScript
- **Responsive CSS Grid/Flexbox** layout
- **Real-time updates** via WebSocket
- **Interactive modals** for confirmations
- **Progressive enhancement** - works without JavaScript for basic functionality

### **Security**
- **Local-only storage** - no cloud dependencies
- **Base64 encoding** for credential obfuscation (not encryption)
- **Input validation** and sanitization
- **CORS protection** by keeping API calls on server side
- **Comprehensive audit logging**

## 🔧 Technical Details

### **System Requirements**
- **Python**: 3.7 or higher
- **Operating System**: Windows 10+, macOS 10.12+, or Linux
- **Web Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)
- **Network**: Internet connection for Vonage API calls
- **Disk Space**: ~50MB for application and logs

### **Dependencies**
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server for FastAPI
- **Requests**: HTTP library for API calls
- **Jinja2**: Template engine for HTML
- **Pydantic**: Data validation and serialization

### **API Endpoints**
- `GET /` - Main application page
- `POST /api/connect` - Connect to Vonage account
- `GET /api/numbers/owned` - Get owned numbers
- `POST /api/numbers/search` - Search available numbers
- `POST /api/numbers/buy` - Purchase numbers
- `POST /api/numbers/cancel` - Cancel numbers
- `GET /api/subaccounts` - Get subaccounts
- `WebSocket /ws/logs` - Real-time activity logging

## 📁 File Structure

```
vonage_numbers_manager_web/
├── main.py                     # FastAPI backend server
├── requirements.txt            # Python dependencies
├── setup.py                   # Automated setup script
├── README_WEB.md              # This documentation
├── templates/
│   └── index.html            # Main HTML template
├── static/
│   ├── styles.css            # CSS styles
│   └── app.js               # JavaScript application
├── logs/                     # Application logs (auto-created)
├── vonage_numbers_credentials.ini  # Saved credentials (auto-created)
├── run_web_interface.bat     # Windows run script (auto-created)
└── run_web_interface.sh      # Unix run script (auto-created)
```

## 🚨 Important Warnings

### **Credential Security**
- Credentials are stored locally with **basic encoding, NOT encryption**
- Only use on **trusted computers**
- Consider **rotating API credentials** regularly
- The application warns users about security limitations

### **Number Operations**
- **Purchases**: Cost real money - review carefully before confirming
- **Cancellations**: **IRREVERSIBLE** - once cancelled, numbers cannot be recovered
- **Testing**: Always test in a safe environment first
- **Account Permissions**: Ensure your Vonage account has necessary permissions

### **Software Disclaimer**
This software is provided **"as-is" without any warranty**. Users bear **full responsibility** for any consequences of using this application, including:
- Phone number purchases and associated costs
- Irreversible number cancellations
- API usage and rate limiting
- Account security and credential management

## 🐛 Troubleshooting

### **Connection Issues**
- **Invalid credentials**: Verify API key and secret are correct
- **Network errors**: Check internet connection and firewall settings
- **Account issues**: Ensure Vonage account is active and not suspended

### **Search Problems**
- **No results**: Try different country codes (US, GB, FR, etc.)
- **Invalid country**: Use 2-letter ISO country codes
- **Server errors**: Check activity log for detailed error messages

### **Purchase/Cancel Failures**
- **Insufficient balance**: Check your Vonage account balance
- **Permission denied**: Verify account has necessary permissions
- **Number unavailable**: Number may have been purchased by someone else
- **Rate limiting**: Wait before making additional API calls

### **Technical Issues**
- **Port conflicts**: Change port in main.py if 8000 is in use
- **Python errors**: Ensure all dependencies are installed correctly
- **Browser issues**: Try a different browser or clear cache
- **WebSocket failures**: Check for proxy or firewall interference

## 🔄 Migration from tkinter Version

The web interface provides **all functionality** of the original tkinter application plus:

### **Improvements**
- ✅ **Better UI/UX**: Modern, responsive design
- ✅ **Cross-platform**: Works on any device with a browser
- ✅ **Real-time logging**: Live activity updates via WebSocket
- ✅ **Better error handling**: More detailed error messages and recovery
- ✅ **Mobile support**: Works on tablets and phones
- ✅ **No installation**: No need for tkinter or GUI libraries

### **Migration Steps**
1. **Backup**: Save any important logs from the tkinter version
2. **Credentials**: The web version can reuse saved credentials from `vonage_numbers_credentials.ini`
3. **Setup**: Follow the setup instructions above
4. **Test**: Verify all functionality works as expected
5. **Deploy**: The web version can be deployed to a server for team access

## 📞 Support & Resources

### **Vonage API Documentation**
- [Numbers API Reference](https://developer.vonage.com/en/api/numbers)
- [Getting Started Guide](https://developer.vonage.com/en/getting-started/overview)
- [API Authentication](https://developer.vonage.com/en/getting-started/authentication)

### **Web Interface Help**
- **Built-in Help**: Click the "📖 Help" button in the application
- **Activity Logs**: Check the real-time activity log for detailed information
- **Log Files**: Review log files in the `logs/` directory
- **Browser Console**: Check for JavaScript errors (F12 in most browsers)

### **Getting Support**
1. **Check the built-in help system** in the web interface
2. **Review activity logs** for specific error messages
3. **Verify API credentials** and account permissions
4. **Test with different browsers** if experiencing issues
5. **Contact Vonage support** for API-related issues

## 🙏 Acknowledgments

- **Vonage**: For providing the excellent Numbers API
- **FastAPI**: For the amazing Python web framework
- **Original tkinter application**: This web interface builds upon that foundation

---

**Version**: 1.0  
**Last Updated**: January 2025  
**Compatibility**: Python 3.7+, Modern Web Browsers  
**License**: Use at your own risk - no warranty provided