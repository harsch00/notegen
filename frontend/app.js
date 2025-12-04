// Detect if running on same origin or different port
const API_BASE_URL = window.location.origin === 'http://localhost:5000' 
    ? '/api' 
    : 'http://localhost:5000/api';

// Check if we should open history tab from URL hash
window.addEventListener('DOMContentLoaded', () => {
    if (window.location.hash === '#history') {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelector('[data-tab="history"]').classList.add('active');
        document.getElementById('history-tab').classList.add('active');
        loadHistory();
    }
});

// Tab navigation
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        
        // Update active nav button
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update active tab content
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`${tab}-tab`).classList.add('active');
        
        // Load history if switching to history tab
        if (tab === 'history') {
            loadHistory();
        }
    });
});

// Radio button styling
document.querySelectorAll('.radio-option').forEach(option => {
    option.addEventListener('click', () => {
        const value = option.dataset.value;
        const radio = option.querySelector('input[type="radio"]');
        radio.checked = true;
        
        // Update styling
        option.parentElement.querySelectorAll('.radio-option').forEach(o => {
            o.classList.remove('selected');
        });
        option.classList.add('selected');
    });
});

// YouTube form submission
document.getElementById('youtube-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const url = document.getElementById('youtube-url').value;
    const detailLevel = document.getElementById('detail-level').value;
    const formatType = document.querySelector('input[name="format_type"]:checked').value;
    
    // Show loading, hide results and error
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').classList.remove('show');
    document.getElementById('error').style.display = 'none';
    document.getElementById('generate-btn').disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-notes/youtube`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                detail_level: detailLevel,
                format_type: formatType
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Show results - render markdown
            const notesContent = document.getElementById('notes-content');
            if (typeof marked !== 'undefined') {
                notesContent.innerHTML = marked.parse(data.note.content);
            } else {
                notesContent.textContent = data.note.content;
            }
            document.getElementById('results').classList.add('show');
            
            // Reload history if on history tab
            if (document.getElementById('history-tab').classList.contains('active')) {
                loadHistory();
            }
        } else {
            throw new Error(data.error || 'Failed to generate notes');
        }
    } catch (error) {
        document.getElementById('error').textContent = `Error: ${error.message}`;
        document.getElementById('error').style.display = 'block';
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('generate-btn').disabled = false;
    }
});

// Load history
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/notes`);
        const data = await response.json();
        
        if (response.ok) {
            displayHistory(data.notes || []);
        } else {
            throw new Error(data.error || 'Failed to load history');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('history-list').innerHTML = 
            `<div class="error">Error loading history: ${error.message}</div>`;
    }
}

// Display history list
function displayHistory(notes) {
    const historyList = document.getElementById('history-list');
    const emptyState = document.getElementById('empty-state');
    const noteDetail = document.getElementById('note-detail');
    
    // Get active filter
    const activeFilter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
    
    // Filter notes
    const filteredNotes = activeFilter === 'all' 
        ? notes 
        : notes.filter(note => note.type === activeFilter);
    
    // Hide detail view
    noteDetail.classList.remove('show');
    
    if (filteredNotes.length === 0) {
        historyList.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    historyList.style.display = 'grid';
    emptyState.style.display = 'none';
    
    historyList.innerHTML = filteredNotes.map(note => `
        <div class="note-card ${note.type}" onclick="showNoteDetail('${note.id}')">
            <div class="note-header">
                <div class="note-title">${escapeHtml(note.title)}</div>
                <span class="note-type ${note.type}">${note.type === 'youtube' ? 'YouTube' : 'Meet'}</span>
            </div>
            <div class="note-date">${formatDate(note.timestamp)}</div>
            <div class="note-preview">${escapeHtml(note.content.substring(0, 200).replace(/#{1,6}\s+/g, '').replace(/\*\*/g, '').replace(/\*/g, ''))}...</div>
        </div>
    `).join('');
}

// Show note detail
async function showNoteDetail(noteId) {
    try {
        const response = await fetch(`${API_BASE_URL}/notes/${noteId}`);
        const data = await response.json();
        
        if (response.ok && data.note) {
            const note = data.note;
            const detailContent = document.getElementById('detail-content');
            
            // Render markdown content
            let renderedContent;
            if (typeof marked !== 'undefined') {
                renderedContent = marked.parse(note.content);
            } else {
                renderedContent = escapeHtml(note.content);
            }
            
            detailContent.innerHTML = `
                <div class="note-card ${note.type}">
                    <div class="note-header">
                        <div class="note-title">${escapeHtml(note.title)}</div>
                        <span class="note-type ${note.type}">${note.type === 'youtube' ? 'YouTube' : 'Meet'}</span>
                    </div>
                    <div class="note-date">${formatDate(note.timestamp)}</div>
                    <div class="notes-content" style="margin-top: 20px;">${renderedContent}</div>
                </div>
            `;
            
            document.getElementById('history-list').style.display = 'none';
            document.getElementById('note-detail').classList.add('show');
        } else {
            throw new Error(data.error || 'Note not found');
        }
    } catch (error) {
        console.error('Error loading note detail:', error);
        alert(`Error loading note: ${error.message}`);
    }
}

// Back button
document.getElementById('back-btn').addEventListener('click', () => {
    document.getElementById('note-detail').classList.remove('show');
    loadHistory();
});

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadHistory();
    });
});

// Utility functions
function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make showNoteDetail available globally
window.showNoteDetail = showNoteDetail;

