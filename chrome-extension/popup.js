let isRecording = false;
let recordedBlob = null;

// Check if on Google Meet page
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0];
    if (!currentTab.url || !currentTab.url.includes('meet.google.com')) {
        document.getElementById('status').textContent = 'Please open a Google Meet page';
        document.getElementById('status').className = 'status error';
        document.getElementById('start-btn').disabled = true;
    }
});

// Get recording status from content script
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0] && tabs[0].url && tabs[0].url.includes('meet.google.com')) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'getRecordingStatus' }, (response) => {
            if (response && response.isRecording) {
                updateUI(true);
            }
        });
    }
});

// Radio button styling
document.querySelectorAll('.radio-option').forEach(option => {
    option.addEventListener('click', () => {
        const value = option.dataset.value;
        const radio = option.querySelector('input[type="radio"]');
        radio.checked = true;
        
        option.parentElement.querySelectorAll('.radio-option').forEach(o => {
            o.classList.remove('selected');
        });
        option.classList.add('selected');
    });
});

// Start recording button
document.getElementById('start-btn').addEventListener('click', async () => {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
        const currentTab = tabs[0];
        
        if (!currentTab.url || !currentTab.url.includes('meet.google.com')) {
            alert('Please open a Google Meet page first');
            return;
        }
        
        // Save options to storage for content script
        const detailLevel = document.getElementById('detail-level').value;
        const formatType = document.querySelector('input[name="format"]:checked').value;
        chrome.storage.local.set({ 
            detailLevel: detailLevel,
            formatType: formatType
        });
        
        // Request stream ID from background
        chrome.runtime.sendMessage({ action: 'startRecording' }, (response) => {
            if (response && response.success) {
                // Send stream ID to content script
                chrome.tabs.sendMessage(currentTab.id, {
                    action: 'startRecording',
                    streamId: response.streamId
                }, (contentResponse) => {
                    if (contentResponse && contentResponse.success) {
                        updateUI(true);
                    } else {
                        alert('Failed to start recording. Make sure you grant microphone permissions.');
                        updateUI(false);
                    }
                });
            } else {
                alert('Failed to start recording: ' + (response?.error || 'Unknown error'));
            }
        });
    });
});

// Stop recording button
document.getElementById('stop-btn').addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const currentTab = tabs[0];
        if (currentTab && currentTab.url && currentTab.url.includes('meet.google.com')) {
            chrome.tabs.sendMessage(currentTab.id, { action: 'stopRecording' }, (response) => {
                if (response && response.success) {
                    updateUI(false);
                }
            });
        }
    });
});

// Update UI based on recording state
function updateUI(recording) {
    isRecording = recording;
    const statusDiv = document.getElementById('status');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const downloadBtn = document.getElementById('download-btn');
    
    if (recording) {
        statusDiv.textContent = '🔴 Recording...';
        statusDiv.className = 'status recording';
        startBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        downloadBtn.style.display = 'none';
    } else {
        statusDiv.textContent = 'Ready to record';
        statusDiv.className = 'status idle';
        startBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        // Check if there's a recording available
        checkForRecording();
    }
}

// Check if there's a recording available to download
function checkForRecording() {
    chrome.storage.local.get(['lastRecordedBlobSize'], (result) => {
        const downloadBtn = document.getElementById('download-btn');
        if (result.lastRecordedBlobSize && result.lastRecordedBlobSize > 0) {
            downloadBtn.style.display = 'block';
            downloadBtn.textContent = `Download Recording (${formatBytes(result.lastRecordedBlobSize)})`;
        } else {
            downloadBtn.style.display = 'none';
        }
    });
}

// Format bytes to human readable
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'recordingStarted') {
        updateUI(true);
    }
    
    if (message.action === 'recordingStopped') {
        updateUI(false);
    }
    
    if (message.action === 'uploadStarted') {
        const statusDiv = document.getElementById('status');
        statusDiv.textContent = '⏳ Processing audio...';
        statusDiv.className = 'status idle';
    }
    
    if (message.action === 'uploadComplete') {
        const statusDiv = document.getElementById('status');
        statusDiv.textContent = '✅ Notes generated!';
        statusDiv.className = 'status idle';
        updateUI(false);
        
        // Open web app in new tab to view notes
        setTimeout(() => {
            chrome.tabs.create({ url: 'http://localhost:5000/#history' });
        }, 1000);
    }
    
    if (message.action === 'uploadError') {
        const statusDiv = document.getElementById('status');
        const errorMsg = message.error || 'Unknown error';
        statusDiv.textContent = '❌ Error: ' + errorMsg;
        statusDiv.className = 'status error';
        console.error('Upload error:', errorMsg);
        alert('Error generating notes: ' + errorMsg);
        updateUI(false);
    }
    
    if (message.action === 'recordingError') {
        alert('Recording error: ' + message.error);
        updateUI(false);
    }
    
    if (message.action === 'recordingComplete') {
        updateUI(false);
        checkForRecording();
    }
});

// Download button handler
document.getElementById('download-btn').addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const currentTab = tabs[0];
        if (currentTab && currentTab.url && currentTab.url.includes('meet.google.com')) {
            chrome.tabs.sendMessage(currentTab.id, { action: 'downloadRecording' }, (response) => {
                if (chrome.runtime.lastError) {
                    alert('Error: ' + chrome.runtime.lastError.message);
                    return;
                }
                if (response && response.success) {
                    const statusDiv = document.getElementById('status');
                    statusDiv.textContent = `✅ Downloaded (${formatBytes(response.size)})`;
                    statusDiv.className = 'status idle';
                } else {
                    alert('Error: ' + (response?.error || 'Failed to download'));
                }
            });
        } else {
            alert('Please open a Google Meet page first');
        }
    });
});

// Check for recording on popup open
checkForRecording();

