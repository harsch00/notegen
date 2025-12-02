let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let currentStream = null;
let lastRecordedBlob = null; // Store last recorded blob for download

function isMeetPage() {
    return window.location.href.includes('meet.google.com/');
}

// Single message listener for popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!isMeetPage()) {
        sendResponse && sendResponse({ success: false, error: 'Not on a Google Meet page' });
        return false;
    }

    if (message.action === 'startRecording') {
        startRecording().then(success => {
            sendResponse && sendResponse({ success, error: success ? null : 'Could not start recording' });
        }).catch(err => {
            console.error('startRecording error:', err);
            sendResponse && sendResponse({ success: false, error: err.message });
        });
        return true; // async
    }

    if (message.action === 'stopRecording') {
        stopRecording();
        sendResponse && sendResponse({ success: true });
        return false;
    }

    if (message.action === 'getRecordingStatus') {
        sendResponse && sendResponse({ isRecording });
        return false;
    }

    if (message.action === 'downloadRecording') {
        if (!lastRecordedBlob) {
            sendResponse && sendResponse({ success: false, error: 'No recording available' });
            return false;
        }
        const url = URL.createObjectURL(lastRecordedBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `meet-recording-${Date.now()}.webm`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        sendResponse && sendResponse({ success: true, size: lastRecordedBlob.size });
        return false;
    }

    return false;
});

// Mic-based recording
async function startRecording() {
    if (isRecording) {
        console.log('Already recording');
        return true;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('getUserMedia is not supported in this browser');
    }

    try {
        console.log('Requesting microphone access...');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        currentStream = stream;

        const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm'];
        let selectedMimeType = 'audio/webm';
        for (const mt of mimeTypes) {
            if (MediaRecorder.isTypeSupported(mt)) {
                selectedMimeType = mt;
                break;
            }
        }
        console.log('Using MIME type:', selectedMimeType);

        mediaRecorder = new MediaRecorder(stream, { mimeType: selectedMimeType });
        recordedChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
            chrome.runtime.sendMessage({
                action: 'recordingError',
                error: event.error?.message || 'Recording error'
            });
        };

        mediaRecorder.onstop = () => {
            console.log('Recording stopped, chunks:', recordedChunks.length);
            if (!recordedChunks.length) {
                chrome.runtime.sendMessage({
                    action: 'uploadError',
                    error: 'No audio was recorded'
                });
                return;
            }

            const blob = new Blob(recordedChunks, { type: selectedMimeType });
            console.log('Recorded blob size:', blob.size);
            lastRecordedBlob = blob;
            chrome.storage.local.set({ lastRecordedBlobSize: blob.size });

            if (!blob.size) {
                chrome.runtime.sendMessage({
                    action: 'uploadError',
                    error: 'Recorded audio is empty'
                });
                return;
            }

            // Auto-upload
            chrome.storage.local.get(['detailLevel', 'formatType'], async (result) => {
                const detailLevel = result.detailLevel || 'medium';
                const formatType = result.formatType || 'bullet';
                await uploadAudioToBackend(blob, detailLevel, formatType);
            });

            if (currentStream) {
                currentStream.getTracks().forEach(t => t.stop());
                currentStream = null;
            }
        };

        mediaRecorder.start(1000);
        isRecording = true;
        chrome.runtime.sendMessage({ action: 'recordingStarted' });
        return true;
    } catch (err) {
        console.error('Error starting recording:', err);
        isRecording = false;
        chrome.runtime.sendMessage({
            action: 'recordingError',
            error: err.message
        });
        return false;
    }
}

async function uploadAudioToBackend(audioBlob, detailLevel, formatType) {
    try {
        chrome.runtime.sendMessage({ action: 'uploadStarted' });

        const formData = new FormData();
        formData.append('audio', audioBlob, `meet-recording-${Date.now()}.webm`);
        formData.append('detail_level', detailLevel);
        formData.append('format_type', formatType);

        const response = await fetch('http://localhost:5000/api/generate-notes/audio', {
            method: 'POST',
            body: formData
        });

        let data;
        try {
            data = await response.json();
        } catch {
            const text = await response.text();
            throw new Error(`Server error ${response.status}: ${text.substring(0, 200)}`);
        }

        if (response.ok && data.success) {
            chrome.runtime.sendMessage({
                action: 'uploadComplete',
                success: true,
                note: data.note
            });
        } else {
            throw new Error(data.error || 'Failed to generate notes');
        }
    } catch (err) {
        console.error('Upload error:', err);
        chrome.runtime.sendMessage({
            action: 'uploadError',
            error: err.message
        });
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        chrome.runtime.sendMessage({ action: 'recordingStopped' });
        if (currentStream) {
            currentStream.getTracks().forEach(t => t.stop());
            currentStream = null;
        }
    } else {
        console.log('Not recording, nothing to stop');
    }
}
