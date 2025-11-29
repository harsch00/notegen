let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let currentStream = null;
let lastRecordedBlob = null; // Store last recorded blob for download

// Check if we're on a Meet page and auto-start if needed
function checkAndStartRecording() {
    const url = window.location.href;
    if (url.includes('meet.google.com/') && 
        url.match(/meet\.google\.com\/[a-z]{3}-[a-z]{4}-[a-z]{3}/) &&
        !isRecording) {
        // Wait a bit for page to load, then auto-start
        setTimeout(() => {
            chrome.runtime.sendMessage({ action: 'getStreamId' }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error('Error getting stream ID:', chrome.runtime.lastError.message);
                    return;
                }
                if (response && response.success && response.streamId) {
                    startRecording(response.streamId);
                } else {
                    console.error('Auto-start failed:', response?.error);
                }
            });
        }, 2000);
    }
}

// Check on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAndStartRecording);
} else {
    checkAndStartRecording();
}

// Listen for URL changes (for SPA navigation) - use a more efficient approach
let lastUrl = window.location.href;
const urlCheckInterval = setInterval(() => {
    const currentUrl = window.location.href;
    if (currentUrl !== lastUrl) {
        lastUrl = currentUrl;
        const isMeetPage = currentUrl.includes('meet.google.com/') && 
                          currentUrl.match(/meet\.google\.com\/[a-z]{3}-[a-z]{4}-[a-z]{3}/);
        
        if (isMeetPage && !isRecording) {
            // Auto-start recording
            chrome.runtime.sendMessage({ action: 'getStreamId' }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error('Error getting stream ID:', chrome.runtime.lastError.message);
                    return;
                }
                if (response && response.success && response.streamId) {
                    startRecording(response.streamId);
                }
            });
        } else if (!isMeetPage && isRecording) {
            // Auto-stop recording
            stopRecording();
        }
    }
}, 1000); // Check every second

// Single message listener for all messages
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // Handle auto-start from background
    if (message.action === 'autoStartRecording') {
        chrome.runtime.sendMessage({ action: 'getStreamId' }, (response) => {
            if (chrome.runtime.lastError) {
                console.error('Error getting stream ID:', chrome.runtime.lastError.message);
                if (sendResponse) sendResponse({ success: false, error: chrome.runtime.lastError.message });
                return;
            }
            if (response && response.success && response.streamId) {
                startRecording(response.streamId).then(success => {
                    if (sendResponse) sendResponse({ success: success });
                });
            } else {
                console.error('Failed to get stream ID:', response?.error);
                if (sendResponse) sendResponse({ success: false, error: response?.error || 'Failed to get stream' });
            }
        });
        return true; // Keep channel open
    }
    
    // Handle auto-stop from background
    if (message.action === 'autoStopRecording') {
        stopRecording();
        if (sendResponse) sendResponse({ success: true });
        return false;
    }
    
    // Handle manual start from popup
    if (message.action === 'startRecording') {
        if (message.streamId) {
            startRecording(message.streamId).then(success => {
                if (sendResponse) sendResponse({ success: success });
            });
            return true; // Keep channel open for async response
        }
    }
    
    // Handle manual stop from popup
    if (message.action === 'stopRecording') {
        stopRecording();
        if (sendResponse) sendResponse({ success: true });
        return false;
    }
    
    // Handle status check
    if (message.action === 'getRecordingStatus') {
        if (sendResponse) sendResponse({ isRecording: isRecording });
        return false;
    }
    
    // Handle download request
    if (message.action === 'downloadRecording') {
        if (lastRecordedBlob) {
            // Create download link
            const url = URL.createObjectURL(lastRecordedBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `meet-recording-${Date.now()}.${lastRecordedBlob.type.includes('ogg') ? 'ogg' : lastRecordedBlob.type.includes('mp4') ? 'mp4' : 'webm'}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            if (sendResponse) sendResponse({ success: true, size: lastRecordedBlob.size });
        } else {
            if (sendResponse) sendResponse({ success: false, error: 'No recording available' });
        }
        return false;
    }
    
    return false;
});

// Function to start recording
async function startRecording(streamId) {
    if (isRecording) {
        console.log('Already recording');
        return true;
    }
    
    try {
        console.log('Starting recording with streamId:', streamId);
        
        // Get the stream using the stream ID
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                mandatory: {
                    chromeMediaSource: 'tab',
                    chromeMediaSourceId: streamId
                }
            },
            video: false
        });
        
        currentStream = stream;
        
        // Check available MIME types
        const mimeTypes = ['audio/webm', 'audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'];
        let selectedMimeType = 'audio/webm';
        for (const mimeType of mimeTypes) {
            if (MediaRecorder.isTypeSupported(mimeType)) {
                selectedMimeType = mimeType;
                break;
            }
        }
        
        console.log('Using MIME type:', selectedMimeType);
        
        // Create MediaRecorder
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: selectedMimeType
        });
        
        recordedChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                console.log('Received audio chunk:', event.data.size, 'bytes');
                recordedChunks.push(event.data);
            }
        };
        
        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
            chrome.runtime.sendMessage({ 
                action: 'recordingError', 
                error: event.error?.message || 'Recording error'
            }).catch(err => console.error('Error sending message:', err));
        };
        
        mediaRecorder.onstop = async () => {
            console.log('Recording stopped, chunks:', recordedChunks.length);
            
            if (recordedChunks.length === 0) {
                console.warn('No audio chunks recorded');
                chrome.runtime.sendMessage({ 
                    action: 'uploadError',
                    error: 'No audio was recorded'
                }).catch(err => console.error('Error sending message:', err));
                return;
            }
            
            // Create blob from recorded chunks
            const blob = new Blob(recordedChunks, { type: selectedMimeType });
            console.log('Created blob, size:', blob.size, 'bytes');
            
            // Store blob for download
            lastRecordedBlob = blob;
            chrome.storage.local.set({ lastRecordedBlobSize: blob.size });
            
            if (blob.size === 0) {
                console.warn('Empty blob created');
                chrome.runtime.sendMessage({ 
                    action: 'uploadError',
                    error: 'Recorded audio is empty'
                }).catch(err => console.error('Error sending message:', err));
                return;
            }
            
            // Get options from storage (set by popup or use defaults)
            chrome.storage.local.get(['detailLevel', 'formatType', 'autoUpload'], async (result) => {
                const detailLevel = result.detailLevel || 'medium';
                const formatType = result.formatType || 'bullet';
                const autoUpload = result.autoUpload !== false; // Default to true
                
                if (autoUpload) {
                    // Upload directly to backend
                    await uploadAudioToBackend(blob, detailLevel, formatType);
                } else {
                    // Just notify that recording is complete
                    chrome.runtime.sendMessage({ 
                        action: 'recordingComplete',
                        blobSize: blob.size
                    }).catch(err => console.error('Error sending message:', err));
                }
            });
            
            // Stop all tracks
            if (currentStream) {
                currentStream.getTracks().forEach(track => {
                    track.stop();
                    console.log('Stopped track:', track.kind);
                });
                currentStream = null;
            }
        };
        
        // Start recording with timeslice to get chunks periodically
        mediaRecorder.start(1000); // Get chunks every second
        isRecording = true;
        
        console.log('Recording started successfully');
        
        // Notify background and popup
        chrome.runtime.sendMessage({ action: 'recordingStarted' }).catch(err => 
            console.error('Error sending recordingStarted message:', err)
        );
        
        return true;
    } catch (error) {
        console.error('Error starting recording:', error);
        isRecording = false;
        chrome.runtime.sendMessage({ 
            action: 'recordingError', 
            error: error.message 
        }).catch(err => console.error('Error sending error message:', err));
        return false;
    }
}

// Function to upload audio to backend
async function uploadAudioToBackend(audioBlob, detailLevel, formatType) {
    try {
        console.log('Uploading audio to backend, size:', audioBlob.size);
        
        // Notify popup that upload is starting
        chrome.runtime.sendMessage({ 
            action: 'uploadStarted' 
        }).catch(err => console.error('Error sending uploadStarted:', err));
        
        const formData = new FormData();
        // Determine file extension based on blob type
        let ext = 'webm';
        if (audioBlob.type.includes('ogg')) ext = 'ogg';
        else if (audioBlob.type.includes('mp4')) ext = 'mp4';
        
        const fileName = `meet-recording-${Date.now()}.${ext}`;
        formData.append('audio', audioBlob, fileName);
        formData.append('detail_level', detailLevel);
        formData.append('format_type', formatType);
        
        console.log('Sending request to backend...');
        const response = await fetch('http://localhost:5000/api/generate-notes/audio', {
            method: 'POST',
            body: formData
        });
        
        console.log('Response status:', response.status);
        
        let data;
        try {
            data = await response.json();
            console.log('Response data:', data);
        } catch (e) {
            const text = await response.text();
            console.error('Failed to parse JSON response:', text);
            throw new Error(`Server error: ${response.status} - ${text.substring(0, 200)}`);
        }
        
        if (response.ok && data.success) {
            console.log('Upload successful!');
            chrome.runtime.sendMessage({ 
                action: 'uploadComplete',
                success: true,
                note: data.note
            }).catch(err => console.error('Error sending uploadComplete:', err));
        } else {
            const errorMsg = data.error || data.message || 'Failed to generate notes';
            console.error('Backend error:', errorMsg);
            throw new Error(errorMsg);
        }
    } catch (error) {
        console.error('Upload error:', error);
        chrome.runtime.sendMessage({ 
            action: 'uploadError',
            error: error.message
        }).catch(err => console.error('Error sending uploadError:', err));
    }
}

// Function to stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        console.log('Stopping recording...');
        mediaRecorder.stop();
        isRecording = false;
        chrome.runtime.sendMessage({ action: 'recordingStopped' }).catch(err => 
            console.error('Error sending recordingStopped:', err)
        );
    } else {
        console.log('Not recording, nothing to stop');
    }
}
