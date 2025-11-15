// Files Page JavaScript

function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
        return;
    }
    
    fetch('/api/delete-file', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload page to show updated file list
            location.reload();
        } else {
            alert('Error deleting file: ' + data.message);
        }
    })
    .catch(error => {
        alert('Error deleting file: ' + error.message);
    });
}