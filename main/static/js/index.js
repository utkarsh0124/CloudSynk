document.addEventListener('DOMContentLoaded', function() {
    // File icon mapping based on extensions
    function getFileIcon(filename) {
        // Remove .zip suffix if present (files are stored as filename.ext.zip)
        let cleanFilename = filename;
        if (filename.toLowerCase().endsWith('.zip')) {
            cleanFilename = filename.slice(0, -4); // Remove last 4 characters (.zip)
        }
        
        const extension = cleanFilename.toLowerCase().split('.').pop();
        const iconMappings = {
            // Documents
            'pdf': 'fas fa-file-pdf text-red-500',
            'doc': 'fas fa-file-word text-blue-600',
            'docx': 'fas fa-file-word text-blue-600',
            'txt': 'fas fa-file-alt text-gray-600',
            'rtf': 'fas fa-file-alt text-gray-600',
            
            // Spreadsheets
            'xls': 'fas fa-file-excel text-green-600',
            'xlsx': 'fas fa-file-excel text-green-600',
            'csv': 'fas fa-file-csv text-green-500',
            
            // Presentations
            'ppt': 'fas fa-file-powerpoint text-orange-600',
            'pptx': 'fas fa-file-powerpoint text-orange-600',
            
            // Images
            'jpg': 'fas fa-file-image text-purple-500',
            'jpeg': 'fas fa-file-image text-purple-500',
            'png': 'fas fa-file-image text-purple-500',
            'gif': 'fas fa-file-image text-purple-500',
            'bmp': 'fas fa-file-image text-purple-500',
            'svg': 'fas fa-file-image text-purple-500',
            'webp': 'fas fa-file-image text-purple-500',
            
            // Audio
            'mp3': 'fas fa-file-audio text-green-500',
            'wav': 'fas fa-file-audio text-green-500',
            'flac': 'fas fa-file-audio text-green-500',
            'aac': 'fas fa-file-audio text-green-500',
            'ogg': 'fas fa-file-audio text-green-500',
            
            // Video
            'mp4': 'fas fa-file-video text-red-600',
            'avi': 'fas fa-file-video text-red-600',
            'mkv': 'fas fa-file-video text-red-600',
            'mov': 'fas fa-file-video text-red-600',
            'wmv': 'fas fa-file-video text-red-600',
            'webm': 'fas fa-file-video text-red-600',
            
            // Archives
            'zip': 'fas fa-file-archive text-yellow-600',
            'rar': 'fas fa-file-archive text-yellow-600',
            '7z': 'fas fa-file-archive text-yellow-600',
            'tar': 'fas fa-file-archive text-yellow-600',
            'gz': 'fas fa-file-archive text-yellow-600',
            
            // Code
            'js': 'fas fa-file-code text-yellow-500',
            'html': 'fas fa-file-code text-orange-500',
            'css': 'fas fa-file-code text-blue-400',
            'py': 'fas fa-file-code text-blue-500',
            'java': 'fas fa-file-code text-red-500',
            'cpp': 'fas fa-file-code text-blue-700',
            'c': 'fas fa-file-code text-blue-700',
            'php': 'fas fa-file-code text-purple-600',
            'rb': 'fas fa-file-code text-red-600',
            'go': 'fas fa-file-code text-blue-400',
            'rs': 'fas fa-file-code text-orange-600',
            'json': 'fas fa-file-code text-green-600',
            'xml': 'fas fa-file-code text-orange-400',
            'yml': 'fas fa-file-code text-gray-600',
            'yaml': 'fas fa-file-code text-gray-600',
            
            // Default
            'default': 'fas fa-file-alt text-gray-500'
        };
        
        return iconMappings[extension] || iconMappings['default'];
    }
    
    // Initialize file icons
    function initializeFileIcons() {
        document.querySelectorAll('.file-icon').forEach(function(iconElement) {
            const filename = iconElement.getAttribute('data-filename');
            if (filename) {
                const iconClasses = getFileIcon(filename);
                iconElement.className = `file-icon text-2xl mr-3 ${iconClasses}`;
                
                // For list view, use smaller icon
                if (iconElement.classList.contains('text-lg')) {
                    iconElement.className = `file-icon text-lg mr-3 ${iconClasses}`;
                }
            }
        });
    }
    
    // Initialize icons on page load
    initializeFileIcons();

    const fileInput = document.getElementById('file-upload');
    const uploadForm = document.getElementById('upload-form');

    // prevent native form submit
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) { e.preventDefault(); });
    }

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : null;
    }

    function uploadFile(file, fileName) {
        if (!file) return;
        const csrftoken = getCsrfToken();
        if (fileInput) fileInput.disabled = true;

        const fd = new FormData();
        fd.append('blob_file', file);
        fd.append('file_name', fileName);

        fetch('/addFile/', {
            method: 'POST',
            body: fd,
            headers: csrftoken ? { 'X-CSRFToken': csrftoken } : {},
            credentials: 'same-origin'
        })
        .then(async res => {
            if (res.ok) { window.location = '/'; return; }
            const data = await res.json().catch(()=>null);
            alert(data?.error || 'Upload failed');
        })
        .catch(err => { console.error('Upload error', err); alert('Upload error'); })
        .finally(() => { if (fileInput) fileInput.disabled = false; });
    }

    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const f = e.target.files[0];
            if (!f) return;
            //zip file before upload
            const zip = new JSZip();
            zip.file(f.name, f);
            const content = await zip.generateAsync({ type: "blob" });
            uploadFile(content, f.name + ".zip");
        });
    }

    // Delete file functionality using modal confirmation
    let currentDeleteBtn = null;
    let currentBlobId = null;
    
    $(document).on('click', '.file-delete-btn', function(e) {
        e.preventDefault();
        currentDeleteBtn = $(this);
        currentBlobId = currentDeleteBtn.data('blob-id');
        
        if (!currentBlobId) {
            alert('File ID not found');
            return;
        }
        
        // Get filename for display in modal (try different data attributes)
        const fileName = currentDeleteBtn.data('blob-name') || 
                        currentDeleteBtn.closest('.file-item-tile, .file-item-list').find('.truncate-name').attr('title') ||
                        currentDeleteBtn.closest('.file-item-tile, .file-item-list').find('.truncate-name').text() ||
                        'this file';
        
        // Set filename in modal and show it
        $('#delete-filename').text(fileName);
        $('#delete-modal').removeClass('hidden');
    });
    
    // Delete modal event handlers
    $('#cancel-delete').on('click', function() {
        $('#delete-modal').addClass('hidden');
        currentDeleteBtn = null;
        currentBlobId = null;
    });
    
    $('#confirm-delete').on('click', function() {
        if (!currentDeleteBtn || !currentBlobId) {
            $('#delete-modal').addClass('hidden');
            return;
        }
        
        const csrftoken = getCsrfToken();
        
        // Show loading state on confirm button
        $(this).html('<i class="fas fa-spinner fa-spin mr-1"></i>Deleting...');
        $(this).prop('disabled', true);
        
        // For icon-only buttons, add status text like download functionality
        let statusContainer = currentDeleteBtn.siblings('.delete-status');
        if (statusContainer.length === 0) {
            statusContainer = $('<span class="delete-status text-xs ml-2 text-red-600"></span>');
            currentDeleteBtn.after(statusContainer);
        }
        statusContainer.text('Deleting...');
        currentDeleteBtn.prop('disabled', true).addClass('opacity-50');
        
        fetch(`/deleteFile/${currentBlobId}/`, {
            method: 'POST',
            headers: csrftoken ? { 'X-CSRFToken': csrftoken } : {},
            credentials: 'same-origin'
        })
        .then(res => {
            if (res.ok) { 
                statusContainer.text('Deleted!').removeClass('text-red-600').addClass('text-green-600');
                setTimeout(() => {
                    window.location = '/'; 
                }, 1000);
                return; 
            }
            throw new Error('Delete failed');
        })
        .catch(err => { 
            console.error('Delete error', err); 
            statusContainer.text('Delete failed').removeClass('text-green-600').addClass('text-red-600');
            setTimeout(() => {
                statusContainer.remove();
                currentDeleteBtn.prop('disabled', false).removeClass('opacity-50');
            }, 2000);
        })
        .finally(() => {
            // Hide modal and reset confirm button
            $('#delete-modal').addClass('hidden');
            $('#confirm-delete').html('Yes, Delete').prop('disabled', false);
            currentDeleteBtn = null;
            currentBlobId = null;
        });
    });

    // Enhanced download file functionality with resume capability
    $(document).on('click', '.file-download-btn', function(e) {
        e.preventDefault();
        const downloadBtn = $(this);
        const blobId = downloadBtn.data('blob-id');
        const blobName = downloadBtn.data('blob-name');
        const blobSize = downloadBtn.data('blob-size');
        
        if (!blobId) {
            alert('File ID not found');
            return;
        }
        
        downloadFileWithResume(blobId, blobName, blobSize, downloadBtn);
    });

    async function downloadFileWithResume(blobId, fileName, blobSize, downloadBtn) {
        const downloadId = `download_${blobId}`;
        let resumeData = getResumeData(downloadId);
        
        try {
            // Add status text container next to button if it doesn't exist
            let statusContainer = downloadBtn.siblings('.download-status');
            if (statusContainer.length === 0) {
                statusContainer = $('<span class="download-status text-xs ml-2"></span>');
                downloadBtn.after(statusContainer);
            }
            
            statusContainer.text('Preparing download...').removeClass('text-green-600 text-red-600').addClass('text-blue-600');
            downloadBtn.prop('disabled', true).addClass('opacity-50');
            
            let downloadedBytes = resumeData ? resumeData.downloadedBytes : 0;
            let chunks = resumeData ? resumeData.chunks : [];
            
            // If already completed
            if (downloadedBytes >= blobSize && chunks.length > 0) {
                downloadCompleted(chunks, fileName, downloadBtn, statusContainer);
                return;
            }
            
            // For small files, use simple form submission
            if (blobSize < 5 * 1024 * 1024) { // Less than 5MB
                simpleDownload(blobId, downloadBtn, statusContainer);
                return;
            }
            
            // Download remaining chunks for large files
            const chunkSize = 2 * 1024 * 1024; // 2MB chunks
            const totalChunks = Math.ceil(blobSize / chunkSize);
            const startChunk = Math.floor(downloadedBytes / chunkSize);
            
            for (let i = startChunk; i < totalChunks; i++) {
                const start = i * chunkSize;
                const end = Math.min(start + chunkSize - 1, blobSize - 1);
                
                try {
                    const chunk = await downloadChunk(blobId, start, end);
                    chunks[i] = chunk;
                    downloadedBytes = end + 1;
                    
                    // Save progress
                    saveResumeData(downloadId, { downloadedBytes, chunks: chunks.slice() });
                    
                    // Update progress
                    const progress = Math.round((downloadedBytes / blobSize) * 100);
                    statusContainer.text(`Downloading... ${progress}%`);
                    
                } catch (error) {
                    console.error(`Failed to download chunk ${i}:`, error);
                    // Save current progress and show resume option
                    saveResumeData(downloadId, { downloadedBytes, chunks: chunks.slice() });
                    showResumeOption(blobId, fileName, downloadBtn, statusContainer);
                    return;
                }
            }
            
            // Download completed
            downloadCompleted(chunks, fileName, downloadBtn, statusContainer);
            clearResumeData(downloadId);
            
        } catch (error) {
            console.error('Download failed:', error);
            let statusContainer = downloadBtn.siblings('.download-status');
            if (statusContainer.length === 0) {
                statusContainer = $('<span class="download-status text-xs ml-2"></span>');
                downloadBtn.after(statusContainer);
            }
            statusContainer.text('Download failed').removeClass('text-blue-600 text-green-600').addClass('text-red-600');
            setTimeout(() => {
                statusContainer.remove();
                downloadBtn.prop('disabled', false).removeClass('opacity-50');
            }, 2000);
        }
    }

    function simpleDownload(blobId, downloadBtn, statusContainer) {
        const csrftoken = getCsrfToken();
        
        // Create a form and submit it to trigger file download
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/downloadFile/${blobId}/`;
        form.style.display = 'none';
        
        // Add CSRF token
        if (csrftoken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrftoken;
            form.appendChild(csrfInput);
        }
        
        document.body.appendChild(form);
        
        // Show downloading state
        statusContainer.text('Downloading...').removeClass('text-green-600 text-red-600').addClass('text-blue-600');
        
        // Submit the form to trigger download
        form.submit();
        
        // Clean up and reset button state
        document.body.removeChild(form);
        
        // Show success state briefly, then reset
        setTimeout(() => {
            statusContainer.text('Downloaded!').removeClass('text-blue-600 text-red-600').addClass('text-green-600');
            setTimeout(() => {
                statusContainer.remove();
                downloadBtn.prop('disabled', false).removeClass('opacity-50');
            }, 1500);
        }, 500);
    }

    async function downloadChunk(blobId, start, end) {
        const response = await fetch(`/downloadFile/${blobId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Range': `bytes=${start}-${end}`,
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.arrayBuffer();
    }

    function saveResumeData(downloadId, data) {
        try {
            // Store in localStorage for persistence across page reloads
            const serializedData = {
                downloadedBytes: data.downloadedBytes,
                chunksCount: data.chunks.length,
                timestamp: Date.now()
            };
            localStorage.setItem(downloadId, JSON.stringify(serializedData));
        } catch (error) {
            console.warn('Failed to save resume data:', error);
        }
    }

    function getResumeData(downloadId) {
        try {
            const data = localStorage.getItem(downloadId);
            if (data) {
                const parsed = JSON.parse(data);
                // Check if data is recent (within 24 hours)
                if (Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
                    return {
                        downloadedBytes: parsed.downloadedBytes,
                        chunks: new Array(parsed.chunksCount)
                    };
                }
            }
        } catch (error) {
            console.warn('Failed to get resume data:', error);
        }
        return null;
    }

    function clearResumeData(downloadId) {
        try {
            localStorage.removeItem(downloadId);
        } catch (error) {
            console.warn('Failed to clear resume data:', error);
        }
    }

    function showResumeOption(blobId, fileName, downloadBtn, statusContainer) {
        statusContainer.text('Click to resume download').removeClass('text-blue-600 text-green-600').addClass('text-orange-600');
        downloadBtn.prop('disabled', false).removeClass('opacity-50');
        
        // Add resume handler
        downloadBtn.off('click.resume').on('click.resume', function(e) {
            e.preventDefault();
            downloadBtn.off('click.resume');
            const blobSize = downloadBtn.data('blob-size');
            downloadFileWithResume(blobId, fileName, blobSize, downloadBtn);
        });
    }

    function downloadCompleted(chunks, fileName, downloadBtn, statusContainer) {
        try {
            // Combine all chunks into a single blob
            const combinedBlob = new Blob(chunks.filter(chunk => chunk));
            triggerDownload(combinedBlob, fileName);
            
            statusContainer.text('Downloaded!').removeClass('text-blue-600 text-red-600').addClass('text-green-600');
            setTimeout(() => {
                statusContainer.remove();
                downloadBtn.prop('disabled', false).removeClass('opacity-50');
            }, 2000);
        } catch (error) {
            console.error('Failed to complete download:', error);
            statusContainer.text('Download error').removeClass('text-blue-600 text-green-600').addClass('text-red-600');
            setTimeout(() => {
                statusContainer.remove();
                downloadBtn.prop('disabled', false).removeClass('opacity-50');
            }, 2000);
        }
    }

    function triggerDownload(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    // Dashboard behaviors moved from sample.html
    // Dropdown menu functionality
    $('#dropdown-menu').hide();
    $('#menu-toggle').on('click', function(e) {
        e.stopPropagation();
        $('#dropdown-menu').toggle();
    });
    $(document).on('click', function() {
        $('#dropdown-menu').hide();
    });
    $('#dropdown-menu').on('click', function(e) {
        e.stopPropagation();
    });

    // Deactivate modal functionality
    $('#deactivate-btn').on('click', function(e) {
        e.preventDefault();
        $('#deactivate-modal').removeClass('hidden');
    });
    $('#cancel-deactivate').on('click', function() {
        $('#deactivate-modal').addClass('hidden');
    });
    $('#confirm-deactivate').on('click', function() {
        // Find the deactivate form and submit it
        const form = $('form[action$="deactivate/"]');
        if (form.length > 0) {
            const csrftoken = getCsrfToken();
            
            // Show loading state
            $(this).html('<i class="fas fa-spinner fa-spin mr-1"></i>Deactivating...');
            $(this).prop('disabled', true);
            
            // Submit via AJAX to handle the response properly
            fetch(form.attr('action'), {
                method: 'POST',
                headers: csrftoken ? { 'X-CSRFToken': csrftoken } : {},
                credentials: 'same-origin'
            })
            .then(async res => {
                if (res.ok) {
                    // Successful deactivation - redirect to login
                    window.location = '/login/';
                    return;
                }
                const data = await res.json().catch(() => null);
                alert(data?.error || 'Deactivation failed');
            })
            .catch(err => {
                console.error('Deactivation error', err);
                alert('Deactivation error');
            })
            .finally(() => {
                // Hide modal and reset button
                $('#deactivate-modal').addClass('hidden');
                $(this).html('Yes, Deactivate');
                $(this).prop('disabled', false);
            });
        } else {
            console.error('Deactivate form not found');
            alert('Error: Deactivate form not found');
        }
    });

    // View toggle functionality with localStorage persistence
    function setViewMode(mode) {
        localStorage.setItem('cloudsynk-view-mode', mode);
        
        if (mode === 'tile') {
            // Update button states
            $('#tile-view-btn').removeClass('bg-gray-200 text-gray-700').addClass('bg-blue-500 text-white');
            $('#list-view-btn').removeClass('bg-blue-500 text-white').addClass('bg-gray-200 text-gray-700');
            
            // Update layout
            $('#file-list-container')
                .removeClass('flex flex-col')
                .addClass('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6');
            $('.file-item-tile').show();
            $('.file-item-list').hide();
        } else {
            // List view (default)
            // Update button states
            $('#list-view-btn').removeClass('bg-gray-200 text-gray-700').addClass('bg-blue-500 text-white');
            $('#tile-view-btn').removeClass('bg-blue-500 text-white').addClass('bg-gray-200 text-gray-700');
            
            // Update layout
            $('#file-list-container')
                .removeClass('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6')
                .addClass('flex flex-col');
            $('.file-item-tile').hide();
            $('.file-item-list').show();
        }
    }
    
    // Load saved view mode on page load
    function initializeViewMode() {
        const savedMode = localStorage.getItem('cloudsynk-view-mode');
        // Default to list view if no preference saved
        const viewMode = savedMode || 'list';
        setViewMode(viewMode);
    }
    
    // Initialize view mode based on saved preference
    initializeViewMode();
    
    // View toggle event handlers
    $('#tile-view-btn').on('click', function() {
        setViewMode('tile');
    });
    
    $('#list-view-btn').on('click', function() {
        setViewMode('list');
    });

    // Storage progress bar calculation
    (function() {
        var $container = $('#storage-container');
        if ($container.length) {
            var used = parseFloat($container.attr('data-used')) || 0;
            var quota = parseFloat($container.attr('data-quota')) || 0;
            var percent = quota > 0 ? (used / quota) * 100 : 0;
            var percentClamped = Math.min(Math.max(percent, 0), 100);
            $('#storage-bar').css('width', percentClamped.toFixed(2) + '%');
            $('#storage-bar').attr('title', 'Used ' + percentClamped.toFixed(2) + '% of total');
            $('#storage-bar').attr('role', 'progressbar');
            $('#storage-bar').attr('aria-valuemin', '0');
            $('#storage-bar').attr('aria-valuemax', '100');
            $('#storage-bar').attr('aria-valuenow', Math.round(percentClamped));
        }
    })();

    // Mobile nav toggle
    // Mobile nav toggle button handler
    $('#nav-toggle-btn').on('click', function(e) {
        e.stopPropagation();
        $('#side-nav').toggleClass('-translate-x-full');
    });
    // Close side-nav when clicking outside on mobile
    $(document).on('click', function(e) {
        if (window.innerWidth < 640) { // only on mobile
            const $nav = $('#side-nav');
            if ($nav.hasClass('-translate-x-full')) return; // nav closed
            if (!$(e.target).closest('#side-nav, #nav-toggle-btn').length) {
                $nav.addClass('-translate-x-full');
            }
        }
    });
});