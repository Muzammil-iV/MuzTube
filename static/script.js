let currentDownloadId = null;
let selectedFormat = null;
let progressInterval = null;

function setPlatform(platform) {
    document.getElementById('urlInput').placeholder = `Paste ${platform} URL...`;
    document.getElementById('urlInput').focus();
    showChips();
}

function clearInput() {
    document.getElementById('urlInput').value = '';
    document.getElementById('urlInput').focus();
}

function showChips() {
    // Re-show chips if hidden
}

async function fetchVideoInfo() {
    const url = document.getElementById('urlInput').value.trim();
    if (!url) return showError('Please enter a valid URL');

    hideAll();
    document.getElementById('loadingCard').style.display = 'block';

    try {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await response.json();
        document.getElementById('loadingCard').style.display = 'none';

        if (data.success) displayVideoInfo(data);
        else showError(data.error || 'Failed to fetch video info');
    } catch (error) {
        document.getElementById('loadingCard').style.display = 'none';
        showError('Network error. Please try again.');
    }
}

function displayVideoInfo(data) {
    document.getElementById('infoCard').style.display = 'block';
    document.getElementById('videoTitle').textContent = data.title;
    document.getElementById('thumbnail').src = data.thumbnail;
    document.getElementById('platform').textContent = data.platform;
    document.getElementById('uploader').textContent = `By ${data.uploader}`;

    const mins = Math.floor(data.duration / 60);
    const secs = data.duration % 60;
    document.getElementById('duration').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

    const qualityContainer = document.getElementById('qualityChips');
    qualityContainer.innerHTML = '';
    data.formats.forEach((format, index) => {
        const chip = document.createElement('button');
        chip.className = 'chip';
        chip.textContent = format.quality;
        if (format.filesize) chip.textContent += ` (${formatBytes(format.filesize)})`;
        chip.onclick = () => selectQuality(format, chip);
        if (index === 0) { chip.classList.add('selected'); selectedFormat = format.format_id; }
        qualityContainer.appendChild(chip);
    });
    document.getElementById('infoCard').scrollIntoView({ behavior: 'smooth' });
}

function selectQuality(format, chip) {
    selectedFormat = format.format_id;
    document.querySelectorAll('#qualityChips .chip').forEach(c => c.classList.remove('selected'));
    chip.classList.add('selected');
}

async function startDownload() {
    const url = document.getElementById('urlInput').value.trim();
    if (!url) return showError('Please enter a URL first');

    hideAll();
    document.getElementById('progressCard').style.display = 'block';
    document.getElementById('saveBtn').style.display = 'none';
    document.getElementById('progressStatus').textContent = 'Starting download...';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressPercent').textContent = '0%';
    document.getElementById('downloadSpeed').textContent = '';
    document.getElementById('eta').textContent = '';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, format_id: selectedFormat })
        });
        const data = await response.json();
        if (data.success) {
            currentDownloadId = data.download_id;
            startProgressTracking();
        } else showError(data.error || 'Download failed');
    } catch (error) {
        showError('Network error during download');
    }
}

function startProgressTracking() {
    if (progressInterval) clearInterval(progressInterval);
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/progress/${currentDownloadId}`);
            const data = await response.json();
            updateProgress(data);
            if (data.status === 'completed') {
                clearInterval(progressInterval);
                onDownloadComplete();
            } else if (data.status === 'error') {
                clearInterval(progressInterval);
                showError(data.error || 'Download failed');
            }
        } catch (error) {
            console.error('Progress check failed:', error);
        }
    }, 300);
}

function updateProgress(data) {
    document.getElementById('progressBar').style.width = data.progress + '%';
    document.getElementById('progressPercent').textContent = Math.round(data.progress) + '%';
    document.getElementById('progressStatus').textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1) + '...';
    if (data.speed) document.getElementById('downloadSpeed').textContent = data.speed;
    if (data.eta) document.getElementById('eta').textContent = data.eta;
}

function onDownloadComplete() {
    document.getElementById('progressBar').style.width = '100%';
    document.getElementById('progressPercent').textContent = '100%';
    document.getElementById('progressStatus').textContent = '✅ Download Complete!';
    document.getElementById('saveBtn').style.display = 'inline-flex';
}

function saveFile() {
    if (currentDownloadId) window.location.href = `/api/download-file/${currentDownloadId}`;
}

function showError(message) {
    hideAll();
    document.getElementById('errorText').textContent = message;
    document.getElementById('errorCard').style.display = 'flex';
    setTimeout(() => document.getElementById('errorCard').style.display = 'none', 5000);
}

function hideAll() {
    document.getElementById('loadingCard').style.display = 'none';
    document.getElementById('infoCard').style.display = 'none';
    document.getElementById('progressCard').style.display = 'none';
    document.getElementById('errorCard').style.display = 'none';
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    return parseFloat((bytes / Math.pow(k, Math.floor(Math.log(bytes) / Math.log(k)))).toFixed(2)) + ' ' + sizes[Math.floor(Math.log(bytes) / Math.log(k))];
}

document.getElementById('urlInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') fetchVideoInfo();
});
