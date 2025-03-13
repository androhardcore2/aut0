// Global variables
let generatedText = '';
let videoPath = '';
let audioPath = '';
let originalText = '';
let selectedOrientation = 'landscape';
let currentPage = 1;
let totalResults = 0;
let currentQuery = '';

// Utility Functions
function showError(message, container) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle mr-2"></i>${message}`;
    container.insertBefore(errorDiv, container.firstChild);
    setTimeout(() => errorDiv.remove(), 5000);
}

function showSuccess(message, container) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${message}`;
    container.insertBefore(successDiv, container.firstChild);
    setTimeout(() => successDiv.remove(), 5000);
}

function setLoading(button, isLoading) {
    if (isLoading) {
        const originalContent = button.innerHTML;
        button.setAttribute('data-original-content', originalContent);
        button.innerHTML = `
            <svg class="loading-spinner w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
        `;
        button.disabled = true;
        button.classList.add('opacity-75', 'cursor-not-allowed');
    } else {
        const originalContent = button.getAttribute('data-original-content');
        button.innerHTML = originalContent;
        button.disabled = false;
        button.classList.remove('opacity-75', 'cursor-not-allowed');
    }
}

function enableStep(stepNumber) {
    document.getElementById(`step${stepNumber}`).classList.remove('step-disabled');
    document.getElementById(`step${stepNumber}`).classList.add('step-enabled');
}

// Text Generation Functions
function usePrompt(prompt) {
    document.getElementById('prompt').value = prompt;
    updateCharCount();
}

function updateCharCount() {
    const prompt = document.getElementById('prompt').value;
    document.getElementById('charCount').textContent = prompt.length;
}

function editText() {
    const textDiv = document.getElementById('generatedText');
    originalText = textDiv.textContent;
    textDiv.contentEditable = true;
    textDiv.classList.add('edit-mode');
    document.getElementById('editBtn').classList.add('hidden');
    document.getElementById('saveBtn').classList.remove('hidden');
    document.getElementById('cancelBtn').classList.remove('hidden');
}

function saveText() {
    const textDiv = document.getElementById('generatedText');
    generatedText = textDiv.textContent;
    textDiv.contentEditable = false;
    textDiv.classList.remove('edit-mode');
    document.getElementById('editBtn').classList.remove('hidden');
    document.getElementById('saveBtn').classList.add('hidden');
    document.getElementById('cancelBtn').classList.add('hidden');
}

function cancelEdit() {
    const textDiv = document.getElementById('generatedText');
    textDiv.textContent = originalText;
    textDiv.contentEditable = false;
    textDiv.classList.remove('edit-mode');
    document.getElementById('editBtn').classList.remove('hidden');
    document.getElementById('saveBtn').classList.add('hidden');
    document.getElementById('cancelBtn').classList.add('hidden');
}

async function generateText(button) {
    const prompt = document.getElementById('prompt').value;
    if (!prompt) {
        showError('Please enter a prompt or select a quick prompt', button.parentElement);
        return;
    }

    if (prompt.length > 500) {
        showError('Prompt is too long (max 500 characters)', button.parentElement);
        return;
    }

    try {
        setLoading(button, true);
        const response = await fetch('/generate-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to generate text');
        }

        generatedText = data.text;
        const container = document.getElementById('generatedTextContainer');
        const textDiv = document.getElementById('generatedText');
        textDiv.textContent = data.text;
        container.classList.remove('hidden');
        container.classList.add('fade-in');
        document.getElementById('regenerateBtn').classList.remove('hidden');
        enableStep(2);
        
        showSuccess('Text generated successfully', button.parentElement);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to generate text', button.parentElement);
    } finally {
        setLoading(button, false);
    }
}

async function regenerateText(button) {
    const prompt = document.getElementById('prompt').value;
    if (!prompt) {
        showError('Please enter a prompt or select a quick prompt', button.parentElement);
        return;
    }
    await generateText(button);
}

// Video Search Functions
function selectOrientation(orientation) {
    selectedOrientation = orientation;
    document.getElementById('landscape-option').classList.toggle('orientation-selected', orientation === 'landscape');
    document.getElementById('portrait-option').classList.toggle('orientation-selected', orientation === 'portrait');
    const videoPreview = document.getElementById('videoPreview');
    videoPreview.classList.add('hidden');
    videoPath = '';
}

async function searchVideo(button, page = 1) {
    const query = document.getElementById('videoQuery').value;
    if (!query) {
        showError('Please enter search keywords', button.parentElement);
        return;
    }

    currentQuery = query;
    currentPage = page;

    try {
        setLoading(button, true);
        const response = await fetch('/download-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query,
                orientation: selectedOrientation,
                page: currentPage
            })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to search videos');
        }

        // Update video grid
        const videoGrid = document.getElementById('videoGrid');
        videoGrid.innerHTML = '';
        
        data.videos.forEach(video => {
            const videoCard = document.createElement('div');
            videoCard.className = 'relative group cursor-pointer rounded-lg overflow-hidden';
            videoCard.innerHTML = `
                <img src="${video.preview}" alt="Video thumbnail" class="w-full h-48 object-cover">
                <div class="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <button onclick="selectVideo('${video.url}')" class="bg-indigo-600 text-white px-4 py-2 rounded-lg">
                        <i class="fas fa-check mr-2"></i>Select
                    </button>
                </div>
                <div class="absolute bottom-0 left-0 right-0 p-2 bg-black bg-opacity-50 text-white text-sm">
                    ${video.width}x${video.height} • ${video.duration}s
                </div>
            `;
            videoGrid.appendChild(videoCard);
        });

        // Update pagination
        totalResults = data.total_results;
        const totalPages = Math.ceil(totalResults / data.per_page);
        
        document.getElementById('pagination').classList.remove('hidden');
        document.getElementById('videoGrid').classList.remove('hidden');
        document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
        document.getElementById('prevBtn').disabled = currentPage === 1;
        document.getElementById('nextBtn').disabled = currentPage === totalPages;
        
        showSuccess('Videos found', button.parentElement);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to search videos', button.parentElement);
    } finally {
        setLoading(button, false);
    }
}

async function selectVideo(url) {
    try {
        const response = await fetch('/select-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to select video');
        }

        videoPath = data.path;
        const preview = document.getElementById('videoPreview');
        const player = document.getElementById('previewPlayer');
        player.src = `/download/${data.path.split('/').pop()}`;
        preview.classList.remove('hidden');
        preview.classList.add('fade-in');
        enableStep(3);
        
        showSuccess('Video selected successfully', preview);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to select video', document.getElementById('videoGrid'));
    }
}

function previousPage() {
    if (currentPage > 1) {
        searchVideo(document.querySelector('#step2 button'), currentPage - 1);
    }
}

function nextPage() {
    const totalPages = Math.ceil(totalResults / 10);
    if (currentPage < totalPages) {
        searchVideo(document.querySelector('#step2 button'), currentPage + 1);
    }
}

// Speech Generation Functions
async function generateSpeech(button) {
    if (!generatedText) {
        showError('Please generate text first', button.parentElement);
        return;
    }

    try {
        setLoading(button, true);
        const response = await fetch('/generate-speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: generatedText })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to generate speech');
        }

        audioPath = data.path;
        const preview = document.getElementById('audioPreview');
        const audio = document.getElementById('previewAudio');
        audio.src = `/download/${data.path.split('/').pop()}`;
        preview.classList.remove('hidden');
        preview.classList.add('fade-in');
        enableStep(4);
        enableStep(5);
        
        showSuccess('Speech generated successfully', button.parentElement);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to generate speech', button.parentElement);
    } finally {
        setLoading(button, false);
    }
}

// Video Creation Functions
async function createVideo(button) {
    if (!videoPath || !audioPath) {
        showError('Please ensure you have both video and audio ready', button.parentElement);
        return;
    }

    const useBackgroundMusic = document.getElementById('useBackgroundMusic').checked;
    const bgVolume = document.getElementById('bgMusicVolume').value / 100;

    try {
        setLoading(button, true);
        const response = await fetch('/create-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_path: videoPath,
                audio_path: audioPath,
                text_content: generatedText,
                background_music: useBackgroundMusic ? 'yes' : 'no',
                background_volume: bgVolume,
                orientation: selectedOrientation
            })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to create video');
        }

        const finalDiv = document.getElementById('finalVideo');
        const player = document.getElementById('finalPlayer');
        const downloadLink = document.getElementById('downloadLink');
        const filename = data.path.split('/').pop();
        
        player.src = `/download/${filename}`;
        downloadLink.href = `/download/${filename}`;
        finalDiv.classList.remove('hidden');
        finalDiv.classList.add('fade-in');
        
        showSuccess('Video created successfully', button.parentElement);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to create video', button.parentElement);
    } finally {
        setLoading(button, false);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Character count
    document.getElementById('prompt').addEventListener('input', updateCharCount);
    
    // Volume slider
    document.getElementById('bgMusicVolume').addEventListener('input', function(e) {
        document.getElementById('volumeValue').textContent = e.target.value + '%';
    });
});
