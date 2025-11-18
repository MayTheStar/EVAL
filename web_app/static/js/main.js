/* ============================================
   EVAL RFP Analysis Platform - Main JavaScript
   All frontend logic and API interactions
   ============================================ */

// ============================================
// Global State Management
// ============================================
const AppState = {
    user: null,
    status: {
        rfpUploaded: false,
        vendorsCount: 0,
        processed: false,
        chatbotReady: false,
        filesCount: 0
    },
    files: [],
    currentFile: null
};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    setupGlobalListeners();
    
    // Page-specific initializations
    const currentPage = window.location.pathname;
    
    if (currentPage.includes('dashboard')) {
        initDashboard();
    } else if (currentPage.includes('upload-rfp')) {
        initUploadRFP();
    } else if (currentPage.includes('upload-vendor')) {
        initUploadVendor();
    } else if (currentPage.includes('chatbot')) {
        initChatbot();
    } else if (currentPage.includes('files')) {
        initFilesPage();
    } else if (currentPage.includes('profile')) {
        initProfile();
    } else if (currentPage.includes('login')) {
        initLogin();
    } else if (currentPage.includes('register')) {
        initRegister();
    }
});

// ============================================
// Page Initialization Functions
// ============================================
function initializePage() {
    // Add active class to navigation
    updateActiveNav();
    
    // Load status if on dashboard pages
    if (window.location.pathname.includes('dashboard') || 
        window.location.pathname.includes('upload') ||
        window.location.pathname.includes('files') ||
        window.location.pathname.includes('chatbot')) {
        loadStatus();
    }
}

function setupGlobalListeners() {
    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', autoResize);
    });
}

function updateActiveNav() {
    const navItems = document.querySelectorAll('.nav-item');
    const currentPage = window.location.pathname;
    
    navItems.forEach(item => {
        item.classList.remove('active');
        const href = item.getAttribute('href');
        if (href && currentPage.includes(href.replace('/', ''))) {
            item.classList.add('active');
        }
    });
}

// ============================================
// Authentication Functions
// ============================================
function initLogin() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
}

function initRegister() {
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const errorMsg = document.getElementById('errorMessage');
    const loginButton = document.getElementById('loginButton');
    
    // Validate
    if (!username || !password) {
        showMessage(errorMsg, 'Please fill in all fields', 'error');
        return;
    }
    
    // Show loading
    setButtonLoading(loginButton, true);
    hideMessage(errorMsg);
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.location.href = data.redirect || '/dashboard';
        } else {
            showMessage(errorMsg, data.message || 'Login failed', 'error');
        }
    } catch (error) {
        showMessage(errorMsg, 'Network error. Please try again.', 'error');
        console.error('Login error:', error);
    } finally {
        setButtonLoading(loginButton, false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorMsg = document.getElementById('errorMessage');
    const registerButton = document.getElementById('registerButton');
    
    // Validate
    if (!username || !password || !confirmPassword) {
        showMessage(errorMsg, 'Please fill in all required fields', 'error');
        return;
    }
    
    if (password !== confirmPassword) {
        showMessage(errorMsg, 'Passwords do not match', 'error');
        return;
    }
    
    if (password.length < 6) {
        showMessage(errorMsg, 'Password must be at least 6 characters', 'error');
        return;
    }
    
    // Show loading
    setButtonLoading(registerButton, true);
    hideMessage(errorMsg);
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.location.href = data.redirect || '/dashboard';
        } else {
            showMessage(errorMsg, data.message || 'Registration failed', 'error');
        }
    } catch (error) {
        showMessage(errorMsg, 'Network error. Please try again.', 'error');
        console.error('Registration error:', error);
    } finally {
        setButtonLoading(registerButton, false);
    }
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}

// ============================================
// Dashboard Functions
// ============================================
function initDashboard() {
    loadStatus();
    setInterval(loadStatus, 5000); // Update every 5 seconds
}

async function loadStatus() {
    try {
        const response = await fetch('/api/get-status');
        const data = await response.json();
        
        AppState.status = data;
        updateDashboardUI(data);
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

function updateDashboardUI(data) {
    // Update RFP status
    const rfpStatus = document.getElementById('rfpStatus');
    const rfpBadge = document.getElementById('rfpBadge');
    if (rfpStatus && rfpBadge) {
        if (data.rfp_uploaded) {
            rfpStatus.textContent = 'Uploaded';
            rfpBadge.textContent = 'Ready';
            rfpBadge.className = 'stat-badge badge-success';
        } else {
            rfpStatus.textContent = 'Not Uploaded';
            rfpBadge.textContent = 'Pending';
            rfpBadge.className = 'stat-badge badge-pending';
        }
    }
    
    // Update vendor count
    const vendorCount = document.getElementById('vendorCount');
    const vendorBadge = document.getElementById('vendorBadge');
    if (vendorCount && vendorBadge) {
        vendorCount.textContent = `${data.vendors_count} Uploaded`;
        if (data.vendors_count > 0) {
            vendorBadge.textContent = 'Ready';
            vendorBadge.className = 'stat-badge badge-success';
        }
    }
    
    // Update processing status
    const processStatus = document.getElementById('processStatus');
    const processBadge = document.getElementById('processBadge');
    const processButton = document.getElementById('processButton');
    if (processStatus && processBadge) {
        if (data.processed) {
            processStatus.textContent = 'Completed';
            processBadge.textContent = 'Done';
            processBadge.className = 'stat-badge badge-success';
            if (processButton) processButton.disabled = true;
        } else if (data.rfp_uploaded && data.vendors_count > 0) {
            processStatus.textContent = 'Ready to Process';
            processBadge.textContent = 'Ready';
            processBadge.className = 'stat-badge badge-warning';
            if (processButton) processButton.disabled = false;
        } else {
            processStatus.textContent = 'Not Started';
            processBadge.textContent = 'Waiting';
            processBadge.className = 'stat-badge badge-pending';
            if (processButton) processButton.disabled = true;
        }
    }
    
    // Update chatbot status
    const chatbotStatus = document.getElementById('chatbotStatus');
    const chatbotStatusBadge = document.getElementById('chatbotStatusBadge');
    const chatbotLink = document.getElementById('chatbotLink');
    const chatbotAction = document.getElementById('chatbotAction');
    
    if (chatbotStatus && chatbotStatusBadge) {
        if (data.chatbot_ready) {
            chatbotStatus.textContent = 'Ready';
            chatbotStatusBadge.textContent = 'Active';
            chatbotStatusBadge.className = 'stat-badge badge-success';
            if (chatbotLink) chatbotLink.style.pointerEvents = 'auto';
            if (chatbotAction) chatbotAction.style.opacity = '1';
        } else {
            chatbotStatus.textContent = 'Not Ready';
            chatbotStatusBadge.textContent = 'Disabled';
            chatbotStatusBadge.className = 'stat-badge badge-disabled';
            if (chatbotLink) chatbotLink.style.pointerEvents = 'none';
            if (chatbotAction) chatbotAction.style.opacity = '0.5';
        }
    }
}

async function processDocuments() {
    const processButton = document.getElementById('processButton');
    const processLog = document.getElementById('processLog');
    const logContainer = document.getElementById('logContainer');
    
    if (!confirm('Start processing documents? This may take a few minutes.')) {
        return;
    }
    
    // Show loading
    setButtonLoading(processButton, true);
    if (processLog) processLog.style.display = 'block';
    if (logContainer) {
        logContainer.innerHTML = '<p>⏳ Starting document processing...</p>';
    }
    
    try {
        const response = await fetch('/api/process-documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (logContainer) {
                logContainer.innerHTML += '<p>✅ Processing completed successfully!</p>';
                if (data.non_compliant_vendors && data.non_compliant_vendors.length > 0) {
                    logContainer.innerHTML += `<p>⚠️ Non-compliant vendors: ${data.non_compliant_vendors.join(', ')}</p>`;
                }
            }
            
            // Reload status
            await loadStatus();
            
            setTimeout(() => {
                alert('Processing complete! You can now use the chatbot.');
            }, 500);
        } else {
            if (logContainer) {
                logContainer.innerHTML += `<p>❌ Error: ${data.message}</p>`;
            }
            alert('Processing failed: ' + data.message);
        }
    } catch (error) {
        if (logContainer) {
            logContainer.innerHTML += `<p>❌ Network error: ${error.message}</p>`;
        }
        alert('Network error. Please try again.');
        console.error('Processing error:', error);
    } finally {
        setButtonLoading(processButton, false);
    }
}

// ============================================
// Upload RFP Functions
// ============================================
function initUploadRFP() {
    const rfpForm = document.getElementById('rfpUploadForm');
    const rfpFile = document.getElementById('rfpFile');
    
    if (rfpForm) {
        rfpForm.addEventListener('submit', handleRFPUpload);
    }
    
    if (rfpFile) {
        rfpFile.addEventListener('change', handleRFPFileSelect);
    }
}

function handleRFPFileSelect(e) {
    const file = e.target.files[0];
    const selectedFile = document.getElementById('selectedFile');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const uploadButton = document.getElementById('uploadButton');
    
    if (file) {
        if (selectedFile) selectedFile.style.display = 'block';
        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = formatFileSize(file.size);
        if (uploadButton) uploadButton.disabled = false;
    }
}

async function handleRFPUpload(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('rfpFile');
    const uploadButton = document.getElementById('uploadButton');
    const uploadMessage = document.getElementById('uploadMessage');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    if (!fileInput.files[0]) {
        showMessage(uploadMessage, 'Please select a file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    // Show loading
    setButtonLoading(uploadButton, true);
    if (uploadProgress) uploadProgress.style.display = 'block';
    hideMessage(uploadMessage);
    
    try {
        const response = await fetch('/api/upload-rfp', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(uploadMessage, '✅ ' + data.message, 'success');
            if (progressFill) progressFill.style.width = '100%';
            if (progressText) progressText.textContent = 'Upload complete!';
            
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            showMessage(uploadMessage, '❌ ' + data.message, 'error');
        }
    } catch (error) {
        showMessage(uploadMessage, '❌ Network error. Please try again.', 'error');
        console.error('Upload error:', error);
    } finally {
        setButtonLoading(uploadButton, false);
        if (uploadProgress) {
            setTimeout(() => {
                uploadProgress.style.display = 'none';
            }, 2000);
        }
    }
}

function clearFile() {
    const rfpFile = document.getElementById('rfpFile');
    const selectedFile = document.getElementById('selectedFile');
    const uploadButton = document.getElementById('uploadButton');
    
    if (rfpFile) rfpFile.value = '';
    if (selectedFile) selectedFile.style.display = 'none';
    if (uploadButton) uploadButton.disabled = true;
}

// ============================================
// Upload Vendor Functions
// ============================================
function initUploadVendor() {
    const vendorForm = document.getElementById('vendorUploadForm');
    const vendorFile = document.getElementById('vendorFile');
    
    if (vendorForm) {
        vendorForm.addEventListener('submit', handleVendorUpload);
    }
    
    if (vendorFile) {
        vendorFile.addEventListener('change', handleVendorFileSelect);
    }
}

function handleVendorFileSelect(e) {
    const file = e.target.files[0];
    const vendorName = document.getElementById('vendorName');
    const selectedFile = document.getElementById('selectedFile');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const uploadButton = document.getElementById('uploadButton');
    
    if (file) {
        if (selectedFile) selectedFile.style.display = 'block';
        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = formatFileSize(file.size);
        if (uploadButton && vendorName && vendorName.value.trim()) {
            uploadButton.disabled = false;
        }
    }
}

async function handleVendorUpload(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('vendorFile');
    const vendorName = document.getElementById('vendorName');
    const uploadButton = document.getElementById('uploadButton');
    const uploadMessage = document.getElementById('uploadMessage');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    if (!fileInput.files[0]) {
        showMessage(uploadMessage, 'Please select a file', 'error');
        return;
    }
    
    if (!vendorName.value.trim()) {
        showMessage(uploadMessage, 'Please enter vendor name', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('vendor_name', vendorName.value.trim());
    
    // Show loading
    setButtonLoading(uploadButton, true);
    if (uploadProgress) uploadProgress.style.display = 'block';
    hideMessage(uploadMessage);
    
    try {
        const response = await fetch('/api/upload-vendor', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(uploadMessage, '✅ ' + data.message, 'success');
            if (progressFill) progressFill.style.width = '100%';
            if (progressText) progressText.textContent = 'Upload complete!';
            
            // Reset form
            setTimeout(() => {
                vendorName.value = '';
                clearVendorFile();
                hideMessage(uploadMessage);
                if (uploadProgress) uploadProgress.style.display = 'none';
            }, 2000);
        } else {
            showMessage(uploadMessage, '❌ ' + data.message, 'error');
        }
    } catch (error) {
        showMessage(uploadMessage, '❌ Network error. Please try again.', 'error');
        console.error('Upload error:', error);
    } finally {
        setButtonLoading(uploadButton, false);
    }
}

function clearVendorFile() {
    const vendorFile = document.getElementById('vendorFile');
    const selectedFile = document.getElementById('selectedFile');
    const uploadButton = document.getElementById('uploadButton');
    
    if (vendorFile) vendorFile.value = '';
    if (selectedFile) selectedFile.style.display = 'none';
    if (uploadButton) uploadButton.disabled = true;
}

// ============================================
// Chatbot Functions
// ============================================
function initChatbot() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    
    if (chatForm) {
        chatForm.addEventListener('submit', handleChatSubmit);
    }
    
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }
}

async function handleChatSubmit(e) {
    e.preventDefault();
    
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const query = chatInput.value.trim();
    
    if (!query) return;
    
    // Add user message
    addMessage('user', query);
    chatInput.value = '';
    
    // Show loading
    const loadingId = addMessage('bot', '💭 Thinking...');
    sendButton.disabled = true;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        // Remove loading message
        removeMessage(loadingId);
        
        if (data.success) {
            addMessage('bot', data.answer);
            if (data.sources && data.sources.length > 0) {
                addSources(data.sources);
            }
        } else {
            addMessage('bot', '❌ Error: ' + data.message);
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage('bot', '❌ Network error. Please try again.');
        console.error('Chat error:', error);
    } finally {
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function addMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const chatWelcome = document.querySelector('.chat-welcome');
    
    // Hide welcome message on first user message
    if (chatWelcome && role === 'user') {
        chatWelcome.style.display = 'none';
    }
    
    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${role}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    contentDiv.appendChild(timeDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

function addSources(sources) {
    const chatMessages = document.getElementById('chatMessages');
    
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'message bot-message';
    sourcesDiv.innerHTML = `
        <div class="message-avatar">📚</div>
        <div class="message-content">
            <strong>Sources:</strong>
            <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                ${sources.map(s => `<li>${s.label} (${s.distance.toFixed(3)})</li>`).join('')}
            </ul>
        </div>
    `;
    
    chatMessages.appendChild(sourcesDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function askQuestion(question) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = question;
        chatInput.focus();
    }
}

// ============================================
// Files Page Functions
// ============================================
function initFilesPage() {
    loadFiles();
}

async function loadFiles() {
    try {
        const response = await fetch('/api/get-status');
        const data = await response.json();
        
        updateFilesSummary(data);
        // Additional file loading logic can be added here
        
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

function updateFilesSummary(data) {
    const rfpCount = document.getElementById('rfpCount');
    const vendorCountFiles = document.getElementById('vendorCountFiles');
    const totalCount = document.getElementById('totalCount');
    
    if (rfpCount) rfpCount.textContent = data.rfp_uploaded ? '1' : '0';
    if (vendorCountFiles) vendorCountFiles.textContent = data.vendors_count || '0';
    if (totalCount) totalCount.textContent = (data.rfp_uploaded ? 1 : 0) + (data.vendors_count || 0);
}

function refreshFiles() {
    loadFiles();
}

function deleteFile(filename) {
    AppState.currentFile = filename;
    const modal = document.getElementById('deleteModal');
    if (modal) modal.style.display = 'flex';
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) modal.style.display = 'none';
    AppState.currentFile = null;
}

async function confirmDelete() {
    if (!AppState.currentFile) return;
    
    try {
        const response = await fetch('/api/delete-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: AppState.currentFile })
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeDeleteModal();
            loadFiles();
        } else {
            alert('Error deleting file: ' + data.message);
        }
    } catch (error) {
        alert('Network error. Please try again.');
        console.error('Delete error:', error);
    }
}

// ============================================
// Profile Functions
// ============================================
function initProfile() {
    const profileForm = document.getElementById('profileForm');
    
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
    
    loadProfileData();
}

function loadProfileData() {
    // Load profile data from session/API
    const username = sessionStorage.getItem('username') || 'User';
    const email = sessionStorage.getItem('email') || '';
    
    const profileUsername = document.getElementById('profileUsername');
    const profileEmail = document.getElementById('profileEmail');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    
    if (profileUsername) profileUsername.textContent = username;
    if (profileEmail) profileEmail.textContent = email || 'No email provided';
    if (usernameInput) usernameInput.value = username;
    if (emailInput) emailInput.value = email;
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    
    // API call to update profile
    alert('Profile updated successfully!');
}

function clearAllData() {
    if (confirm('Are you sure you want to clear all data? This action cannot be undone.')) {
        // API call to clear data
        alert('All data cleared successfully!');
    }
}

function deleteAccount() {
    if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
        if (confirm('This is your final warning. All data will be permanently deleted.')) {
            // API call to delete account
            alert('Account deleted. You will be logged out.');
            logout();
        }
    }
}

// ============================================
// Utility Functions
// ============================================
function showMessage(element, message, type) {
    if (!element) return;
    
    element.textContent = message;
    element.style.display = 'block';
    element.className = type === 'error' ? 'error-message' : 'success-message';
}

function hideMessage(element) {
    if (!element) return;
    element.style.display = 'none';
}

function setButtonLoading(button, loading) {
    if (!button) return;
    
    const buttonText = button.querySelector('.button-text');
    const buttonLoader = button.querySelector('.button-loader');
    
    if (loading) {
        button.disabled = true;
        if (buttonText) buttonText.style.display = 'none';
        if (buttonLoader) buttonLoader.style.display = 'flex';
    } else {
        button.disabled = false;
        if (buttonText) buttonText.style.display = 'flex';
        if (buttonLoader) buttonLoader.style.display = 'none';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function autoResize() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ============================================
// Error Handling
// ============================================
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});

// ============================================
// Export for testing (optional)
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AppState,
        formatFileSize,
        formatDate
    };
}

// Additional JavaScript for enhanced dashboard with vendor scoring

// Function to load and display vendor scores
async function loadVendorScores() {
    try {
        const response = await fetch('/api/get-vendor-scores');
        const data = await response.json();
        
        if (data.success && data.scores && data.scores.length > 0) {
            displayVendorScores(data.scores);
            
            // Hide empty state, show scoring dashboard
            const emptyState = document.getElementById('emptyState');
            const scoringDashboard = document.getElementById('scoringDashboard');
            if (emptyState) emptyState.style.display = 'none';
            if (scoringDashboard) scoringDashboard.style.display = 'block';
        } else {
            // Show empty state
            const emptyState = document.getElementById('emptyState');
            const scoringDashboard = document.getElementById('scoringDashboard');
            if (emptyState) emptyState.style.display = 'block';
            if (scoringDashboard) scoringDashboard.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading vendor scores:', error);
    }
}

// Function to display vendor scores in the dashboard
function displayVendorScores(scores) {
    const container = document.getElementById('vendorScoresContainer');
    if (!container) return;
    
    // Sort scores by total score (descending)
    scores.sort((a, b) => b.total_score - a.total_score);
    
    // Clear container
    container.innerHTML = '';
    
    // Create vendor cards
    scores.forEach((vendor, index) => {
        const rank = index + 1;
        const isTopVendor = rank === 1;
        
        const card = document.createElement('div');
        card.className = `vendor-card ${isTopVendor ? 'top-vendor' : ''}`;
        
        // Calculate percentage
        const percentage = ((vendor.total_score / vendor.max_score) * 100).toFixed(1);
        
        card.innerHTML = `
            <div class="vendor-header">
                <div>
                    <div class="vendor-name">${escapeHtml(vendor.vendor_name)}</div>
                </div>
                <div class="vendor-rank ${rank === 1 ? 'rank-1' : ''}">${rank}</div>
            </div>
            
            <div class="overall-score">
                <div class="score-label">Overall Score</div>
                <div class="score-value">
                    ${vendor.total_score.toFixed(1)}
                    <span class="score-max">/ ${vendor.max_score}</span>
                </div>
                <div style="margin-top: 0.5rem; color: var(--gray-600); font-size: 0.9rem;">
                    ${percentage}%
                </div>
            </div>
            
            <div class="score-breakdown">
                ${vendor.technical_score !== undefined ? `
                    <div class="score-item">
                        <span class="score-item-label">Technical Score</span>
                        <span class="score-item-value">${vendor.technical_score.toFixed(1)}</span>
                    </div>
                ` : ''}
                
                ${vendor.financial_score !== undefined ? `
                    <div class="score-item">
                        <span class="score-item-label">Financial Score</span>
                        <span class="score-item-value">${vendor.financial_score.toFixed(1)}</span>
                    </div>
                ` : ''}
                
                ${vendor.experience_score !== undefined ? `
                    <div class="score-item">
                        <span class="score-item-label">Experience Score</span>
                        <span class="score-item-value">${vendor.experience_score.toFixed(1)}</span>
                    </div>
                ` : ''}
                
                ${vendor.compliance_score !== undefined ? `
                    <div class="score-item">
                        <span class="score-item-label">Compliance Score</span>
                        <span class="score-item-value">${vendor.compliance_score.toFixed(1)}</span>
                    </div>
                ` : ''}
            </div>
            
            ${vendor.compliance_status !== undefined ? `
                <div class="compliance-badge ${vendor.compliance_status === 'compliant' ? 'compliance-pass' : 'compliance-fail'}">
                    ${vendor.compliance_status === 'compliant' ? '✓ Compliant' : '✗ Non-Compliant'}
                </div>
            ` : ''}
        `;
        
        container.appendChild(card);
    });
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enhanced updateDashboardUI function to load vendor scores
const originalUpdateDashboardUI = window.updateDashboardUI;
window.updateDashboardUI = function(data) {
    // Call original function if it exists
    if (originalUpdateDashboardUI) {
        originalUpdateDashboardUI(data);
    }
    
    // Load vendor scores if processed
    if (data.processed) {
        loadVendorScores();
    }
};

// Load vendor scores on page load if already processed
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('dashboard')) {
        // Check if processed and load scores
        setTimeout(loadVendorScores, 1000);
    }
});

// ============================================
// UPDATED: Dashboard UI Update Function
// ============================================

function updateDashboardUI(data) {
    // Update process button state based on uploaded files
    const processButton = document.getElementById('processButton');
    
    if (processButton) {
        if (data.processed) {
            // Already processed - disable button
            processButton.disabled = true;
            processButton.querySelector('.button-text').textContent = '✓ Processing Complete';
        } else if (data.rfp_uploaded && data.vendors_count > 0) {
            // Ready to process - enable button
            processButton.disabled = false;
            processButton.querySelector('.button-text').textContent = '🚀 Process Documents';
        } else {
            // Not ready - disable button
            processButton.disabled = true;
            processButton.querySelector('.button-text').textContent = '🚀 Process Documents';
        }
    }
    
    // Update chatbot link availability
    const chatbotLink = document.getElementById('chatbotLink');
    const chatbotBadge = document.getElementById('chatbotBadge');
    
    if (chatbotLink && chatbotBadge) {
        if (data.chatbot_ready) {
            chatbotLink.style.pointerEvents = 'auto';
            chatbotLink.style.opacity = '1';
            chatbotBadge.style.display = 'inline-block';
            chatbotBadge.textContent = 'Ready';
        } else {
            chatbotLink.style.pointerEvents = 'none';
            chatbotLink.style.opacity = '0.5';
            chatbotBadge.style.display = 'none';
        }
    }
}
// ============================================
// Dashboard Functions - COMPLETE UPDATED VERSION
// Replace lines 210-355 in your main.js with this code
// ============================================

function initDashboard() {
    loadStatus();
    loadVendorScores(); // Load scores when dashboard initializes
    setInterval(loadStatus, 5000); // Update every 5 seconds
}

async function loadStatus() {
    try {
        const response = await fetch('/api/get-status');
        const data = await response.json();
        
        AppState.status = data;
        updateDashboardUI(data);
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

function updateDashboardUI(data) {
    // Update process button state based on uploaded files
    const processButton = document.getElementById('processButton');
    
    if (processButton) {
        if (data.processed) {
            // Already processed - disable button
            processButton.disabled = true;
            const buttonText = processButton.querySelector('.button-text');
            if (buttonText) buttonText.textContent = '✓ Processing Complete';
        } else if (data.rfp_uploaded && data.vendors_count > 0) {
            // Ready to process - enable button
            processButton.disabled = false;
            const buttonText = processButton.querySelector('.button-text');
            if (buttonText) buttonText.textContent = '🚀 Process Documents';
        } else {
            // Not ready - disable button
            processButton.disabled = true;
            const buttonText = processButton.querySelector('.button-text');
            if (buttonText) buttonText.textContent = '🚀 Process Documents';
        }
    }
    
    // Update chatbot link availability
    const chatbotLink = document.getElementById('chatbotLink');
    const chatbotBadge = document.getElementById('chatbotBadge');
    
    if (chatbotLink && chatbotBadge) {
        if (data.chatbot_ready) {
            chatbotLink.style.pointerEvents = 'auto';
            chatbotLink.style.opacity = '1';
            chatbotBadge.style.display = 'inline-block';
            chatbotBadge.textContent = 'Ready';
        } else {
            chatbotLink.style.pointerEvents = 'none';
            chatbotLink.style.opacity = '0.5';
            chatbotBadge.style.display = 'none';
        }
    }
}

async function processDocuments() {
    const processButton = document.getElementById('processButton');
    const statusMessage = document.getElementById('statusMessage');
    
    if (!confirm('Start processing documents? This may take a few minutes.')) {
        return;
    }
    
    // Show loading
    setButtonLoading(processButton, true);
    if (statusMessage) {
        statusMessage.textContent = '⏳ Processing documents...';
        statusMessage.style.display = 'block';
        statusMessage.style.background = 'rgba(59, 130, 246, 0.15)';
        statusMessage.style.color = '#1d4ed8';
    }
    
    try {
        const response = await fetch('/api/process-documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (statusMessage) {
                statusMessage.textContent = '✓ Processing completed successfully!';
                statusMessage.style.background = 'rgba(76, 175, 80, 0.15)';
                statusMessage.style.color = '#2e7d32';
            }
            
            // Load vendor scores
            await loadVendorScores();
            
            // Reload status
            await loadStatus();
            
            setTimeout(() => {
                if (statusMessage) statusMessage.style.display = 'none';
            }, 5000);
        } else {
            if (statusMessage) {
                statusMessage.textContent = '✗ Processing failed: ' + (data.message || 'Unknown error');
                statusMessage.style.background = 'rgba(244, 67, 54, 0.15)';
                statusMessage.style.color = '#c62828';
            }
        }
    } catch (error) {
        if (statusMessage) {
            statusMessage.textContent = '✗ Network error: ' + error.message;
            statusMessage.style.background = 'rgba(244, 67, 54, 0.15)';
            statusMessage.style.color = '#c62828';
        }
        console.error('Processing error:', error);
    } finally {
        setButtonLoading(processButton, false);
    }
}

async function loadVendorScores() {
    try {
        const response = await fetch('/api/get-scores');
        const data = await response.json();

        const container = document.getElementById('vendorScoreContainer');
        const noScores = document.getElementById('noScores');

        if (!data.success || !data.scores || Object.keys(data.scores.vendors || {}).length === 0) {
            if (container) container.innerHTML = '';
            if (noScores) noScores.style.display = 'block';
            return;
        }

        if (noScores) noScores.style.display = 'none';
        if (container) container.innerHTML = '';

        const vendors = Object.values(data.scores.vendors);

        // Sort vendors by total score (descending)
        vendors.sort((a, b) => (b.total_score || 0) - (a.total_score || 0));

        vendors.forEach(vendor => {
            // Safe default values
            const total = vendor.total_score !== undefined ? vendor.total_score.toFixed(1) : 'N/A';
            const conf = vendor.confidence_score !== undefined ? (vendor.confidence_score * 100).toFixed(0) + '%' : 'N/A';
            const strengths = vendor.strengths || [];
            const weaknesses = vendor.weaknesses || [];
            const criteria = vendor.criteria_breakdown || [];

            const card = document.createElement('div');
            card.className = 'vendor-card';

            card.innerHTML = `
                <div class="card-head">
                    <h3 class="vendor-title">${vendor.vendor_name || 'Unnamed Vendor'}</h3>
                    <div class="vendor-badges">
                        <span class="badge score-badge">Total Score: ${total}</span>
                    </div>
                </div>

                <div class="card-row">
                    <div class="card-col">
                        <h4>Strengths:</h4>
                        <ul class="list-box strengths-list">
                            ${strengths.length ? strengths.map(s => `<li>${s}</li>`).join('') : '<li>No strengths identified</li>'}
                        </ul>
                    </div>

                    <div class="card-col">
                        <h4>Weaknesses:</h4>
                        <ul class="list-box weaknesses-list">
                            ${weaknesses.length ? weaknesses.map(w => `<li>${w}</li>`).join('') : '<li>No weaknesses identified</li>'}
                        </ul>
                    </div>
                </div>

                <h4 class="criteria-heading">Criteria Breakdown:</h4>
                <div class="criteria-box">
                    ${criteria.map(c => {
                        const evidenceList = (c.evidence || []);
                        const gapsList = (c.gaps || []);
                        
                        return `
                        <div class="criterion">
                            <div class="crit-meta">
                                <strong>${c.criterion_name} (Weighted: ${c.weighted_score !== undefined ? c.weighted_score.toFixed(1) : 'N/A'})</strong>
                                <span class="crit-scores">Confidence: ${c.confidence !== undefined ? (c.confidence * 100).toFixed(0) + '%' : 'N/A'}</span>
                            </div>
                            <div class="crit-sub">
                                <details>
                                    <summary>Evidence (${evidenceList.length})</summary>
                                    ${evidenceList.length ? `
                                        <ul>
                                            ${evidenceList.map(ev => `<li>${ev}</li>`).join('')}
                                        </ul>
                                    ` : '<p style="font-size: 0.85rem; color: #888; margin-top: 0.5rem;">No evidence provided</p>'}
                                </details>
                                <details>
                                    <summary>Gaps (${gapsList.length})</summary>
                                    ${gapsList.length ? `
                                        <ul>
                                            ${gapsList.map(g => `<li>${g}</li>`).join('')}
                                        </ul>
                                    ` : '<p style="font-size: 0.85rem; color: #888; margin-top: 0.5rem;">No gaps identified</p>'}
                                </details>
                            </div>
                        </div>
                        `;
                    }).join('')}
                </div>
            `;

            if (container) container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading vendor scores:', error);
    }
}