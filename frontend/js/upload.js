// File Upload Handler
let currentFile = null;

// Initialize upload functionality
function initUpload() {
    const fileInput = document.getElementById('audioFileInput');
    const dropzone = document.getElementById('uploadDropzone');
    const uploadArea = document.getElementById('uploadArea');

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            // Only process if file is actually selected (not just cleared)
            if (file) {
                handleFile(file);
            }
        }
    });

    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('audio/')) {
                handleFile(file);
            } else {
                alert('Please upload an audio file');
            }
        }
    });
}

// Handle file upload
async function handleFile(file) {
    currentFile = file;
    
    // Reset any previous state
    resetProgress();
    
    // Hide results section if visible
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
    
    // Ensure upload section is visible
    const uploadSection = document.getElementById('uploadSection');
    if (uploadSection) {
        uploadSection.style.display = 'block';
    }
    
    // Validate file
    const maxSize = 25 * 1024 * 1024; // 25MB
    if (file.size > maxSize) {
        alert('File size exceeds 25MB limit');
        return;
    }

    const allowedTypes = ['audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/m4a', 'audio/x-m4a'];
    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|m4a)$/i)) {
        alert('Please upload a valid audio file (.mp3, .wav, or .m4a)');
        return;
    }

    // Show progress
    showProgress();
    updateProgress(10, 'Uploading file...');

    try {
        // Upload file
        const result = await API.uploadAudio(file);
        
        updateProgress(100, 'Processing complete!');
        
        // Show results after a short delay
        setTimeout(() => {
            hideProgress();
            // Reset file input so user can upload again
            const fileInput = document.getElementById('audioFileInput');
            if (fileInput) {
                fileInput.value = '';
            }
            currentFile = null;
            
            // Ensure results section exists and is ready
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) {
                displayResults(result);
            } else {
                console.error('Results section not found in DOM');
                alert('Processing complete! But results section not found.');
            }
        }, 1000);

    } catch (error) {
        console.error('Upload error:', error);
        hideProgress();
        // Reset file input on error so user can try again
        const fileInput = document.getElementById('audioFileInput');
        if (fileInput) {
            fileInput.value = '';
        }
        currentFile = null;
        alert('Error: ' + error.message);
    }
}

// Show progress bar
function showProgress() {
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('statusContainer').style.display = 'block';
    updateStatus('upload', true);
}

// Update progress
function updateProgress(percent, text) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

// Update status
function updateStatus(step, completed) {
    const statusMap = {
        'upload': 'statusPreprocessing',
        'preprocessing': 'statusPreprocessing',
        'transcribing': 'statusTranscribing',
        'extracting': 'statusExtracting',
        'assigning': 'statusAssigning'
    };

    const statusId = statusMap[step];
    if (statusId) {
        const statusItem = document.getElementById(statusId);
        if (completed) {
            statusItem.classList.add('completed');
            statusItem.querySelector('.status-icon').textContent = '✓';
        } else {
            statusItem.classList.add('active');
            statusItem.querySelector('.status-icon').textContent = '⏳';
        }
    }
}

// Hide progress
function hideProgress() {
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('statusContainer').style.display = 'none';
}

// Reset all progress and status indicators
function resetProgress() {
    // Hide progress containers
    const progressContainer = document.getElementById('progressContainer');
    const statusContainer = document.getElementById('statusContainer');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
    if (statusContainer) {
        statusContainer.style.display = 'none';
    }
    
    // Reset progress bar
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    if (progressFill) {
        progressFill.style.width = '0%';
    }
    if (progressText) {
        progressText.textContent = 'Processing...';
    }
    
    // Reset all status indicators
    const statusIds = ['statusPreprocessing', 'statusTranscribing', 'statusExtracting', 'statusAssigning'];
    statusIds.forEach(statusId => {
        const statusItem = document.getElementById(statusId);
        if (statusItem) {
            statusItem.classList.remove('completed', 'active');
            const icon = statusItem.querySelector('.status-icon');
            if (icon) {
                icon.textContent = '⏳';
            }
        }
    });
    
    // Reset file input so same file can be selected again
    const fileInput = document.getElementById('audioFileInput');
    if (fileInput) {
        fileInput.value = '';
    }
    
    // Reset current file
    currentFile = null;
}

// Make resetProgress globally accessible
window.resetProgress = resetProgress;

// Initialize on page load
document.addEventListener('DOMContentLoaded', initUpload);

