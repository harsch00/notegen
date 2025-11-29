// Track recording state per tab
const recordingTabs = new Set();

// Listen for tab updates to detect Google Meet
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (!tab.url) return;
    
    const isMeetPage = tab.url.includes('meet.google.com/') && 
                       tab.url.match(/meet\.google\.com\/[a-z]{3}-[a-z]{4}-[a-z]{3}/);
    
    if (changeInfo.status === 'complete' || changeInfo.url) {
        if (isMeetPage && !recordingTabs.has(tabId)) {
            // Start automatic recording
            recordingTabs.add(tabId);
            chrome.tabs.sendMessage(tabId, { action: 'autoStartRecording' }).catch(() => {
                // Content script might not be ready yet, retry after a delay
                setTimeout(() => {
                    chrome.tabs.sendMessage(tabId, { action: 'autoStartRecording' }).catch(() => {});
                }, 1000);
            });
        } else if (!isMeetPage && recordingTabs.has(tabId)) {
            // Stop recording if leaving Meet page
            recordingTabs.delete(tabId);
            chrome.tabs.sendMessage(tabId, { action: 'autoStopRecording' }).catch(() => {});
        }
    }
});

// Clean up when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
    recordingTabs.delete(tabId);
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'startRecording' || message.action === 'autoStartRecording' || message.action === 'getStreamId') {
        const tabId = sender.tab ? sender.tab.id : null;
        if (!tabId) {
            // Fallback: get active tab
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                if (tabs[0] && tabs[0].url && tabs[0].url.includes('meet.google.com')) {
                    requestStreamId(tabs[0].id, sendResponse);
                } else {
                    sendResponse({ success: false, error: 'Not on a Google Meet page' });
                }
            });
            return true;
        } else {
            requestStreamId(tabId, sendResponse);
            return true;
        }
    }
    
    if (message.action === 'stopRecording' || message.action === 'autoStopRecording') {
        const tabId = sender.tab ? sender.tab.id : null;
        if (tabId) {
            recordingTabs.delete(tabId);
        }
        chrome.storage.local.set({ recording: false });
        sendResponse({ success: true });
    }
    
    if (message.action === 'recordingStarted') {
        const tabId = sender.tab ? sender.tab.id : null;
        if (tabId) {
            recordingTabs.add(tabId);
        }
    }
    
    if (message.action === 'recordingStopped') {
        const tabId = sender.tab ? sender.tab.id : null;
        if (tabId) {
            recordingTabs.delete(tabId);
        }
    }
});

function requestStreamId(tabId, sendResponse) {
    chrome.tabCapture.getMediaStreamId({ consumerTabId: tabId }, (streamId) => {
        if (chrome.runtime.lastError) {
            sendResponse({ success: false, error: chrome.runtime.lastError.message });
        } else {
            sendResponse({ success: true, streamId: streamId });
        }
    });
}


