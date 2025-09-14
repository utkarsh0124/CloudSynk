/**
 * CloudSynk Download Manager
 * Supports chunked downloads, pause/resume, queue management
 */

class DownloadManager {
    constructor() {
        this.downloads = new Map(); // Map of downloadId -> DownloadItem
        this.queue = [];
        this.activeDownloads = new Set(); // Currently active download IDs
        this.maxConcurrentDownloads = 1; // Configurable
        this.chunkSize = 2 * 1024 * 1024; // 2MB chunks
        this.smallFileThreshold = 5 * 1024 * 1024; // 5MB
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
        
        // Initialize UI components
        this.initializeUI();
        this.bindEvents();
        
        // Restore downloads from localStorage on page load
        this.restoreDownloads();
        
        console.log('🚀 DownloadManager initialized');
    }

    /**
     * Initialize the download modal and UI components
     */
    initializeUI() {
        // Check if modal already exists
        if (!$('#download-manager-modal').length) {
            this.createDownloadModal();
        }
        
        // Initialize progress bars and status containers
        this.updateUI();
    }

    /**
     * Create the download modal HTML structure
     */
    createDownloadModal() {
        const modalHTML = `
            <div id="download-manager-modal" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50 hidden transition-all duration-300">
                <div class="bg-white rounded-lg shadow-lg max-w-2xl w-full mx-4 transform transition-all duration-300" style="height: 70vh; max-height: 600px;">
                    <!-- Modal Header -->
                    <div class="flex justify-between items-center p-6 border-b border-gray-200">
                        <h2 class="text-2xl font-semibold text-gray-800 flex items-center">
                            <i class="fas fa-download mr-3 text-blue-600"></i>
                            Download Manager
                        </h2>
                        <button id="close-download-manager" class="text-gray-400 hover:text-gray-600 transition-colors">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    
                    <!-- Modal Content -->
                    <div class="flex flex-col h-full" style="height: calc(70vh - 140px); max-height: 460px;">
                        <!-- Active Downloads Section -->
                        <div class="px-6 py-4 border-b border-gray-100">
                            <h3 class="text-lg font-medium text-gray-700 mb-3 flex items-center">
                                <i class="fas fa-play-circle mr-2 text-green-600"></i>
                                Active Downloads
                                <span id="active-count" class="ml-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">0</span>
                            </h3>
                            <div id="active-downloads" class="space-y-3 max-h-32 overflow-y-auto">
                                <div id="no-active-downloads" class="text-gray-500 text-sm italic">No active downloads</div>
                            </div>
                        </div>
                        
                        <!-- Queued Downloads Section -->
                        <div class="px-6 py-4 flex-1 overflow-hidden">
                            <h3 class="text-lg font-medium text-gray-700 mb-3 flex items-center">
                                <i class="fas fa-clock mr-2 text-blue-600"></i>
                                Download Queue
                                <span id="queue-count" class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">0</span>
                            </h3>
                            <div id="download-queue" class="space-y-2 h-full overflow-y-auto">
                                <div id="no-queued-downloads" class="text-gray-500 text-sm italic">No downloads in queue</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Modal Footer -->
                    <div class="flex justify-between items-center p-6 border-t border-gray-200 bg-gray-50">
                        <div class="flex space-x-3">
                            <!-- Pause All and Resume All removed as requested -->
                        </div>
                        <div class="flex space-x-3">
                            <!-- Clear functionality temporarily disabled
                            <button id="clear-completed-downloads" class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors">
                                Clear Completed
                            </button>
                            <button id="clear-all-downloads" class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors">
                                Clear All
                            </button>
                            -->
                            <button id="close-download-manager-footer" class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modalHTML);
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        // Modal close buttons
        $(document).on('click', '#close-download-manager, #close-download-manager-footer', () => {
            this.hideModal();
        });

        // Control buttons
        /*
        $(document).on('click', '#clear-completed-downloads', () => {
            this.clearCompletedDownloads();
        });

        $(document).on('click', '#clear-all-downloads', () => {
            this.clearAllDownloads();
        });
        */

        // Individual download controls
        $(document).on('click', '.download-pause-btn', (e) => {
            const downloadId = $(e.target).closest('.download-item').data('download-id');
            this.pauseDownload(downloadId);
        });

        $(document).on('click', '.download-resume-btn', (e) => {
            const downloadId = $(e.target).closest('.download-item').data('download-id');
            this.resumeDownload(downloadId);
        });

        $(document).on('click', '.download-cancel-btn', (e) => {
            const downloadId = $(e.target).closest('.download-item').data('download-id');
            this.cancelDownload(downloadId);
        });

        $(document).on('click', '.download-retry-btn', (e) => {
            const downloadId = $(e.target).closest('.download-item').data('download-id');
            this.retryDownload(downloadId);
        });

        $(document).on('click', '.download-remove-btn', (e) => {
            const downloadId = $(e.target).closest('.download-item').data('download-id');
            this.removeDownload(downloadId);
        });

        // Show modal when downloads button is clicked
        $(document).on('click', '#downloads-btn', () => {
            this.showModal();
        });

        // Close modal when clicking outside
        $(document).on('click', '#download-manager-modal', (e) => {
            if (e.target.id === 'download-manager-modal') {
                this.hideModal();
            }
        });
    }

    /**
     * Add a new download to the queue
     */
    addDownload(blobId, fileName, fileSize, downloadBtn = null) {
        const downloadId = this.generateDownloadId();
        
        const downloadItem = {
            id: downloadId,
            blobId: blobId,
            fileName: fileName,
            fileSize: fileSize,
            downloadBtn: downloadBtn,
            status: 'queued', // queued, downloading, paused, completed, failed, cancelled
            progress: 0,
            downloadedBytes: 0,
            chunks: [],
            currentChunk: 0,
            totalChunks: 0,
            startTime: null,
            endTime: null,
            downloadSpeed: 0,
            remainingTime: 0,
            abortController: null,
            retryCount: 0,
            errorMessage: null,
            resumeData: this.getResumeData(downloadId)
        };

        // Determine download strategy
        downloadItem.isLargeFile = fileSize >= this.smallFileThreshold;
        
        if (downloadItem.isLargeFile) {
            downloadItem.totalChunks = Math.ceil(fileSize / this.chunkSize);
            
            // Restore progress if resuming
            if (downloadItem.resumeData) {
                downloadItem.downloadedBytes = downloadItem.resumeData.downloadedBytes || 0;
                downloadItem.currentChunk = downloadItem.resumeData.currentChunk || 0;
                downloadItem.chunks = downloadItem.resumeData.chunks || [];
                downloadItem.progress = (downloadItem.downloadedBytes / fileSize) * 100;
            }
        }

        this.downloads.set(downloadId, downloadItem);
        this.queue.push(downloadId);
        
        console.log(`📥 Added download: ${fileName} (${this.formatFileSize(fileSize)})`);
        
        this.updateUI();
        this.processQueue();
        
        return downloadId;
    }

    /**
     * Process the download queue
     */
    async processQueue() {
        if (this.activeDownloads.size >= this.maxConcurrentDownloads) {
            console.log('🔄 Maximum concurrent downloads reached, waiting...');
            return;
        }

        const queuedDownloads = this.queue.filter(id => {
            const download = this.downloads.get(id);
            return download && download.status === 'queued';
        });

        if (queuedDownloads.length === 0) {
            console.log('📭 No queued downloads');
            return;
        }

        const downloadId = queuedDownloads[0];
        const download = this.downloads.get(downloadId);
        
        if (!download) return;

        try {
            await this.startDownload(downloadId);
        } catch (error) {
            console.error(`❌ Failed to start download ${downloadId}:`, error);
            this.handleDownloadError(downloadId, error);
        }
    }

    /**
     * Start a specific download
     */
    async startDownload(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download || this.activeDownloads.has(downloadId)) return;

        download.status = 'downloading';
        download.startTime = Date.now();
        download.abortController = new AbortController();
        
        this.activeDownloads.add(downloadId);
        this.removeFromQueue(downloadId);
        
        console.log(`🚀 Starting download: ${download.fileName}`);
        
        this.updateUI();
        this.saveDownloadState(downloadId);

        try {
            if (download.isLargeFile) {
                await this.downloadLargeFile(downloadId);
            } else {
                await this.downloadSmallFile(downloadId);
            }
        } catch (error) {
            if (error.name === 'AbortError' || error.message === 'Download cancelled') {
                console.log(`🚫 Download cancelled: ${download.fileName}`);
                // Don't treat cancellation as an error - the status is already set correctly
            } else {
                console.error(`❌ Download failed: ${download.fileName}`, error);
                this.handleDownloadError(downloadId, error);
            }
        } finally {
            this.activeDownloads.delete(downloadId);
            // Continue processing queue
            setTimeout(() => this.processQueue(), 100);
        }
    }

    /**
     * Download large files using chunked approach with resume support
     */
    async downloadLargeFile(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download) return;

        console.log(`📦 Starting chunked download: ${download.fileName} (${download.totalChunks} chunks)`);

        const allChunks = [];
        
        for (let chunkIndex = download.currentChunk; chunkIndex < download.totalChunks; chunkIndex++) {
            if (download.status === 'paused') {
                console.log(`⏸️ Download paused during chunk processing: ${download.fileName}`);
                return; // Just return, don't throw error
            }
            
            if (download.status !== 'downloading') {
                throw new Error('Download cancelled');
            }

            const start = chunkIndex * this.chunkSize;
            const end = Math.min(start + this.chunkSize - 1, download.fileSize - 1);
            
            download.currentChunk = chunkIndex;
            
            try {
                const chunkData = await this.downloadChunk(downloadId, start, end);
                allChunks.push(chunkData);
                download.chunks[chunkIndex] = true;
                
                // Update progress
                download.downloadedBytes = (chunkIndex + 1) * this.chunkSize;
                if (chunkIndex === download.totalChunks - 1) {
                    download.downloadedBytes = download.fileSize; // Exact size for last chunk
                }
                
                download.progress = (download.downloadedBytes / download.fileSize) * 100;
                
                // Calculate speed and remaining time
                this.updateDownloadStats(downloadId);
                
                // Save progress
                this.saveDownloadState(downloadId);
                
                // Update UI
                this.updateUI();
                
                console.log(`✅ Chunk ${chunkIndex + 1}/${download.totalChunks} completed (${Math.round(download.progress)}%)`);
                
            } catch (error) {
                console.error(`❌ Chunk ${chunkIndex + 1} failed:`, error);
                
                // Retry chunk if possible
                if (download.retryCount < this.retryAttempts) {
                    download.retryCount++;
                    console.log(`🔄 Retrying chunk ${chunkIndex + 1} (attempt ${download.retryCount})`);
                    chunkIndex--; // Retry this chunk
                    await this.delay(this.retryDelay);
                    continue;
                } else {
                    throw error;
                }
            }
        }

        // All chunks downloaded successfully
        download.status = 'completed';
        download.endTime = Date.now();
        download.progress = 100;
        
        console.log(`🎉 Download completed: ${download.fileName}`);
        
        // Trigger file download
        this.triggerFileDownload(allChunks, download.fileName);
        
        // Clean up resume data
        this.clearResumeData(downloadId);
        
        this.updateUI();
    }

    /**
     * Download a single chunk
     */
    async downloadChunk(downloadId, start, end) {
        const download = this.downloads.get(downloadId);
        if (!download) throw new Error('Download not found');

        const response = await fetch(`/downloadFile/${download.blobId}/`, {
            method: 'POST',
            headers: {
                'Range': `bytes=${start}-${end}`,
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            signal: download.abortController.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.arrayBuffer();
    }

    /**
     * Download small files using simple approach
     */
    async downloadSmallFile(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download) return;

        console.log(`📄 Starting simple download: ${download.fileName}`);

        try {
            // Use form submission for small files (Django CSRF compatibility)
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/downloadFile/${download.blobId}/`;
            form.style.display = 'none';
            
            // Add CSRF token
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = this.getCSRFToken();
            form.appendChild(csrfInput);
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
            
            // Simulate completion for small files
            setTimeout(() => {
                download.status = 'completed';
                download.endTime = Date.now();
                download.progress = 100;
                download.downloadedBytes = download.fileSize;
                
                console.log(`✅ Small file download completed: ${download.fileName}`);
                
                this.updateUI();
                this.clearResumeData(downloadId);
            }, 1000);
            
        } catch (error) {
            throw error;
        }
    }

    /**
     * Pause a download
     */
    pauseDownload(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download || download.status !== 'downloading') return;

        if (download.abortController) {
            download.abortController.abort();
        }
        
        download.status = 'paused';
        this.activeDownloads.delete(downloadId);
        
        // Add back to queue if not already there
        if (!this.queue.includes(downloadId)) {
            this.queue.unshift(downloadId); // Add to front of queue
        }
        
        console.log(`⏸️ Paused download: ${download.fileName}`);
        
        this.saveDownloadState(downloadId);
        this.updateUI();
        
        // Continue processing other downloads
        setTimeout(() => this.processQueue(), 100);
    }

    /**
     * Resume a download
     */
    resumeDownload(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download || download.status !== 'paused') return;

        download.status = 'queued';
        download.retryCount = 0;
        
        if (!this.queue.includes(downloadId)) {
            this.queue.unshift(downloadId); // Add to front of queue
        }
        
        console.log(`▶️ Resumed download: ${download.fileName}`);
        
        this.updateUI();
        this.processQueue();
    }

    /**
     * Cancel a download
     */
    cancelDownload(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download) return;

        if (download.abortController) {
            download.abortController.abort();
        }
        
        download.status = 'cancelled';
        this.activeDownloads.delete(downloadId);
        this.removeFromQueue(downloadId);
        
        console.log(`🚫 Cancelled download: ${download.fileName}`);
        
        this.clearResumeData(downloadId);
        this.updateUI();
        
        // Continue processing other downloads
        setTimeout(() => this.processQueue(), 100);
    }

    /**
     * Retry a failed download
     */
    retryDownload(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download || download.status !== 'failed') return;

        download.status = 'queued';
        download.retryCount = 0;
        download.errorMessage = null;
        
        if (!this.queue.includes(downloadId)) {
            this.queue.unshift(downloadId); // Add to front of queue
        }
        
        console.log(`🔄 Retrying download: ${download.fileName}`);
        
        this.updateUI();
        this.processQueue();
    }

    /**
     * Remove a download from the manager
     */
    removeDownload(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download) return;

        // Cancel if active
        if (download.status === 'downloading' || download.status === 'paused') {
            this.cancelDownload(downloadId);
        }
        
        this.downloads.delete(downloadId);
        this.removeFromQueue(downloadId);
        this.clearResumeData(downloadId);
        
        console.log(`🗑️ Removed download: ${download.fileName}`);
        
        this.updateUI();
    }

    /*
    // Clear completed downloads - DISABLED
    clearCompletedDownloads() {
        const toRemove = [];
        this.downloads.forEach((download, downloadId) => {
            if (download.status === 'completed') {
                toRemove.push(downloadId);
            }
        });
        
        toRemove.forEach(downloadId => {
            this.removeDownload(downloadId);
        });
        
        console.log(`🧹 Cleared ${toRemove.length} completed downloads`);
    }

    // Clear all downloads - DISABLED
    clearAllDownloads() {
        if (!confirm('Are you sure you want to clear all downloads? Active downloads will be cancelled.')) {
            return;
        }
        
        // Cancel all active downloads manually
        const activeDownloads = Array.from(this.activeDownloads);
        activeDownloads.forEach(downloadId => {
            this.pauseDownload(downloadId);
        });
        
        // Clear all data
        this.downloads.clear();
        this.queue = [];
        this.activeDownloads.clear();
        
        // Clear all resume data
        this.clearAllResumeData();
        
        console.log('🧹 Cleared all downloads');
        
        this.updateUI();
    }
    */

    /**
     * Show the download manager modal
     */
    showModal() {
        $('#download-manager-modal').removeClass('hidden');
        this.updateUI();
    }

    /**
     * Hide the download manager modal
     */
    hideModal() {
        $('#download-manager-modal').addClass('hidden');
    }

    /**
     * Update the UI with current download states
     */
    updateUI() {
        this.updateActiveDownloads();
        this.updateQueuedDownloads();
        this.updateCounts();
    }

    /**
     * Update active downloads section
     */
    updateActiveDownloads() {
        const container = $('#active-downloads');
        const noActiveMsg = $('#no-active-downloads');
        
        const activeDownloads = Array.from(this.activeDownloads).map(id => this.downloads.get(id)).filter(Boolean);
        
        if (activeDownloads.length === 0) {
            noActiveMsg.show();
            container.children('.download-item').remove();
        } else {
            noActiveMsg.hide();
            
            // Remove items that are no longer active
            container.children('.download-item').each((i, el) => {
                const downloadId = $(el).data('download-id');
                if (!this.activeDownloads.has(downloadId)) {
                    $(el).remove();
                }
            });
            
            // Add or update active downloads
            activeDownloads.forEach(download => {
                let item = container.find(`[data-download-id="${download.id}"]`);
                if (item.length === 0) {
                    item = $(this.createDownloadItemHTML(download, true));
                    container.append(item);
                } else {
                    item.replaceWith(this.createDownloadItemHTML(download, true));
                }
            });
        }
    }

    /**
     * Update queued downloads section
     */
    updateQueuedDownloads() {
        const container = $('#download-queue');
        const noQueueMsg = $('#no-queued-downloads');
        
        const queuedDownloads = this.queue.map(id => this.downloads.get(id))
            .filter(download => download && ['queued', 'paused', 'failed', 'completed'].includes(download.status));
        
        if (queuedDownloads.length === 0) {
            noQueueMsg.show();
            container.children('.download-item').remove();
        } else {
            noQueueMsg.hide();
            
            container.empty();
            queuedDownloads.forEach(download => {
                const item = $(this.createDownloadItemHTML(download, false));
                container.append(item);
            });
        }
    }

    /**
     * Update download counts
     */
    updateCounts() {
        const activeCount = this.activeDownloads.size;
        const queueCount = this.queue.filter(id => {
            const download = this.downloads.get(id);
            return download && ['queued', 'paused', 'failed', 'completed'].includes(download.status);
        }).length;
        
        $('#active-count').text(activeCount);
        $('#queue-count').text(queueCount);
    }

    /**
     * Create HTML for a download item
     */
    createDownloadItemHTML(download, isActive) {
        const statusIcon = this.getStatusIcon(download.status);
        const statusColor = this.getStatusColor(download.status);
        const progressBarColor = this.getProgressBarColor(download.status);
        
        const timeInfo = isActive && download.status === 'downloading' ? 
            `<div class="text-xs text-gray-500 mt-1">
                Speed: ${this.formatSpeed(download.downloadSpeed)} • ETA: ${this.formatTime(download.remainingTime)}
            </div>` : '';
        
        const controls = this.getDownloadControls(download);
        
        return `
            <div class="download-item bg-gray-50 rounded-lg p-3" data-download-id="${download.id}">
                <div class="flex items-center justify-between">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center">
                            <i class="${statusIcon} ${statusColor} mr-2"></i>
                            <span class="font-medium text-gray-800 truncate">${download.fileName}</span>
                            <span class="ml-2 text-sm text-gray-500">${this.formatFileSize(download.fileSize)}</span>
                        </div>
                        
                        ${isActive ? `
                            <div class="mt-2">
                                <div class="flex justify-between text-xs text-gray-600 mb-1">
                                    <span>${Math.round(download.progress)}%</span>
                                    <span>${this.formatFileSize(download.downloadedBytes)} / ${this.formatFileSize(download.fileSize)}</span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-${progressBarColor} h-2 rounded-full transition-all duration-300" 
                                         style="width: ${download.progress}%"></div>
                                </div>
                                ${timeInfo}
                            </div>
                        ` : `
                            <div class="text-sm ${statusColor} mt-1">
                                ${this.getStatusText(download)}
                                ${download.progress > 0 ? ` • ${Math.round(download.progress)}%` : ''}
                            </div>
                        `}
                        
                        ${download.errorMessage ? `
                            <div class="text-xs text-red-600 mt-1 bg-red-50 p-2 rounded border">
                                ${download.errorMessage}
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="flex space-x-1 ml-3">
                        ${controls}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get status icon for download
     */
    getStatusIcon(status) {
        const icons = {
            'queued': 'fas fa-clock',
            'downloading': 'fas fa-download',
            'paused': 'fas fa-pause',
            'completed': 'fas fa-check-circle',
            'failed': 'fas fa-exclamation-triangle',
            'cancelled': 'fas fa-ban'
        };
        return icons[status] || 'fas fa-file';
    }

    /**
     * Get status color for download
     */
    getStatusColor(status) {
        const colors = {
            'queued': 'text-blue-600',
            'downloading': 'text-green-600',
            'paused': 'text-yellow-600',
            'completed': 'text-green-700',
            'failed': 'text-red-600',
            'cancelled': 'text-gray-600'
        };
        return colors[status] || 'text-gray-600';
    }

    /**
     * Get progress bar color for download
     */
    getProgressBarColor(status) {
        const colors = {
            'downloading': 'blue-600',
            'paused': 'yellow-500',
            'completed': 'green-600',
            'failed': 'red-600'
        };
        return colors[status] || 'blue-600';
    }

    /**
     * Get status text for download
     */
    getStatusText(download) {
        const statusTexts = {
            'queued': 'Waiting in queue',
            'downloading': 'Downloading...',
            'paused': 'Paused',
            'completed': 'Completed',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        };
        
        let text = statusTexts[download.status] || 'Unknown';
        
        if (download.status === 'failed' && download.retryCount > 0) {
            text += ` (${download.retryCount}/${this.retryAttempts} retries)`;
        }
        
        return text;
    }

    /**
     * Get control buttons for download
     */
    getDownloadControls(download) {
        let controls = '';
        
        switch (download.status) {
            case 'downloading':
                controls = `
                    <button class="download-pause-btn p-1 text-yellow-600 hover:bg-yellow-100 rounded" title="Pause">
                        <i class="fas fa-pause"></i>
                    </button>
                    <button class="download-cancel-btn p-1 text-red-600 hover:bg-red-100 rounded" title="Cancel">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                break;
            case 'paused':
                controls = `
                    <button class="download-resume-btn p-1 text-green-600 hover:bg-green-100 rounded" title="Resume">
                        <i class="fas fa-play"></i>
                    </button>
                    <button class="download-cancel-btn p-1 text-red-600 hover:bg-red-100 rounded" title="Cancel">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                break;
            case 'failed':
                controls = `
                    <button class="download-retry-btn p-1 text-blue-600 hover:bg-blue-100 rounded" title="Retry">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="download-remove-btn p-1 text-red-600 hover:bg-red-100 rounded" title="Remove">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
                break;
            case 'completed':
            case 'cancelled':
                controls = `
                    <button class="download-remove-btn p-1 text-gray-600 hover:bg-gray-200 rounded" title="Remove">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
                break;
            case 'queued':
                controls = `
                    <button class="download-cancel-btn p-1 text-red-600 hover:bg-red-100 rounded" title="Cancel">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                break;
        }
        
        return controls;
    }

    /**
     * Handle download errors
     */
    handleDownloadError(downloadId, error) {
        const download = this.downloads.get(downloadId);
        if (!download) return;

        download.status = 'failed';
        download.errorMessage = error.message || 'Unknown error occurred';
        
        this.activeDownloads.delete(downloadId);
        
        console.error(`❌ Download error for ${download.fileName}:`, error);
        
        this.updateUI();
    }

    /**
     * Update download statistics (speed, remaining time)
     */
    updateDownloadStats(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download || !download.startTime) return;

        const elapsed = (Date.now() - download.startTime) / 1000; // seconds
        const bytesPerSecond = download.downloadedBytes / elapsed;
        const remainingBytes = download.fileSize - download.downloadedBytes;
        const remainingSeconds = bytesPerSecond > 0 ? remainingBytes / bytesPerSecond : 0;
        
        download.downloadSpeed = bytesPerSecond;
        download.remainingTime = remainingSeconds;
    }

    /**
     * Trigger file download in browser
     */
    triggerFileDownload(chunks, fileName) {
        try {
            const blob = new Blob(chunks, { type: 'application/octet-stream' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = fileName;
            a.style.display = 'none';
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // Clean up the URL object
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            
            console.log(`💾 File download triggered: ${fileName}`);
        } catch (error) {
            console.error('❌ Failed to trigger download:', error);
        }
    }

    /**
     * Utility functions
     */
    generateDownloadId() {
        return 'dl_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    removeFromQueue(downloadId) {
        this.queue = this.queue.filter(id => id !== downloadId);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatSpeed(bytesPerSecond) {
        if (bytesPerSecond === 0) return '0 B/s';
        return this.formatFileSize(bytesPerSecond) + '/s';
    }

    formatTime(seconds) {
        if (!seconds || !isFinite(seconds)) return '--';
        if (seconds < 60) return Math.round(seconds) + 's';
        if (seconds < 3600) return Math.round(seconds / 60) + 'm';
        return Math.round(seconds / 3600) + 'h';
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getCSRFToken() {
        return $('[name=csrfmiddlewaretoken]').val() || 
               $('meta[name=csrf-token]').attr('content') || 
               document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }

    /**
     * Resume data management
     */
    saveDownloadState(downloadId) {
        const download = this.downloads.get(downloadId);
        if (!download || !download.isLargeFile) return;

        const resumeData = {
            downloadedBytes: download.downloadedBytes,
            currentChunk: download.currentChunk,
            chunks: download.chunks,
            lastSaved: Date.now()
        };
        
        localStorage.setItem(`cloudsynk_resume_${downloadId}`, JSON.stringify(resumeData));
    }

    getResumeData(downloadId) {
        try {
            const data = localStorage.getItem(`cloudsynk_resume_${downloadId}`);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.warn('Failed to parse resume data:', error);
            return null;
        }
    }

    clearResumeData(downloadId) {
        localStorage.removeItem(`cloudsynk_resume_${downloadId}`);
    }

    clearAllResumeData() {
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('cloudsynk_resume_')) {
                localStorage.removeItem(key);
            }
        });
    }

    restoreDownloads() {
        // In a real implementation, you might want to restore paused downloads
        // For now, we'll just clean up old resume data
        this.cleanupOldResumeData();
    }

    cleanupOldResumeData() {
        const cutoffTime = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
        
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('cloudsynk_resume_')) {
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    if (data.lastSaved < cutoffTime) {
                        localStorage.removeItem(key);
                    }
                } catch (error) {
                    localStorage.removeItem(key);
                }
            }
        });
    }
}

// Initialize the global download manager
window.downloadManager = new DownloadManager();

// Expose to global scope for easy integration
window.addDownload = (blobId, fileName, fileSize, downloadBtn) => {
    return window.downloadManager.addDownload(blobId, fileName, fileSize, downloadBtn);
};

console.log('🎉 CloudSynk Download Manager loaded successfully');