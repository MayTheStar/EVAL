// Dashboard JavaScript

// Check status on page load
document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    setInterval(checkStatus, 5000); // Check every 5 seconds
    
    // Load vendor scores if available
    loadVendorScores();

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


// ------------------------------
// NEW SECTION:
// Load vendor scores and render cards
// ------------------------------

async function loadVendorScores() {
    try {
        const response = await fetch('/api/get-scores');
        const data = await response.json();

        const container = document.getElementById("vendor-score-container");
        if (!container) return; // Not on dashboard

        // No results yet
        if (!data.success || !data.scores || !data.scores.vendors) {
            container.innerHTML = `
                <div class="no-scores">
                    <p>No scoring results available yet.</p>
                    <p>Please upload vendors and process documents.</p>
                </div>
            `;
            return;
        }

        const vendors = data.scores.vendors;
        container.innerHTML = "";

        Object.values(vendors).forEach(vendor => {
            const card = `
                <div class="vendor-card">
                    <h2>${vendor.vendor_name}</h2>

                    <div class="score-row">
                        <div class="score-box">
                            <span class="label">Total Score</span>
                            <span class="value">${vendor.total_score}</span>
                        </div>

                        <div class="score-box">
                            <span class="label">Confidence</span>
                            <span class="value">${(vendor.confidence_score * 100).toFixed(1)}%</span>
                        </div>
                    </div>

                    <h3>Strengths</h3>
                    <ul class="list-box">
                        ${vendor.strengths.map(s => `<li>${s}</li>`).join("")}
                    </ul>

                    <h3>Weaknesses</h3>
                    <ul class="list-box">
                        ${vendor.weaknesses.map(w => `<li>${w}</li>`).join("")}
                    </ul>

                    <h3>Criteria Breakdown</h3>
                    <div class="criteria-box">
                        ${vendor.criteria_breakdown.map(c =>
                            `
                            <div class="criterion">
                                <strong>${c.criterion_name}</strong>
                                <div class="crit-details">
                                    <p>Weight: ${c.weight}</p>
                                    <p>Raw Score: ${c.raw_score}</p>
                                    <p>Weighted: ${c.weighted_score}</p>
                                    <p>Confidence: ${(c.confidence * 100).toFixed(1)}%</p>
                                </div>

                                <details>
                                    <summary>Evidence</summary>
                                    <ul>${c.evidence.map(e => `<li>${e}</li>`).join("")}</ul>
                                </details>

                                <details>
                                    <summary>Gaps</summary>
                                    <ul>${c.gaps.map(g => `<li>${g}</li>`).join("")}</ul>
                                </details>
                            </div>
                            `
                        ).join("")}
                    </div>
                </div>
            `;

            container.innerHTML += card;
        });

    } catch (error) {
        console.error("Error loading vendor scores:", error);
    }
}



// ------------------------------
// EXISTING STATUS + PROCESSING CODE
// (unchanged; kept as-is)
// ------------------------------

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
        
        // Show process bar
        const processBar = document.getElementById('process-bar');
        if (processBar) {
            if ((data.rfp_uploaded || data.vendors_count > 0) && !data.processed) {
                processBar.style.display = 'block';
            } else {
                processBar.style.display = 'none';
            }
        }
        
        // Chatbot nav link
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
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        modal.classList.remove('show');
        
        if (data.success) {
            alert(`Success! ${data.message}`);
            checkStatus();
            loadVendorScores();  // reload vendor scores after processing
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
