// Dashboard JavaScript

// Check status on page load
document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    setInterval(checkStatus, 5000); // Check every 5 seconds
    
    // Setup process button
    const processButton = document.getElementById('process-button');
    if (processButton) {
        processButton.addEventListener('click', processDocuments);
    }
    
    // Setup chatbot button
    const chatbotButton = document.getElementById('chatbot-button');
    if (chatbotButton) {
        chatbotButton.addEventListener('click', () => {
            fetch('/api/get-status')
                .then(res => res.json())
                .then(data => {
                    if (data.chatbot_ready) {
                        window.location.href = '/chatbot';
                    } else {
                        alert('Please upload and process documents first!');
                    }
                });
        });
    }
});

async function checkStatus() {
    try {
        const response = await fetch('/api/get-status');
        const data = await response.json();
        
        // Update status indicators
        updateStatus('rfp-status', data.rfp_uploaded, 
            data.rfp_uploaded ? '✓ RFP uploaded' : 'Not uploaded');
        
        updateStatus('vendor-status', data.vendors_count > 0, 
            data.vendors_count > 0 ? `✓ ${data.vendors_count} vendor(s) uploaded` : 'No vendors');
        
        updateStatus('chatbot-status', data.chatbot_ready, 
            data.chatbot_ready ? '✓ Ready' : 'Process documents first');
        
        updateStatus('files-status', data.files_count > 0, 
            data.files_count > 0 ? `${data.files_count} file(s)` : 'No files');
        
        // Show process button if files are uploaded but not processed
        const processBar = document.getElementById('process-bar');
        if (processBar) {
            if ((data.rfp_uploaded || data.vendors_count > 0) && !data.processed) {
                processBar.style.display = 'block';
            } else {
                processBar.style.display = 'none';
            }
        }
        
        // Update chatbot nav link
        const chatbotNav = document.getElementById('chatbot-nav');
        if (chatbotNav) {
            if (!data.chatbot_ready) {
                chatbotNav.style.opacity = '0.5';
                chatbotNav.style.pointerEvents = 'none';
            } else {
                chatbotNav.style.opacity = '1';
                chatbotNav.style.pointerEvents = 'auto';
            }
        }
        
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

function updateStatus(elementId, isSuccess, text) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = text;
    element.style.color = isSuccess ? 'var(--success-green)' : '#999';
    element.style.fontWeight = isSuccess ? '600' : 'normal';
}

async function processDocuments() {
    const modal = document.getElementById('processing-modal');
    const button = document.getElementById('process-button');
    
    // Show processing modal
    modal.classList.add('show');
    button.disabled = true;
    
    try {
        const response = await fetch('/api/process-documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        modal.classList.remove('show');
        
        if (data.success) {
            alert(`Success! ${data.message}`);
            checkStatus();
        } else {
            alert(`Error: ${data.message}`);
        }
        
    } catch (error) {
        modal.classList.remove('show');
        alert(`Error processing documents: ${error.message}`);
    } finally {
        button.disabled = false;
    }
}