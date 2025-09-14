document.addEventListener('DOMContentLoaded', function() {
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

    // Delete file functionality using event delegation
    $(document).on('click', '.file-delete-btn', function(e) {
        e.preventDefault();
        const deleteBtn = $(this);
        const blobId = deleteBtn.data('blob-id');
        
        if (!blobId) {
            alert('File ID not found');
            return;
        }
        
        const confirmed = confirm("Are you sure you want to delete this file?");
        if (confirmed) {
            const csrftoken = getCsrfToken();
            
            // Show loading state
            const originalText = deleteBtn.html();
            deleteBtn.html('<i class="fas fa-spinner fa-spin mr-1"></i>Deleting...');
            deleteBtn.prop('disabled', true);
            
            fetch(`/deleteFile/${blobId}/`, {
                method: 'POST',
                headers: csrftoken ? { 'X-CSRFToken': csrftoken } : {},
                credentials: 'same-origin'
            })
            .then(res => {
                if (res.ok) { 
                    window.location = '/'; 
                    return; 
                }
                alert('Delete failed');
            })
            .catch(err => { 
                console.error('Delete error', err); 
                alert('Delete error'); 
            })
            .finally(() => {
                // Reset button state
                deleteBtn.html(originalText);
                deleteBtn.prop('disabled', false);
            });
        }
    });

    // Enhanced download file functionality with resume capability
    $(document).on('click', '.file-download-btn', function(e) {
        e.preventDefault();
        const downloadBtn = $(this);
        const blobId = downloadBtn.data('blob-id');
        const blobName = downloadBtn.data('blob-name');
        const blobSize = downloadBtn.data('blob-size');
        // print all information
        console.log('Blob ID:', blobId, 'Blob Name:', blobName, 'Blob Size:', blobSize);
        
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
            const originalText = downloadBtn.html();
            downloadBtn.html('<i class="fas fa-spinner fa-spin mr-1"></i>Preparing download...');
            downloadBtn.prop('disabled', true);
            
            let downloadedBytes = resumeData ? resumeData.downloadedBytes : 0;
            let chunks = resumeData ? resumeData.chunks : [];
            
            // If already completed
            if (downloadedBytes >= blobSize && chunks.length > 0) {
                downloadCompleted(chunks, fileName, downloadBtn, originalText);
                return;
            }
            
            // For small files, use simple form submission
            if (blobSize < 5 * 1024 * 1024) { // Less than 5MB
                simpleDownload(blobId, downloadBtn, originalText);
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
                    downloadBtn.html(`<i class="fas fa-download mr-1"></i>Downloading... ${progress}%`);
                    
                } catch (error) {
                    console.error(`Failed to download chunk ${i}:`, error);
                    // Save current progress and show resume option
                    saveResumeData(downloadId, { downloadedBytes, chunks: chunks.slice() });
                    showResumeOption(blobId, fileName, downloadBtn, originalText);
                    return;
                }
            }
            
            // Download completed
            downloadCompleted(chunks, fileName, downloadBtn, originalText);
            clearResumeData(downloadId);
            
        } catch (error) {
            console.error('Download failed:', error);
            downloadBtn.html('<i class="fas fa-exclamation-triangle mr-1"></i>Download failed');
            setTimeout(() => {
                downloadBtn.html(originalText);
                downloadBtn.prop('disabled', false);
            }, 2000);
        }
    }

    function simpleDownload(blobId, downloadBtn, originalText) {
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
        downloadBtn.html('<i class="fas fa-download mr-1"></i>Downloading...');
        
        // Submit the form to trigger download
        form.submit();
        
        // Clean up and reset button state
        document.body.removeChild(form);
        
        // Show success state briefly, then reset
        setTimeout(() => {
            downloadBtn.html('<i class="fas fa-check mr-1"></i>Downloaded');
            setTimeout(() => {
                downloadBtn.html(originalText);
                downloadBtn.prop('disabled', false);
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

    function showResumeOption(blobId, fileName, downloadBtn, originalText) {
        downloadBtn.html('<i class="fas fa-play mr-1"></i>Resume download');
        downloadBtn.prop('disabled', false);
        
        // Add resume handler
        downloadBtn.off('click.resume').on('click.resume', function(e) {
            e.preventDefault();
            downloadBtn.off('click.resume');
            downloadFileWithResume(blobId, fileName, downloadBtn);
        });
    }

    function downloadCompleted(chunks, fileName, downloadBtn, originalText) {
        try {
            // Combine all chunks into a single blob
            const combinedBlob = new Blob(chunks.filter(chunk => chunk));
            triggerDownload(combinedBlob, fileName);
            
            downloadBtn.html('<i class="fas fa-check mr-1"></i>Downloaded');
            setTimeout(() => {
                downloadBtn.html(originalText);
                downloadBtn.prop('disabled', false);
            }, 2000);
        } catch (error) {
            console.error('Failed to complete download:', error);
            downloadBtn.html('<i class="fas fa-exclamation-triangle mr-1"></i>Download error');
            setTimeout(() => {
                downloadBtn.html(originalText);
                downloadBtn.prop('disabled', false);
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

    // View toggle functionality
    $('#tile-view-btn').on('click', function() {
        $('#file-list-container')
            .removeClass('flex flex-col')
            .addClass('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6');
        $('.file-item-tile').show();
        $('.file-item-list').hide();
    });
    $('#list-view-btn').on('click', function() {
        $('#file-list-container')
            .removeClass('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6')
            .addClass('flex flex-col');
        $('.file-item-tile').hide();
        $('.file-item-list').show();
    });
    // Initial state: tile view only
    $('.file-item-list').hide();

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