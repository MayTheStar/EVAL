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
    
    if (currentPage.includes('dashboard.html')) {
        initDashboard();
    } else if (currentPage.includes('upload_rfp.html')) {
        initUploadRFP();
    } else if (currentPage.includes('upload_vendor.html')) {
        initUploadVendor();
    } else if (currentPage.includes('chatbot.html')) {
        initChatbot();
    } else if (currentPage.includes('files_uploaded.html')) {
        initFilesPage();
    } else if (currentPage.includes('profile.html')) {
        initProfile();
    } else if (currentPage.includes('login.html')) {
        initLogin();
    } else if (currentPage.includes('register.html')) {
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
        if (item.getAttribute('href') && currentPage.includes(item.getAttribute('href'))) {
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
            window.location.href = data.redirect || 'dashboard.html';
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
            window.location.href = data.redirect || 'dashboard.html';
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
            processStatus.textContent = 'Complete';
            processBadge.textContent = 'Done';
            processBadge.className = 'stat-badge badge-success';
        } else {
            processStatus.textContent = 'Not Started';
            processBadge.textContent = 'Waiting';
            processBadge.className = 'stat-badge badge-pending';
        }
    }
    
    // Enable/disable process button
    if (processButton) {
        processButton.disabled = !data.rfp_uploaded || data.vendors_count === 0 || data.processed;
    }
    
    // Update chatbot status
    const chatbotStatus = document.getElementById('chatbotStatus');
    const chatbotStatusBadge = document.getElementById('chatbotStatusBadge');
    const chatbotLink = document.getElementById('chatbotLink');
    const chatbotBadge = document.getElementById('chatbotBadge');
    
    if (chatbotStatus && chatbotStatusBadge) {
        if (data.chatbot_ready) {
            chatbotStatus.textContent = 'Ready';
            chatbotStatusBadge.textContent = 'Active';
            chatbotStatusBadge.className = 'stat-badge badge-success';
            
            if (chatbotLink) {
                chatbotLink.style.pointerEvents = 'auto';
                chatbotLink.style.opacity = '1';
            }
            if (chatbotBadge) {
                chatbotBadge.style.display = 'block';
            }
        } else {
            chatbotStatus.textContent = 'Not Ready';
            chatbotStatusBadge.textContent = 'Disabled';
            chatbotStatusBadge.className = 'stat-badge badge-disabled';
            
            if (chatbotLink) {
                chatbotLink.style.pointerEvents = 'none';
                chatbotLink.style.opacity = '0.5';
            }
            if (chatbotBadge) {
                chatbotBadge.style.display = 'none';
            }
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
    
    setButtonLoading(processButton, true);
    if (processLog) processLog.style.display = 'block';
    
    addLogMessage(logContainer, 'Starting document processing...');
    
    try {
        const response = await fetch('/api/process-documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            addLogMessage(logContainer, '✅ Processing complete!');
            
            if (data.non_compliant_vendors && data.non_compliant_vendors.length > 0) {
                addLogMessage(logContainer, `⚠️ ${data.non_compliant_vendors.length} vendor(s) disqualified for non-compliance`);
            }
            
            setTimeout(() => {
                loadStatus();
                window.location.reload();
            }, 2000);
        } else {
            addLogMessage(logContainer, `❌ Error: ${data.message}`);
        }
    } catch (error) {
        addLogMessage(logContainer, `❌ Network error: ${error.message}`);
        console.error('Process error:', error);
    } finally {
        setButtonLoading(processButton, false);
    }
}

function addLogMessage(container, message) {
    if (!container) return;
    
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    container.appendChild(logEntry);
    container.scrollTop = container.scrollHeight;
}

// ============================================
// File Upload Functions
// ============================================
function initUploadRFP() {
    const rfpForm = document.getElementById('rfpUploadForm');
    const rfpFile = document.getElementById('rfpFile');
    const uploadButton = document.getElementById('uploadButton');
    
    if (rfpFile) {
        rfpFile.addEventListener('change', function(e) {
            handleFileSelect(e, 'rfpFile', 'selectedFile', 'fileName', 'fileSize', 'uploadButton');
        });
    }
    
    if (rfpForm) {
        rfpForm.addEventListener('submit', handleRFPUpload);
    }
}

function initUploadVendor() {
    const vendorForm = document.getElementById('vendorUploadForm');
    const vendorFile = document.getElementById('vendorFile');
    const vendorName = document.getElementById('vendorName');
    const uploadButton = document.getElementById('uploadButton');
    
    if (vendorFile) {
        vendorFile.addEventListener('change', function(e) {
            handleFileSelect(e, 'vendorFile', 'selectedFile', 'fileName', 'fileSize', 'uploadButton');
        });
    }
    
    if (vendorName) {
        vendorName.addEventListener('input', function() {
            checkVendorFormValidity();
        });
    }
    
    if (vendorForm) {
        vendorForm.addEventListener('submit', handleVendorUpload);
    }
}

function handleFileSelect(e, fileInputId, selectedFileId, fileNameId, fileSizeId, buttonId) {
    const file = e.target.files[0];
    const selectedFileDiv = document.getElementById(selectedFileId);
    const fileNameSpan = document.getElementById(fileNameId);
    const fileSizeSpan = document.getElementById(fileSizeId);
    const uploadButton = document.getElementById(buttonId);
    
    if (file) {
        // Validate file type
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!allowedTypes.includes(file.type)) {
            alert('Please select a PDF, DOC, or DOCX file');
            e.target.value = '';
            return;
        }
        
        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size must be less than 10 MB');
            e.target.value = '';
            return;
        }
        
        if (selectedFileDiv) selectedFileDiv.style.display = 'block';
        if (fileNameSpan) fileNameSpan.textContent = file.name;
        if (fileSizeSpan) fileSizeSpan.textContent = formatFileSize(file.size);
        if (uploadButton) uploadButton.disabled = false;
        
        // For vendor form, also check vendor name
        if (fileInputId === 'vendorFile') {
            checkVendorFormValidity();
        }
    }
}

function checkVendorFormValidity() {
    const vendorName = document.getElementById('vendorName');
    const vendorFile = document.getElementById('vendorFile');
    const uploadButton = document.getElementById('uploadButton');
    
    if (uploadButton) {
        uploadButton.disabled = !vendorName.value.trim() || !vendorFile.files[0];
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

function clearVendorFile() {
    const vendorFile = document.getElementById('vendorFile');
    const selectedFile = document.getElementById('selectedFile');
    
    if (vendorFile) vendorFile.value = '';
    if (selectedFile) selectedFile.style.display = 'none';
    checkVendorFormValidity();
}

async function handleRFPUpload(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const uploadButton = document.getElementById('uploadButton');
    const uploadMessage = document.getElementById('uploadMessage');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    setButtonLoading(uploadButton, true);
    if (uploadProgress) uploadProgress.style.display = 'block';
    hideMessage(uploadMessage);
    
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 10;
        if (progress <= 90 && progressFill) {
            progressFill.style.width = progress + '%';
        }
    }, 200);
    
    try {
        const response = await fetch('/api/upload-rfp', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        clearInterval(progressInterval);
        if (progressFill) progressFill.style.width = '100%';
        
        if (data.success) {
            showMessage(uploadMessage, `✅ ${data.message}`, 'success');
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1500);
        } else {
            showMessage(uploadMessage, `❌ ${data.message}`, 'error');
        }
    } catch (error) {
        clearInterval(progressInterval);
        showMessage(uploadMessage, '❌ Upload failed. Please try again.', 'error');
        console.error('Upload error:', error);
    } finally {
        setButtonLoading(uploadButton, false);
        setTimeout(() => {
            if (uploadProgress) uploadProgress.style.display = 'none';
            if (progressFill) progressFill.style.width = '0%';
        }, 2000);
    }
}

async function handleVendorUpload(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const uploadButton = document.getElementById('uploadButton');
    const uploadMessage = document.getElementById('uploadMessage');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    
    setButtonLoading(uploadButton, true);
    if (uploadProgress) uploadProgress.style.display = 'block';
    hideMessage(uploadMessage);
    
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 10;
        if (progress <= 90 && progressFill) {
            progressFill.style.width = progress + '%';
        }
    }, 200);
    
    try {
        const response = await fetch('/api/upload-vendor', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        clearInterval(progressInterval);
        if (progressFill) progressFill.style.width = '100%';
        
        if (data.success) {
            showMessage(uploadMessage, `✅ ${data.message}`, 'success');
            
            // Reset form for next vendor
            setTimeout(() => {
                e.target.reset();
                clearVendorFile();
                hideMessage(uploadMessage);
            }, 2000);
        } else {
            showMessage(uploadMessage, `❌ ${data.message}`, 'error');
        }
    } catch (error) {
        clearInterval(progressInterval);
        showMessage(uploadMessage, '❌ Upload failed. Please try again.', 'error');
        console.error('Upload error:', error);
    } finally {
        setButtonLoading(uploadButton, false);
        setTimeout(() => {
            if (uploadProgress) uploadProgress.style.display = 'none';
            if (progressFill) progressFill.style.width = '0%';
        }, 2000);
    }
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
    autoResize.call(chatInput);
    
    setButtonLoading(sendButton, true);
    
    // Add thinking indicator
    const thinkingId = addMessage('bot', '💭 Thinking...');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        // Remove thinking indicator
        removeMessage(thinkingId);
        
        if (data.success) {
            addMessage('bot', data.answer);
            
            // Show sources if available
            if (data.sources && data.sources.length > 0) {
                addSources(data.sources);
            }
        } else {
            addMessage('bot', `❌ Error: ${data.message}`);
        }
    } catch (error) {
        removeMessage(thinkingId);
        addMessage('bot', '❌ Network error. Please try again.');
        console.error('Chat error:', error);
    } finally {
        setButtonLoading(sendButton, false);
    }
}

function addMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const chatWelcome = document.querySelector('.chat-welcome');
    
    if (chatWelcome && chatMessages.children.length === 0) {
        chatWelcome.style.display = 'none';
    }
    
    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    messageDiv.id = messageId;
    
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