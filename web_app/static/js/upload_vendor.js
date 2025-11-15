// Vendor Upload JavaScript

let selectedFile = null;
let uploadedVendors = [];

document.addEventListener('DOMContentLoaded', () => {
    const uploadBox = document.getElementById('upload-box');
    const fileInput = document.getElementById('file-input');
    const uploadInfo = document.getElementById('upload-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const removeButton = document.getElementById('remove-file');
    const importButton = document.getElementById('import-button');
    const vendorNameInput = document.getElementById('vendor-name');
    
    // Click to upload
    uploadBox.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File selected
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileSelect(file);
        }
    });
    
    // Drag and drop
    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = 'var(--light-teal)';
        uploadBox.style.background = '#FAFAFA';
    });
    
    uploadBox.addEventListener('dragleave', () => {
        uploadBox.style.borderColor = 'var(--border-color)';
        uploadBox.style.background = 'var(--card-bg)';
    });
    
    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = 'var(--border-color)';
        uploadBox.style.background = 'var(--card-bg)';
        
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileSelect(file);
        }
    });
    
    // Remove file
    removeButton.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        uploadBox.style.display = 'flex';
        uploadInfo.style.display = 'none';
        importButton.disabled = true;
    });
    
    // Import button
    importButton.addEventListener('click', uploadFile);
    
    // Modal buttons
    document.getElementById('done-button').addEventListener('click', () => {
        window.location.href = '/dashboard';
    });
    
    document.getElementById('another-button').addEventListener('click', () => {
        document.getElementById('success-modal').classList.remove('show');
        resetForm();
    });
    
    document.getElementById('close-error').addEventListener('click', () => {
        document.getElementById('error-modal').classList.remove('show');
    });
    
    // Enable/disable import button based on vendor name
    vendorNameInput.addEventListener('input', () => {
        updateImportButton();
    });
});

function handleFileSelect(file) {
    // Validate file type
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!allowedTypes.includes(file.type)) {
        showError('Invalid file type. Please upload PDF, DOC, or DOCX files.');
        return;
    }
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showError('File size exceeds 10MB limit.');
        return;
    }
    
    selectedFile = file;
    
    // Update UI
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-size').textContent = formatFileSize(file.size);
    document.getElementById('upload-box').style.display = 'none';
    document.getElementById('upload-info').style.display = 'flex';
    
    updateImportButton();
}

function updateImportButton() {
    const vendorName = document.getElementById('vendor-name').value.trim();
    const importButton = document.getElementById('import-button');
    importButton.disabled = !selectedFile || !vendorName;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function uploadFile() {
    if (!selectedFile) return;
    
    const vendorName = document.getElementById('vendor-name').value.trim();
    if (!vendorName) {
        showError('Please enter a vendor name');
        return;
    }
    
    const importButton = document.getElementById('import-button');
    importButton.disabled = true;
    importButton.textContent = 'Uploading...';
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('vendor_name', vendorName);
    
    try {
        const response = await fetch('/api/upload-vendor', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Add to uploaded vendors list
            uploadedVendors.push({
                name: data.vendor_name,
                filename: data.filename
            });
            updateVendorsList();
            
            // Update success message
            document.getElementById('success-message').textContent = 
                `Vendor response from ${data.vendor_name} uploaded successfully!`;
            
            // Show success modal
            document.getElementById('success-modal').classList.add('show');
        } else {
            showError(data.message);
        }
        
    } catch (error) {
        showError('Error uploading file: ' + error.message);
    } finally {
        importButton.disabled = false;
        importButton.textContent = 'Import';
    }
}

function updateVendorsList() {
    const vendorsList = document.getElementById('vendors-list');
    const uploadedVendorsDiv = document.getElementById('uploaded-vendors');
    
    if (uploadedVendors.length > 0) {
        uploadedVendorsDiv.style.display = 'block';
        vendorsList.innerHTML = uploadedVendors.map(vendor => `
            <div class="vendor-tag">
                📦 ${vendor.name} - ${vendor.filename}
            </div>
        `).join('');
    } else {
        uploadedVendorsDiv.style.display = 'none';
    }
}

function resetForm() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('vendor-name').value = '';
    document.getElementById('upload-box').style.display = 'flex';
    document.getElementById('upload-info').style.display = 'none';
    document.getElementById('import-button').disabled = true;
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('error-modal').classList.add('show');
}