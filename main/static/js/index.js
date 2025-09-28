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
            
            // Check if it's a quota-related error
            if (data?.error && isQuotaError(data.error)) {
                showQuotaExceededModal(file, data.error);
            } else if (data?.error && isDuplicateFilenameError(data.error)) {
                showDuplicateFilenameModal(file, data.error);
            } else {
                alert(data?.error || 'Upload failed');
            }
        })
        .catch(err => { console.error('Upload error', err); alert('Upload error'); })
        .finally(() => { if (fileInput) fileInput.disabled = false; });
    }

    // Function to check if error is duplicate filename related
    function isDuplicateFilenameError(errorMessage) {
        const duplicateKeywords = [
            'blob name already exists',
            'file with this name already exists',
            'filename already exists',
            'duplicate filename',
            'name already exists',
            'please use a different file'
        ];
        return duplicateKeywords.some(keyword => 
            errorMessage.toLowerCase().includes(keyword)
        );
    }

    // Function to check if error is quota-related
    function isQuotaError(errorMessage) {
        const quotaKeywords = [
            'storage quota exceeded',
            'quota exceeded',
            'not enough storage',
            'storage limit',
            'storage space',
            'upgrade your subscription'
        ];
        return quotaKeywords.some(keyword => 
            errorMessage.toLowerCase().includes(keyword)
        );
    }

    // Function to show duplicate filename modal
    function showDuplicateFilenameModal(file, errorMessage) {
        // Update modal content
        $('#duplicate-error-message').text(errorMessage);
        $('#duplicate-file-name').text(file.name);
        $('#duplicate-file-size').text(formatFileSize(file.size));
        
        // Show the modal
        $('#duplicate-filename-modal').removeClass('hidden');
    }

    // Function to show quota exceeded modal
    function showQuotaExceededModal(file, errorMessage) {
        // Update modal content
        $('#quota-error-message').text(errorMessage);
        $('#quota-file-size').text(formatFileSize(file.size));
        
        // Show the modal
        $('#quota-exceeded-modal').removeClass('hidden');
    }

    // Helper function to format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const f = e.target.files[0];
            if (!f) return;
            
            // Use the new transfer manager for uploads
            if (window.transferManager) {
                const transferId = window.transferManager.addUpload(f);
                console.log(`📤 Added to transfer manager: ${f.name} (ID: ${transferId})`);
                
                // Track upload activity
                /* if (window.historyManager) {
                    window.historyManager.trackUpload(f.name, f.size, transferId);
                } */
                
                // Reset the file input
                fileInput.value = '';
                
                // Optionally show the transfer manager modal
                window.transferManager.showModal();
            } else {
                console.error('❌ Transfer manager not available');
                alert('Transfer manager not loaded. Please refresh the page.');
            }
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
                
                // Track delete activity
                if (window.historyManager) {
                    const fileName = currentDeleteBtn.data('blob-name') || 
                                    currentDeleteBtn.closest('.file-item-tile, .file-item-list').find('.truncate-name').attr('title') ||
                                    currentDeleteBtn.closest('.file-item-tile, .file-item-list').find('.truncate-name').text() ||
                                    'Unknown file';
                }
                
                // Update modal to show processing message
                $('#confirm-delete').html('<i class="fas fa-spinner fa-spin mr-1"></i>Deleting...').removeClass('bg-red-600 hover:bg-red-700').addClass('bg-blue-600 hover:bg-blue-700');
                
                // Update storage progress before page reload
                if (window.updateStorageProgress) {
                    // Trigger storage refresh (this will be handled by page reload anyway, but good practice)
                    setTimeout(() => {
                        window.location = '/'; 
                    }, 1000);
                } else {
                    setTimeout(() => {
                        window.location = '/'; 
                    }, 1000);
                }
                return; 
            }
            throw new Error('Delete failed');
        })
        .catch(err => { 
            console.error('Delete error', err); 
            statusContainer.text('Delete failed').removeClass('text-green-600').addClass('text-red-600');
            
            // Reset modal state on error
            $('#delete-modal').addClass('hidden');
            $('#confirm-delete').html('Yes, Delete').prop('disabled', false);
            
            setTimeout(() => {
                statusContainer.remove();
                if (currentDeleteBtn) {
                    currentDeleteBtn.prop('disabled', false).removeClass('opacity-50');
                }
            }, 2000);
            
            currentDeleteBtn = null;
            currentBlobId = null;
        });
    });

    // Enhanced download file functionality with modern transfer manager
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
        
        // Use the new transfer manager
        if (window.transferManager) {
            const transferId = window.transferManager.addDownload(blobId, blobName, blobSize);
            console.log(`📥 Added to transfer manager: ${blobName} (ID: ${transferId})`);
            
            // Track download activity
            /* if (window.historyManager) {
                window.historyManager.trackDownload(blobName, blobSize, transferId, blobId);
            } */
            
            // Show brief feedback
            const originalText = downloadBtn.find('span').text();
            downloadBtn.find('span').text('Added to queue');
            setTimeout(() => {
                downloadBtn.find('span').text(originalText);
            }, 1500);
            
            // The transfer manager modal is already shown by addDownload() with downloads tab
            // No need to call showModal() again here
        } else {
            console.error('❌ Transfer manager not available');
            alert('Transfer manager not loaded. Please refresh the page.');
        }
    });

    async function downloadFileWithResume(blobId, fileName, blobSize, downloadBtn) {
        console.log('🔽 downloadFileWithResume started for:', fileName, 'Size:', blobSize, 'ID:', blobId);
        const downloadId = `download_${blobId}`;
        let resumeData = getResumeData(downloadId);
        
        try {
            console.log('🔍 Resume data check:', resumeData ? 'Found' : 'None');
            
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
            
            console.log('📊 Download state - Downloaded:', downloadedBytes, 'Total:', blobSize, 'Chunks:', chunks.length);
            
            // If already completed
            if (downloadedBytes >= blobSize && chunks.length > 0) {
                console.log('✅ File already completed, triggering completion');
                downloadCompleted(chunks, fileName, downloadBtn, statusContainer);
                return;
            }
            
            // For small files, use simple form submission
            if (blobSize < 5 * 1024 * 1024) { // Less than 5MB
                console.log('📁 Small file detected, using simple download');
                simpleDownload(blobId, downloadBtn, statusContainer);
                return;
            }
            
            console.log('📦 Large file detected, using chunked download');
            
            // Download remaining chunks for large files
            const chunkSize = 2 * 1024 * 1024; // 2MB chunks
            const totalChunks = Math.ceil(blobSize / chunkSize);
            const startChunk = Math.floor(downloadedBytes / chunkSize);
            
            console.log('🔢 Chunked download - Total chunks:', totalChunks, 'Start chunk:', startChunk);
            
            for (let i = startChunk; i < totalChunks; i++) {
                const start = i * chunkSize;
                const end = Math.min(start + chunkSize - 1, blobSize - 1);
                
                console.log(`📦 Downloading chunk ${i + 1}/${totalChunks} (${start}-${end})`);
                
                try {
                    const chunk = await downloadChunk(blobId, start, end);
                    chunks[i] = chunk;
                    downloadedBytes = end + 1;
                    
                    // Save progress
                    saveResumeData(downloadId, { downloadedBytes, chunks: chunks.slice() });
                    
                    // Update progress
                    const progress = Math.round((downloadedBytes / blobSize) * 100);
                    statusContainer.text(`Downloading... ${progress}%`);
                    
                    // Update progress in downloads modal if item is currently downloading
                    updateDownloadProgress(blobId, progress);
                    
                } catch (error) {
                    console.error(`Failed to download chunk ${i}:`, error);
                    // Save current progress and show resume option
                    saveResumeData(downloadId, { downloadedBytes, chunks: chunks.slice() });
                    showResumeOption(blobId, fileName, downloadBtn, statusContainer);
                    return;
                }
            }
            
            // Download completed - update progress to 100% and mark as completed
            console.log('🎯 Download completed in regular flow for:', fileName);
            updateDownloadProgress(blobId, 100);
            updateDownloadStatus(blobId, 'completed');
            console.log('📞 Calling downloadCompleted function');
            downloadCompleted(chunks, fileName, downloadBtn, statusContainer);
            
            // Check if this is a queue download and notify the queue system
            if (currentDownload && currentDownload.id === blobId) {
                console.log('🎯 This is a queue download, updating queue status');
                currentDownload.status = 'completed';
                console.log('📝 Updated currentDownload.status to:', currentDownload.status);
                updateDownloadsModal();
                
                // Clear any timeout
                if (currentDownload.timeoutId) {
                    clearTimeout(currentDownload.timeoutId);
                    console.log('⏰ Cleared download timeout');
                }
                
                // Resolve the Promise for the queue system
                if (currentDownload.resolvePromise) {
                    console.log('✅ Resolving queue Promise');
                    currentDownload.resolvePromise();
                    // Clear the promise functions to prevent multiple calls
                    currentDownload.resolvePromise = null;
                    currentDownload.rejectPromise = null;
                }
                
                // Don't clear currentDownload here - let the queue system handle the timing
            }
            
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
        console.log('📄 simpleDownload called for ID:', blobId);
        const csrftoken = getCsrfToken();
        console.log('🔑 CSRF token:', csrftoken ? 'Found' : 'Missing');
        
        // Create a form and submit it to trigger file download
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/downloadFile/${blobId}/`;
        form.style.display = 'none';
        
        console.log('📋 Form created with action:', form.action);
        
        // Add CSRF token
        if (csrftoken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrftoken;
            form.appendChild(csrfInput);
            console.log('✅ CSRF token added to form');
        }
        
        document.body.appendChild(form);
        
        // Show downloading state
        statusContainer.text('Downloading...').removeClass('text-green-600 text-red-600').addClass('text-blue-600');
        
        console.log('🚀 Submitting form for simple download');
        
        // Submit the form to trigger download
        form.submit();
        
        console.log('✅ Form submitted, cleaning up');
        
        // Clean up and reset button state
        document.body.removeChild(form);
        
        // For small files, we can't detect completion directly, so simulate it
        // Since the form submission triggers immediate download, we'll assume success
        setTimeout(() => {
            console.log('🎯 Simulating completion for small file download');
            statusContainer.text('Downloaded!').removeClass('text-blue-600 text-red-600').addClass('text-green-600');
            
            // Trigger the completion callback for queue system
            // Create a dummy blob for the completion callback
            const dummyBlob = new Blob(['Small file downloaded via form'], { type: 'text/plain' });
            
            // Get the filename from currentDownload if it exists
            const fileName = currentDownload ? currentDownload.name : 'download';
            
            console.log('📞 Calling downloadCompleted for small file');
            downloadCompleted([dummyBlob], fileName, downloadBtn, statusContainer);
        }, 1000); // Give browser time to start the download
    }

    async function downloadChunk(blobId, start, end) {
        console.log(`🔽 downloadChunk called - ID: ${blobId}, Range: ${start}-${end}`);
        
        const response = await fetch(`/downloadFile/${blobId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Range': `bytes=${start}-${end}`,
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        console.log(`📡 Chunk response - Status: ${response.status}, OK: ${response.ok}`);
        
        if (!response.ok) {
            console.error(`❌ Chunk download failed - HTTP ${response.status}`);
            throw new Error(`HTTP ${response.status}`);
        }
        
        const arrayBuffer = await response.arrayBuffer();
        console.log(`✅ Chunk downloaded - Size: ${arrayBuffer.byteLength} bytes`);
        
        return arrayBuffer;
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
        try {
            console.log('🔽 Triggering download for:', filename, 'Size:', blob.size);
            
            // Check if this might be a large file that triggers save dialog
            if (blob.size > 50 * 1024 * 1024) { // 50MB
                console.log('📁 Large file detected, browser may ask for save location');
            }
            
            // Method 1: Direct download with forced attributes
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            // Set all possible attributes to force download
            a.href = url;
            a.download = filename;
            a.setAttribute('download', filename);
            a.style.display = 'none';
            a.style.position = 'absolute';
            a.style.left = '-9999px';
            
            // Add to DOM
            document.body.appendChild(a);
            
            // Method 2: Try programmatic click with user gesture context
            const mouseEvent = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true
            });
            
            // Dispatch the event immediately while we're in user gesture context
            a.dispatchEvent(mouseEvent);
            
            console.log('🔽 Download triggered - if browser asks for location, check browser settings');
            console.log('💡 To avoid save dialogs: Browser Settings > Downloads > Turn off "Ask where to save each file"');
            
            // Clean up
            setTimeout(() => {
                try {
                    window.URL.revokeObjectURL(url);
                    if (document.body.contains(a)) {
                        document.body.removeChild(a);
                    }
                } catch (cleanupError) {
                    console.warn('Cleanup error:', cleanupError);
                }
            }, 1000);
            
        } catch (error) {
            console.error('Download failed:', error);
            
            // Ultimate fallback - simple approach
            try {
                const url = window.URL.createObjectURL(blob);
                window.open(url, '_blank');
                setTimeout(() => window.URL.revokeObjectURL(url), 1000);
            } catch (fallbackError) {
                console.error('Fallback download also failed:', fallbackError);
                alert('Download failed. Please check your browser settings and try again.');
            }
        }
    }

    // Dashboard behaviors moved from sample.html
    // Dropdown menu functionality with smooth animations
    $(document).ready(function() {
        const $dropdown = $('#dropdown-menu');
        
        // Initialize dropdown as hidden
        $dropdown.hide().css({
            'transform': 'scale(0.095)',
            'opacity': '0',
            'transform-origin': 'top right'
        });
        
        function showDropdown() {
            $dropdown.show().css({
                'transform': 'scale(0.095)',
                'opacity': '0'
            }).animate({
                'opacity': '1'
            }, {
                duration: 0.01,
                easing: 'swing',
                step: function(now, fx) {
                    if (fx.prop === 'opacity') {
                        const scale = 0.95 + (now * 0.05); // Scale from 0.95 to 1.0
                        $(this).css('transform', `scale(${scale})`);
                    }
                }
            });
        }
        
        function hideDropdown() {
            $dropdown.animate({
                'opacity': '0'
            }, {
                duration: 0.01,
                easing: 'swing',
                step: function(now, fx) {
                    if (fx.prop === 'opacity') {
                        const scale = 0.95 + (now * 0.05); // Scale from current to 0.95
                        $(this).css('transform', `scale(${scale})`);
                    }
                },
                complete: function() {
                    $(this).hide();
                }
            });
        }
        
        $('#menu-toggle').on('click', function(e) {
            console.log('Menu toggle clicked - using smooth animation');
            e.stopPropagation();
            
            if ($dropdown.is(':visible') && $dropdown.css('opacity') == '1') {
                hideDropdown();
            } else {
                showDropdown();
            }
        });
        
        $(document).on('click', function() {
            if ($dropdown.is(':visible')) {
                hideDropdown();
            }
        });
        
        $('#dropdown-menu').on('click', function(e) {
            e.stopPropagation();
        });
    });
    
    // Deactivate modal functionality (triggered from settings modal)
    $('#cancel-deactivate').on('click', function() {
        $('#deactivate-modal').addClass('hidden');
    });
    $('#confirm-deactivate').on('click', function() {
        const csrftoken = getCsrfToken();
        
        // Show loading state
        $(this).html('<i class="fas fa-spinner fa-spin mr-1"></i>Deactivating...');
        $(this).prop('disabled', true);
        
        // Submit via AJAX to handle the response properly
        fetch('/deactivate/', {
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
    });

    // Transfer Manager modal functionality
    $('#transfer-manager-btn').on('click', function(e) {
        e.preventDefault();
        if (window.transferManager) {
            window.transferManager.showModal();
        } else {
            console.error('❌ Transfer manager not available');
            alert('Transfer manager not loaded. Please refresh the page.');
        }
    });

    // History modal functionality (commented out)
    /*
    $('#history-btn').on('click', function(e) {
        e.preventDefault();
        if (window.historyManager) {
            window.historyManager.showModal();
        } else {
            console.error('❌ History manager not available');
            alert('History manager not loaded. Please refresh the page.');
        }
    });
    */

    // Settings modal functionality
    $('#settings-btn').on('click', function(e) {
        e.preventDefault();
        $('#settings-modal').removeClass('hidden');
    });

    $('#close-settings').on('click', function() {
        $('#settings-modal').addClass('hidden');
    });    // Settings deactivate button - redirect to main deactivate modal
    $('#settings-deactivate-btn').on('click', function() {
        $('#settings-modal').addClass('hidden');
        $('#deactivate-modal').removeClass('hidden');
    });

    // About modal functionality
    $('#about-btn').on('click', function(e) {
        e.preventDefault();
        $('#about-modal').removeClass('hidden');
    });
    
    $('#close-about').on('click', function() {
        $('#about-modal').addClass('hidden');
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
                .addClass('grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4');
            $('.file-item-tile').show();
            $('.file-item-list').hide();
        } else {
            // List view (default)
            // Update button states
            $('#list-view-btn').removeClass('bg-gray-200 text-gray-700').addClass('bg-blue-500 text-white');
            $('#tile-view-btn').removeClass('bg-blue-500 text-white').addClass('bg-gray-200 text-gray-700');
            
            // Update layout
            $('#file-list-container')
                .removeClass('grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4')
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

    // Function to update storage progress bar
    function updateStorageProgress(usedBytes, quotaBytes) {
        var $container = $('#storage-container');
        if ($container.length) {
            // Update data attributes
            $container.attr('data-used', usedBytes);
            $container.attr('data-quota', quotaBytes);
            
            // Recalculate and update progress bar
            var used = parseFloat(usedBytes) || 0;
            var quota = parseFloat(quotaBytes) || 0;
            var percent = quota > 0 ? (used / quota) * 100 : 0;
            var percentClamped = Math.min(Math.max(percent, 0), 100);
            
            $('#storage-bar').css('width', percentClamped.toFixed(2) + '%');
            $('#storage-bar').attr('title', 'Used ' + percentClamped.toFixed(2) + '% of total');
            $('#storage-bar').attr('aria-valuenow', Math.round(percentClamped));
            
            // Update text displays
            var usedFormatted = formatFileSize(used);
            var quotaFormatted = formatFileSize(quota);
            
            // Update sidebar storage display
            $('.flex.flex-col.mt-2.ml-1.mr-2 .font-medium.text-gray-800').text(usedFormatted + ' / ' + quotaFormatted);
            
            console.log('Storage progress updated:', percentClamped.toFixed(2) + '%');
        }
    }

    // Function to format file size (helper function)
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 bytes';
        var k = 1024;
        var sizes = ['bytes', 'KB', 'MB', 'GB', 'TB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

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

    // Make updateStorageProgress available globally
    window.updateStorageProgress = updateStorageProgress;

    // Quota exceeded modal functionality
    $('#quota-modal-close').on('click', function() {
        $('#quota-exceeded-modal').addClass('hidden');
    });
    
    $('#quota-manage-files').on('click', function() {
        $('#quota-exceeded-modal').addClass('hidden');
        // Scroll to file list area
        $('html, body').animate({
            scrollTop: $('#file-list-container').offset().top - 100
        }, 500);
    });
    
    $('#upgrade-subscription-link').on('click', function() {
        $('#quota-exceeded-modal').addClass('hidden');
        // Open settings modal to show subscription info
        $('#settings-modal').removeClass('hidden');
    });

    // Duplicate filename modal functionality
    $('#duplicate-modal-close').on('click', function() {
        $('#duplicate-filename-modal').addClass('hidden');
    });
    
    $('#duplicate-manage-files').on('click', function() {
        $('#duplicate-filename-modal').addClass('hidden');
        // Scroll to file list area
        $('html, body').animate({
            scrollTop: $('#file-list-container').offset().top - 100
        }, 500);
    });

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