// Global variables
let isConnected = false;
let ownedNumbers = [];
let availableNumbers = [];
let selectedOwned = new Set();
let selectedAvailable = new Set();
let autoScroll = true;
let logWebSocket = null;
let currentAccountBalance = null;

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Vonage Numbers Manager - Web Interface Loaded');
    
    // Load version information
    loadVersionInfo();
    
    // Check connection status on startup
    checkConnectionStatus();
    
    // Initialize WebSocket for real-time logging
    initializeWebSocket();
    
    // Set up input listeners
    setupInputListeners();
    
    // Initial state
    updateButtonStates();
});

// WebSocket for real-time logging
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
    
    logWebSocket = new WebSocket(wsUrl);
    
    logWebSocket.onopen = function(event) {
        addLogEntry('WebSocket connection established', 'info');
    };
    
    logWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type !== 'ping') {
            addLogEntry(data.message, data.level.toLowerCase(), data.timestamp);
        }
    };
    
    logWebSocket.onclose = function(event) {
        addLogEntry('WebSocket connection closed', 'warning');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
            addLogEntry('Attempting to reconnect...', 'info');
            initializeWebSocket();
        }, 5000);
    };
    
    logWebSocket.onerror = function(error) {
        addLogEntry('WebSocket error occurred', 'error');
    };
}

// Setup input listeners
function setupInputListeners() {
    // Enter key support for credentials
    document.getElementById('apiKey').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') connectAccount();
    });
    
    document.getElementById('apiSecret').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') connectAccount();
    });
    
    // Enter key support for search
    document.getElementById('countryCode').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !document.getElementById('searchBtn').disabled) {
            searchNumbers();
        }
    });
    
    // Auto-uppercase country code
    document.getElementById('countryCode').addEventListener('input', function(e) {
        e.target.value = e.target.value.toUpperCase().slice(0, 2);
    });
}

// Utility Functions
function showLoading(text = 'Loading...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function updateStatus(message, type = 'info') {
    const statusElement = document.getElementById('connectionStatus');
    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;
}

function addLogEntry(message, level = 'info', timestamp = null) {
    if (!timestamp) {
        timestamp = new Date().toLocaleTimeString();
    }
    
    const logContent = document.getElementById('logContent');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${level}`;
    
    logEntry.innerHTML = `
        <span class="timestamp">[${timestamp}]</span>
        <span class="level">${level.toUpperCase()}:</span>
        <span class="message">${message}</span>
    `;
    
    logContent.appendChild(logEntry);
    
    // Auto-scroll to bottom if enabled
    if (autoScroll) {
        logContent.scrollTop = logContent.scrollHeight;
    }
}

function clearLog() {
    document.getElementById('logContent').innerHTML = '';
    addLogEntry('Activity log cleared', 'info');
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const button = document.getElementById('autoScrollText');
    button.textContent = autoScroll ? 'Disable Auto-scroll' : 'Enable Auto-scroll';
    addLogEntry(`Auto-scroll ${autoScroll ? 'enabled' : 'disabled'}`, 'info');
}

// Modal Functions
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Help tab switching
function showHelpTab(tabName) {
    // Hide all help content
    document.querySelectorAll('.help-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.help-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected content and activate tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            closeModal(modal.id);
        }
    });
});

// Credential Management Functions
async function loadCredentials(silent = false) {
    try {
        const response = await fetch('/api/credentials/load');
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('apiKey').value = result.data.api_key;
            document.getElementById('apiSecret').value = result.data.api_secret;
            
            if (!silent) {
                const savedDate = new Date(result.data.saved_at).toLocaleString();
                updateStatus(`Loaded credentials saved on ${savedDate}`, 'success');
                addLogEntry('Credentials loaded from storage', 'info');
            }
        } else {
            if (!silent) {
                updateStatus('No saved credentials found', 'error');
            }
        }
    } catch (error) {
        if (!silent) {
            updateStatus('Error loading credentials', 'error');
            addLogEntry(`Error loading credentials: ${error.message}`, 'error');
        }
    }
    
    updateButtonStates();
}

// Removed old saveCredentials and clearCredentials functions 
// (incompatible with multi-user mode)

// Connection and Account Management
async function connectAccount() {
    const apiKey = document.getElementById('apiKey').value.trim();
    const apiSecret = document.getElementById('apiSecret').value.trim();
    
    if (!apiKey || !apiSecret) {
        updateStatus('Please enter both API key and secret', 'error');
        return;
    }
    
    try {
        showLoading('Connecting to account...');
        updateStatus('Connecting to account...', 'info');
        
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                api_key: apiKey,
                api_secret: apiSecret,
                save_credentials: false  // Multi-user mode: no credential saving
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            isConnected = true;
            ownedNumbers = result.data.numbers || [];
            
            updateStatus(result.message, 'success');
            updateOwnedNumbersDisplay();
            updateButtonStates();
            addLogEntry(`Connected successfully - ${ownedNumbers.length} numbers found`, 'info');
            
            // Load account information after successful connection
            await loadAccountInfo();
        } else {
            isConnected = false;
            updateStatus(`Connection failed: ${result.error}`, 'error');
            addLogEntry(`Connection failed: ${result.error}`, 'error');
            updateButtonStates();
        }
    } catch (error) {
        isConnected = false;
        updateStatus('Connection error occurred', 'error');
        addLogEntry(`Connection error: ${error.message}`, 'error');
        updateButtonStates();
    } finally {
        hideLoading();
    }
}

async function refreshNumbers() {
    if (!isConnected) return;
    
    try {
        showLoading('Refreshing numbers...');
        
        const response = await fetch('/api/numbers/owned');
        const result = await response.json();
        
        if (result.success) {
            ownedNumbers = result.data.numbers || [];
            updateOwnedNumbersDisplay();
            addLogEntry(`Numbers refreshed - ${ownedNumbers.length} numbers found`, 'info');
        } else {
            addLogEntry(`Failed to refresh numbers: ${result.error}`, 'error');
        }
    } catch (error) {
        addLogEntry(`Error refreshing numbers: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Owned Numbers Display
function updateOwnedNumbersDisplay() {
    const tbody = document.getElementById('ownedNumbersBody');
    const countElement = document.getElementById('numbersCount');
    
    countElement.textContent = ownedNumbers.length;
    selectedOwned.clear();
    
    if (ownedNumbers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    No phone numbers found in your account
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = ownedNumbers.map((number, index) => `
        <tr>
            <td>
                <input type="checkbox" id="owned_${index}" 
                       onchange="toggleOwnedNumber(${index})">
            </td>
            <td>${number.country || 'N/A'}</td>
            <td>${number.msisdn || 'N/A'}</td>
            <td>${number.type || 'N/A'}</td>
            <td>${(number.features || []).join(', ') || 'N/A'}</td>
            <td>${number.app_id || number.messagesCallbackValue || 'N/A'}</td>
        </tr>
    `).join('');
    
    updateCancelButton();
}

function toggleOwnedNumber(index) {
    const checkbox = document.getElementById(`owned_${index}`);
    if (checkbox.checked) {
        selectedOwned.add(index);
    } else {
        selectedOwned.delete(index);
    }
    updateCancelButton();
}

function toggleAllOwned() {
    const selectAll = document.getElementById('selectAllOwned');
    const checkboxes = document.querySelectorAll('input[id^="owned_"]');
    
    selectedOwned.clear();
    
    checkboxes.forEach((checkbox, index) => {
        checkbox.checked = selectAll.checked;
        if (selectAll.checked) {
            selectedOwned.add(index);
        }
    });
    
    updateCancelButton();
}

function updateCancelButton() {
    const cancelBtn = document.getElementById('cancelBtn');
    const count = selectedOwned.size;
    
    if (count > 0) {
        cancelBtn.textContent = `Cancel Selected (${count})`;
        cancelBtn.disabled = false;
    } else {
        cancelBtn.textContent = 'Cancel Selected';
        cancelBtn.disabled = ownedNumbers.length === 0;
    }
}

// Search Functions
async function searchNumbers() {
    const country = document.getElementById('countryCode').value.trim().toUpperCase();
    const numberType = document.getElementById('numberType').value;
    const features = document.getElementById('features').value;
    const size = parseInt(document.getElementById('resultsSize').value);
    
    if (!country || country.length !== 2) {
        updateSearchResults('Please enter a valid 2-letter country code', 'error');
        return;
    }
    
    if (size < 1 || size > 100) {
        updateSearchResults('Results size must be between 1 and 100', 'error');
        return;
    }
    
    try {
        showLoading('Searching available numbers...');
        updateSearchResults('Searching available numbers...', 'info');
        
        const response = await fetch('/api/numbers/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                country: country,
                type: numberType || null,
                features: features !== 'Any' ? features : null,
                size: size
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            availableNumbers = result.data.numbers || [];
            updateAvailableNumbersDisplay();
            
            const count = result.data.count || availableNumbers.length;
            updateSearchResults(`Found ${availableNumbers.length} available numbers (total: ${count})`, 'success');
            addLogEntry(`Search completed - ${availableNumbers.length} numbers found`, 'info');
        } else {
            availableNumbers = [];
            updateAvailableNumbersDisplay();
            updateSearchResults(`Search failed: ${result.error}`, 'error');
            addLogEntry(`Search failed: ${result.error}`, 'error');
        }
    } catch (error) {
        availableNumbers = [];
        updateAvailableNumbersDisplay();
        updateSearchResults('Search error occurred', 'error');
        addLogEntry(`Search error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function updateSearchResults(message, type = 'info') {
    const resultsElement = document.getElementById('searchResults');
    resultsElement.textContent = message;
    resultsElement.className = `search-results ${type}`;
}

// Available Numbers Display
function updateAvailableNumbersDisplay() {
    const tbody = document.getElementById('availableNumbersBody');
    selectedAvailable.clear();
    
    if (availableNumbers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    No available numbers found. Try different search criteria.
                </td>
            </tr>
        `;
        updateBuyButton();
        return;
    }
    
    tbody.innerHTML = availableNumbers.map((number, index) => `
        <tr>
            <td>
                <input type="checkbox" id="available_${index}" 
                       onchange="toggleAvailableNumber(${index})">
            </td>
            <td>${number.country || 'N/A'}</td>
            <td>${number.msisdn || 'N/A'}</td>
            <td>${number.type || 'N/A'}</td>
            <td>€${number.initialPrice || '0.00'}</td>
            <td>€${number.cost || '0.00'}</td>
            <td>${(number.features || []).join(', ') || 'N/A'}</td>
        </tr>
    `).join('');
    
    updateBuyButton();
}

function toggleAvailableNumber(index) {
    const checkbox = document.getElementById(`available_${index}`);
    if (checkbox.checked) {
        selectedAvailable.add(index);
    } else {
        selectedAvailable.delete(index);
    }
    updateBuyButton();
}

function toggleAllAvailable() {
    const selectAll = document.getElementById('selectAllAvailable');
    const checkboxes = document.querySelectorAll('input[id^="available_"]');
    
    selectedAvailable.clear();
    
    checkboxes.forEach((checkbox, index) => {
        checkbox.checked = selectAll.checked;
        if (selectAll.checked) {
            selectedAvailable.add(index);
        }
    });
    
    updateBuyButton();
}

function updateBuyButton() {
    const buyBtn = document.getElementById('buyBtn');
    const count = selectedAvailable.size;
    
    if (count > 0) {
        buyBtn.textContent = `Buy Selected (${count})`;
        buyBtn.disabled = false;
    } else {
        buyBtn.textContent = 'Buy Selected Numbers';
        buyBtn.disabled = availableNumbers.length === 0;
    }
}

// Purchase Functions
async function buySelectedNumbers() {
    if (selectedAvailable.size === 0) {
        alert('Please select at least one number to purchase.');
        return;
    }
    
    const selectedNumbers = Array.from(selectedAvailable).map(index => availableNumbers[index]);
    
    // Calculate totals
    let totalInitial = 0;
    let totalMonthly = 0;
    
    selectedNumbers.forEach(number => {
        totalInitial += parseFloat(number.initialPrice || 0);
        totalMonthly += parseFloat(number.cost || 0);
    });
    
    // Populate purchase modal
    document.getElementById('purchaseCount').textContent = selectedNumbers.length;
    document.getElementById('purchaseInitialCost').textContent = `€${totalInitial.toFixed(2)}`;
    document.getElementById('purchaseMonthlyCost').textContent = `€${totalMonthly.toFixed(2)}`;
    
    // Populate numbers list
    const numbersList = document.getElementById('purchaseNumbersList');
    numbersList.innerHTML = selectedNumbers.map(number => `
        <tr>
            <td>${number.country}</td>
            <td>${number.msisdn}</td>
            <td>${number.type}</td>
            <td>€${number.initialPrice || '0.00'}</td>
            <td>€${number.cost || '0.00'}</td>
        </tr>
    `).join('');
    
    // Load subaccounts
    await loadSubaccounts();
    
    // Show modal first
    showModal('purchaseModal');
    
    // Use setTimeout to ensure DOM is fully rendered before balance check
    setTimeout(async () => {
        console.log('About to check balance - currentAccountBalance:', currentAccountBalance);
        console.log('Total initial cost:', totalInitial);
        await checkAndShowBalanceWarning(totalInitial, currentAccountBalance);
    }, 100);
}

async function loadSubaccounts() {
    const select = document.getElementById('subaccountSelect');
    const status = document.getElementById('subaccountStatus');
    
    try {
        status.textContent = 'Loading subaccounts...';
        select.innerHTML = '<option value="">Master Account (default)</option>';
        
        const response = await fetch('/api/subaccounts');
        const result = await response.json();
        
        if (result.success) {
            const subaccounts = result.data._embedded?.subaccounts || [];
            
            subaccounts.forEach(subaccount => {
                const option = document.createElement('option');
                option.value = subaccount.api_key;
                option.textContent = `${subaccount.name || 'Unnamed'} (${subaccount.api_key})`;
                select.appendChild(option);
            });
            
            status.textContent = `Found ${subaccounts.length} subaccounts`;
        } else {
            status.textContent = 'Failed to load subaccounts';
        }
    } catch (error) {
        status.textContent = 'Error loading subaccounts';
    }
}

async function confirmPurchase() {
    const selectedNumbers = Array.from(selectedAvailable).map(index => availableNumbers[index]);
    const targetApiKey = document.getElementById('subaccountSelect').value || null;
    
    closeModal('purchaseModal');
    showLoading('Processing purchase...');
    
    try {
        const response = await fetch('/api/numbers/buy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                numbers: selectedNumbers,
                target_api_key: targetApiKey
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            addLogEntry(`Purchase process completed: ${data.successful}/${data.total} successful`, 'info');
            
            showPurchaseResults(data);
            
            // Refresh owned numbers after successful purchases
            if (data.successful > 0) {
                setTimeout(() => refreshNumbers(), 2000);
            }
        } else {
            addLogEntry(`Purchase failed: ${result.error}`, 'error');
            alert(`Purchase failed: ${result.error}`);
        }
    } catch (error) {
        addLogEntry(`Purchase error: ${error.message}`, 'error');
        alert(`Purchase error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function showPurchaseResults(data) {
    document.getElementById('resultsTitle').textContent = 'Purchase Results';
    document.getElementById('resultsSummary').innerHTML = `
        <strong>Purchase Complete:</strong> ${data.successful}/${data.total} successful
        ${data.failed > 0 ? `<br><strong style="color: #e74c3c;">${data.failed} purchases failed</strong>` : ''}
    `;
    
    let details = '';
    if (data.successful > 0) {
        details += '✅ SUCCESSFUL PURCHASES:\n';
        data.results.filter(r => r.success).forEach(r => {
            details += `  • ${r.number} (${r.country})\n`;
        });
        details += '\n';
    }
    
    if (data.failed > 0) {
        details += '❌ FAILED PURCHASES:\n';
        data.results.filter(r => !r.success).forEach(r => {
            details += `  • ${r.number} (${r.country}): ${r.error}\n`;
        });
    }
    
    document.getElementById('resultsDetails').value = details;
    showModal('resultsModal');
}

// Cancellation Functions
async function cancelSelectedNumbers() {
    if (selectedOwned.size === 0) {
        alert('Please select at least one number to cancel.');
        return;
    }
    
    const selectedNumbers = Array.from(selectedOwned).map(index => ownedNumbers[index]);
    
    // Populate cancellation modal
    document.getElementById('cancelCount').textContent = selectedNumbers.length;
    
    const numbersList = document.getElementById('cancelNumbersList');
    numbersList.innerHTML = selectedNumbers.map(number => `
        <tr>
            <td>${number.country}</td>
            <td>${number.msisdn}</td>
            <td>${number.type}</td>
            <td>${(number.features || []).join(', ') || 'N/A'}</td>
        </tr>
    `).join('');
    
    showModal('cancelModal');
}

async function confirmCancellation() {
    if (!confirm('Are you absolutely sure you want to cancel these numbers? This action cannot be undone!')) {
        return;
    }
    
    const selectedNumbers = Array.from(selectedOwned).map(index => ownedNumbers[index]);
    
    closeModal('cancelModal');
    showLoading('Processing cancellation...');
    
    try {
        const response = await fetch('/api/numbers/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                numbers: selectedNumbers
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            addLogEntry(`Cancellation process completed: ${data.successful}/${data.total} successful`, 'info');
            
            showCancellationResults(data);
            
            // Refresh owned numbers after successful cancellations
            if (data.successful > 0) {
                setTimeout(() => refreshNumbers(), 2000);
            }
        } else {
            addLogEntry(`Cancellation failed: ${result.error}`, 'error');
            alert(`Cancellation failed: ${result.error}`);
        }
    } catch (error) {
        addLogEntry(`Cancellation error: ${error.message}`, 'error');
        alert(`Cancellation error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function showCancellationResults(data) {
    document.getElementById('resultsTitle').textContent = 'Cancellation Results';
    document.getElementById('resultsSummary').innerHTML = `
        <strong>Cancellation Complete:</strong> ${data.successful}/${data.total} successful
        ${data.failed > 0 ? `<br><strong style="color: #e74c3c;">${data.failed} cancellations failed</strong>` : ''}
    `;
    
    let details = '';
    if (data.successful > 0) {
        details += '✅ SUCCESSFUL CANCELLATIONS:\n';
        data.results.filter(r => r.success).forEach(r => {
            details += `  • ${r.number} (${r.country})\n`;
        });
        details += '\n';
    }
    
    if (data.failed > 0) {
        details += '❌ FAILED CANCELLATIONS:\n';
        data.results.filter(r => !r.success).forEach(r => {
            details += `  • ${r.number} (${r.country}): ${r.error}\n`;
        });
    }
    
    document.getElementById('resultsDetails').value = details;
    showModal('resultsModal');
}

// Connection Status Check
async function checkConnectionStatus() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const result = await response.json();
            isConnected = result.connected;
            
            if (isConnected) {
                updateStatus('Connected to Vonage account', 'success');
                // Refresh owned numbers if connected
                await refreshOwnedNumbers();
            } else {
                updateStatus('Not connected - please enter credentials', 'info');
            }
            
            updateButtonStates();
        }
    } catch (error) {
        console.log('Could not check connection status:', error.message);
        updateStatus('Enter credentials and click Connect Account', 'info');
    }
}

// Disconnect from account
async function disconnectAccount() {
    try {
        showLoading('Disconnecting...');
        
        const response = await fetch('/api/disconnect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            isConnected = false;
            ownedNumbers = [];
            availableNumbers = [];
            selectedOwned.clear();
            selectedAvailable.clear();
            
            // Clear displays
            updateOwnedNumbersDisplay();
            updateAvailableNumbersDisplay();
            clearAccountDisplay();
            
            updateStatus('Disconnected successfully', 'info');
            updateButtonStates();
            addLogEntry('Disconnected from account', 'info');
        } else {
            updateStatus(`Disconnect failed: ${result.error}`, 'error');
        }
    } catch (error) {
        updateStatus('Disconnect error occurred', 'error');
        addLogEntry(`Disconnect error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Load saved credentials (for backwards compatibility - now just a placeholder)
function loadCredentials(silent = false) {
    if (!silent) {
        updateStatus('Multi-user mode: Please enter your credentials manually', 'info');
    }
}

// Clear saved credentials (for backwards compatibility - now just a placeholder)
function clearCredentials() {
    // Clear the input fields
    document.getElementById('apiKey').value = '';
    document.getElementById('apiSecret').value = '';
    
    updateStatus('Credential fields cleared', 'info');
    addLogEntry('Credential fields cleared', 'info');
}

// Refresh owned numbers
async function refreshOwnedNumbers() {
    if (!isConnected) {
        updateStatus('Not connected to account', 'error');
        return;
    }
    
    try {
        showLoading('Refreshing owned numbers...');
        
        const response = await fetch('/api/numbers/owned');
        const result = await response.json();
        
        if (result.success) {
            ownedNumbers = result.data.numbers || [];
            updateOwnedNumbersDisplay();
            updateStatus(`Refreshed - ${ownedNumbers.length} numbers found`, 'success');
            addLogEntry(`Refreshed owned numbers: ${ownedNumbers.length} found`, 'info');
        } else {
            updateStatus(`Refresh failed: ${result.error}`, 'error');
            addLogEntry(`Failed to refresh numbers: ${result.error}`, 'error');
        }
    } catch (error) {
        updateStatus('Refresh error occurred', 'error');
        addLogEntry(`Refresh error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Button State Management
function updateButtonStates() {
    // Connection-dependent buttons
    const connectionButtons = ['refreshBtn', 'searchBtn'];
    connectionButtons.forEach(btnId => {
        const button = document.getElementById(btnId);
        if (button) {
            button.disabled = !isConnected;
        }
    });
    
    // Update connect/disconnect button
    const connectBtn = document.getElementById('connectBtn');
    if (isConnected) {
        connectBtn.innerHTML = '<i class="fas fa-plug"></i> Disconnect';
        connectBtn.onclick = disconnectAccount;
        connectBtn.className = 'btn btn-warning';
    } else {
        connectBtn.innerHTML = '<i class="fas fa-plug"></i> Connect Account';
        connectBtn.onclick = connectAccount;
        connectBtn.className = 'btn btn-primary';
    }
    
    // Update account info refresh button
    const refreshAccountBtn = document.getElementById('refreshAccountBtn');
    if (refreshAccountBtn) {
        refreshAccountBtn.disabled = !isConnected;
    }
    
    // Update cancel button
    updateCancelButton();
    
    // Update buy button
    updateBuyButton();
}

// Account Information Management
async function loadAccountInfo() {
    if (!isConnected) {
        clearAccountDisplay();
        return;
    }
    
    try {
        const response = await fetch('/api/account/info');
        const result = await response.json();
        
        if (result.success) {
            displayAccountInfo(result.data);
        } else {
            showAccountError(result.error || 'Failed to load account information');
        }
    } catch (error) {
        showAccountError(`Error loading account info: ${error.message}`);
    }
}

function displayAccountInfo(data) {
    // Display account balance
    displayAccountBalance(data.balance, data.balance_error);
    
    // Display subaccounts
    displaySubaccounts(data.subaccounts, data.subaccounts_error);
}

function displayAccountBalance(balance, error) {
    const balanceContainer = document.getElementById('accountBalance');
    if (!balanceContainer) return;
    
    // Store balance globally for purchase validation
    currentAccountBalance = balance;
    
    if (error) {
        currentAccountBalance = null;
        balanceContainer.innerHTML = `
            <div class="balance-placeholder">
                <i class="fas fa-exclamation-triangle"></i> Error: ${error}
            </div>
        `;
        return;
    }
    
    if (balance && balance.value !== undefined) {
        const creditLimitDisplay = balance.credit_limit ? 
            `<div class="credit-limit">Credit Limit: ${balance.credit_limit} ${balance.currency || 'EUR'}</div>` : '';
        
        balanceContainer.innerHTML = `
            <div class="balance-amount">${balance.value}</div>
            <div class="balance-currency">${balance.currency || 'EUR'}</div>
            ${creditLimitDisplay}
        `;
    } else {
        currentAccountBalance = null;
        balanceContainer.innerHTML = `
            <div class="balance-placeholder">
                <i class="fas fa-question-circle"></i> Balance information not available
            </div>
        `;
    }
}

function displaySubaccounts(subaccounts, error) {
    const subaccountsContainer = document.getElementById('subaccountsList');
    if (!subaccountsContainer) return;
    
    if (error) {
        subaccountsContainer.innerHTML = `
            <div class="subaccounts-placeholder">
                <i class="fas fa-exclamation-triangle"></i> Error: ${error}
            </div>
        `;
        return;
    }
    
    if (subaccounts && subaccounts._embedded && subaccounts._embedded.subaccounts) {
        const subaccountList = subaccounts._embedded.subaccounts;
        
        if (subaccountList.length === 0) {
            subaccountsContainer.innerHTML = `
                <div class="subaccounts-placeholder">
                    <i class="fas fa-info-circle"></i> No subaccounts found
                </div>
            `;
            return;
        }
        
        let html = '';
        subaccountList.forEach(subaccount => {
            const creditLimitInfo = subaccount.credit_limit ? 
                `<div class="subaccount-credit-limit">Limit: ${subaccount.credit_limit} ${subaccount.currency || 'EUR'}</div>` : '';
            
            html += `
                <div class="subaccount-item">
                    <div>
                        <div class="subaccount-name">${subaccount.name || 'Unnamed'}</div>
                        <div class="subaccount-key">${subaccount.api_key}</div>
                    </div>
                    <div class="subaccount-info">
                        <div class="subaccount-balance">
                            ${subaccount.balance || '0.00'} ${subaccount.currency || 'EUR'}
                        </div>
                        ${creditLimitInfo}
                    </div>
                </div>
            `;
        });
        
        subaccountsContainer.innerHTML = html;
    } else {
        subaccountsContainer.innerHTML = `
            <div class="subaccounts-placeholder">
                <i class="fas fa-info-circle"></i> No subaccounts available
            </div>
        `;
    }
}

function clearAccountDisplay() {
    const balanceContainer = document.getElementById('accountBalance');
    const subaccountsContainer = document.getElementById('subaccountsList');
    
    if (balanceContainer) {
        balanceContainer.innerHTML = `
            <div class="balance-placeholder">
                <i class="fas fa-plug"></i> Connect to view balance
            </div>
        `;
    }
    
    if (subaccountsContainer) {
        subaccountsContainer.innerHTML = `
            <div class="subaccounts-placeholder">
                <i class="fas fa-plug"></i> Connect to view subaccounts
            </div>
        `;
    }
}

function showAccountError(message) {
    const balanceContainer = document.getElementById('accountBalance');
    const subaccountsContainer = document.getElementById('subaccountsList');
    
    if (balanceContainer) {
        balanceContainer.innerHTML = `
            <div class="balance-placeholder">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
    }
    
    if (subaccountsContainer) {
        subaccountsContainer.innerHTML = `
            <div class="subaccounts-placeholder">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
    }
}

async function refreshAccountInfo() {
    if (!isConnected) {
        updateStatus('Not connected to account', 'error');
        return;
    }
    
    try {
        showLoading('Refreshing account information...');
        await loadAccountInfo();
        addLogEntry('Account information refreshed', 'info');
    } catch (error) {
        addLogEntry(`Failed to refresh account info: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Version and Changelog Management
async function loadVersionInfo() {
    try {
        const response = await fetch('/api/version');
        const versionData = await response.json();
        
        if (versionData.version) {
            // Update version badge
            const versionBadge = document.getElementById('versionBadge');
            if (versionBadge) {
                versionBadge.textContent = `v${versionData.version}`;
            }
            
            // Store changelog data for modal
            window.changelogData = versionData;
            
            console.log(`Vonage Numbers Manager v${versionData.version} loaded`);
        }
    } catch (error) {
        console.log('Could not load version info:', error.message);
    }
}


function displayChangelog(versionData) {
    const changelogContent = document.getElementById('changelogContent');
    if (!changelogContent) return;
    
    let html = `<div class="changelog-header">
        <h4>Vonage Numbers Manager v${versionData.version}</h4>
        <p class="release-date">Released: ${versionData.release_date}</p>
    </div>`;
    
    versionData.changelog.forEach(release => {
        const typeClass = release.type === 'major' ? 'major' : release.type === 'minor' ? 'minor' : 'patch';
        const typeIcon = release.type === 'major' ? '🚀' : release.type === 'minor' ? '✨' : '🐛';
        
        html += `
            <div class="changelog-entry ${typeClass}">
                <div class="changelog-version">
                    <span class="version-number">${typeIcon} v${release.version}</span>
                    <span class="version-date">${release.date}</span>
                </div>
                <h5 class="version-title">${release.title}</h5>
                <ul class="changelog-list">
                    ${release.changes.map(change => `<li>${change}</li>`).join('')}
                </ul>
            </div>
        `;
    });
    
    changelogContent.innerHTML = html;
}

// Modal Management
function showModal(modalId) {
    if (modalId === 'changelogModal') {
        // Load changelog content when modal is opened
        if (window.changelogData && window.changelogData.changelog) {
            displayChangelog(window.changelogData);
        } else {
            // Fallback if version data not loaded
            loadVersionInfo().then(() => {
                if (window.changelogData) {
                    displayChangelog(window.changelogData);
                }
            });
        }
    }
    
    // Show modal
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Balance validation functions
async function checkAndShowBalanceWarning(requiredAmount, accountBalance) {
    const warningElement = document.getElementById('insufficientBalanceWarning');
    const confirmButton = document.querySelector('#purchaseModal .btn-success');
    
    console.log('checkAndShowBalanceWarning called:', {
        requiredAmount,
        accountBalance,
        warningElement: !!warningElement,
        confirmButton: !!confirmButton
    });
    
    if (!warningElement || !confirmButton) {
        console.error('Missing DOM elements for balance validation');
        return;
    }
    
    // Hide warning by default
    warningElement.style.display = 'none';
    confirmButton.disabled = false;
    confirmButton.innerHTML = '<i class="fas fa-check"></i> Confirm Purchase';
    
    // If no account balance is available, try to fetch it
    let balanceToCheck = accountBalance;
    if (!balanceToCheck || balanceToCheck.value === undefined) {
        console.log('No cached balance, fetching fresh balance data...');
        try {
            const response = await fetch('/api/account/info');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data.balance) {
                    balanceToCheck = data.data.balance;
                    currentAccountBalance = balanceToCheck; // Update global cache
                    console.log('Fetched fresh balance:', balanceToCheck);
                }
            }
        } catch (error) {
            console.error('Failed to fetch balance:', error);
        }
    }
    
    if (balanceToCheck && balanceToCheck.value !== undefined) {
        const currentBalance = parseFloat(balanceToCheck.value);
        const currency = balanceToCheck.currency || 'EUR';
        const currencySymbol = currency === 'EUR' ? '€' : currency === 'USD' ? '$' : currency === 'GBP' ? '£' : currency;
        
        console.log('Balance check:', {
            currentBalance,
            requiredAmount,
            insufficient: currentBalance < requiredAmount
        });
        
        if (currentBalance < requiredAmount) {
            const shortage = requiredAmount - currentBalance;
            
            // Update warning content
            document.getElementById('modalCurrentBalance').textContent = `${currencySymbol}${currentBalance.toFixed(2)}`;
            document.getElementById('modalRequiredAmount').textContent = `${currencySymbol}${requiredAmount.toFixed(2)}`;
            document.getElementById('modalShortageAmount').textContent = `${currencySymbol}${shortage.toFixed(2)}`;
            
            // Show warning and disable button
            warningElement.style.display = 'block';
            confirmButton.disabled = true;
            confirmButton.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Insufficient Balance';
            
            console.log('Showing insufficient balance warning - DOM elements updated');
            
            // Log the insufficient balance warning
            addLogEntry(`Insufficient balance: Need ${currencySymbol}${requiredAmount.toFixed(2)}, have ${currencySymbol}${currentBalance.toFixed(2)}`, 'warning');
        } else {
            console.log('Balance is sufficient:', currentBalance, '>=', requiredAmount);
        }
    } else {
        console.log('Still no account balance available for validation after fetch attempt');
        // Show a generic warning that balance couldn't be verified
        warningElement.innerHTML = `
            <div class="warning-box insufficient-balance">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Unable to Verify Balance</strong>
                <p>Could not verify your account balance. Please ensure you have sufficient funds before proceeding.</p>
            </div>
        `;
        warningElement.style.display = 'block';
    }
}

function openVonageTopUp() {
    // Open Vonage dashboard in a new tab for account top-up
    window.open('https://dashboard.nexmo.com/billing', '_blank');
    
    // Log the action
    addLogEntry('Opened Vonage dashboard for account top-up', 'info');
}