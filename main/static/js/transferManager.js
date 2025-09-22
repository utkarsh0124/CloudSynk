/**
 * Unified Transfer Manager for CloudSynk
 * Handles both uploads and downloads with chunked support, pause/resume, and queue management
 * Similar to Google Drive's transfer manager interface
 */

class TransferManager {
    constructor() {
        this.uploads = new Map();
        this.downloads = new Map();
        this.activeTransfers = new Map();
        this.maxConcurrentTransfers = 1;
        this.chunkSize = 1 * 1024 * 1024; // 1MB chunks
        this.currentView = 'all'; // all, uploads, downloads
        
        this.init();
    }

    init() {
        this.createModal();
        this.bindEvents();
        this.loadStoredTransfers();
    }

    /**
     * Add a new download to the queue
     */
    addDownload(blobId, fileName, fileSize) {
        const transferId = `download_${blobId}_${Date.now()}`;
        
        const transfer = {
            id: transferId,
            type: 'download',
            blobId: blobId,
            fileName: fileName,
            fileSize: fileSize,
            status: 'queued',
            progress: 0,
            speed: 0,
            eta: 0,
            downloadedBytes: 0,
            startTime: null,
            chunks: [],
            abortController: new AbortController(),
            error: null,
            createdAt: Date.now()
        };

        this.downloads.set(transferId, transfer);
        this.addToQueue(transfer);
        this.updateUI();
        this.processQueue();

        return transferId;
    }

    /**
     * Add a new upload to the queue
     */
    addUpload(file) {
        const transferId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        const transfer = {
            id: transferId,
            type: 'upload',
            file: file,
            fileName: file.name,
            fileSize: file.size,
            status: 'queued',
            progress: 0,
            speed: 0,
            eta: 0,
            uploadedBytes: 0,
            startTime: null,
            chunks: [],
            uploadId: transferId, // Unique upload ID for chunked uploads
            abortController: new AbortController(),
            error: null,
            createdAt: Date.now(),
            fileMetadata: {
                name: file.name,
                size: file.size,
                type: file.type,
                lastModified: file.lastModified
            }
        };

        this.uploads.set(transferId, transfer);
        this.addToQueue(transfer);
        this.updateUI();
        this.processQueue();

        return transferId;
    }

    /**
     * Add transfer to active queue
     */
    addToQueue(transfer) {
        this.activeTransfers.set(transfer.id, transfer);
    }

    /**
     * Process the transfer queue
     */
    async processQueue() {
        const activeCount = Array.from(this.activeTransfers.values())
            .filter(t => t.status === 'active').length;

        if (activeCount >= this.maxConcurrentTransfers) {
            return;
        }

        // Find next queued transfer
        const queuedTransfer = Array.from(this.activeTransfers.values())
            .find(t => t.status === 'queued');

        if (!queuedTransfer) {
            return;
        }

        // Start the transfer
        this.startTransfer(queuedTransfer);
    }

    /**
     * Start a transfer (upload or download)
     */
    async startTransfer(transfer) {
        transfer.status = 'active';
        transfer.startTime = Date.now();
        this.updateUI();

        try {
            if (transfer.type === 'download') {
                await this.startDownload(transfer);
            } else if (transfer.type === 'upload') {
                await this.startUpload(transfer);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                transfer.status = 'paused';
            } else {
                transfer.status = 'error';
                transfer.error = error.message;
                
                // Check if it's a quota error and show appropriate modal
                if (this.isQuotaError(error.message) && transfer.type === 'upload') {
                    this.showQuotaExceededModal(transfer);
                }
            }
            this.updateUI();
            this.processQueue(); // Continue with next transfer
        }
    }

    /**
     * Start download process (similar to existing downloadManager)
     */
    async startDownload(transfer) {
        const { blobId, fileName, fileSize } = transfer;

        // Determine if we need chunked download
        if (fileSize >= 5 * 1024 * 1024) { // 5MB threshold
            await this.downloadLargeFile(transfer);
        } else {
            await this.downloadSmallFile(transfer);
        }
    }

    /**
     * Download large file with chunking
     */
    async downloadLargeFile(transfer) {
        const { blobId, fileName, fileSize } = transfer;
        const chunks = [];
        const totalChunks = Math.ceil(fileSize / this.chunkSize);

        // Initialize chunks array if not exists (new download) or validate existing (resume)
        if (!transfer.chunks || transfer.chunks.length !== totalChunks) {
            transfer.chunks = new Array(totalChunks).fill(null);
        }

        // Calculate starting point for resume
        let startChunk = 0;
        if (transfer.downloadedBytes > 0) {
            // Find first missing chunk for resume
            startChunk = transfer.chunks.findIndex(chunk => chunk === null);
            if (startChunk === -1) {
                // All chunks already downloaded, just assemble
                startChunk = totalChunks;
            }
        }

        for (let i = startChunk; i < totalChunks; i++) {
            if (transfer.abortController.signal.aborted) {
                throw new DOMException('Download was aborted', 'AbortError');
            }

            const start = i * this.chunkSize;
            const end = Math.min(start + this.chunkSize - 1, fileSize - 1);

            try {
                const chunk = await this.downloadChunk(blobId, start, end, transfer.abortController.signal);
                transfer.chunks[i] = chunk;
                
                // Update progress (account for previously downloaded chunks)
                const downloadedChunks = transfer.chunks.filter(c => c !== null).length;
                transfer.downloadedBytes = downloadedChunks * this.chunkSize;
                if (downloadedChunks === totalChunks) {
                    // Last chunk might be smaller
                    const lastChunkSize = fileSize - (totalChunks - 1) * this.chunkSize;
                    transfer.downloadedBytes = (totalChunks - 1) * this.chunkSize + lastChunkSize;
                }
                
                transfer.progress = (transfer.downloadedBytes / fileSize) * 100;
                this.updateTransferStats(transfer);
                this.updateUI();

            } catch (error) {
                if (error.name === 'AbortError') {
                    throw error;
                }
                transfer.status = 'error';
                transfer.error = `Chunk ${i + 1} failed: ${error.message}`;
                throw error;
            }
        }

        // Combine chunks and trigger download
        const blob = new Blob(transfer.chunks);
        this.triggerDownload(blob, fileName);
        
        // Allow a brief moment for download to initiate before marking complete
        setTimeout(() => {
            this.moveToCompleted(transfer);
        }, 100);
    }

    /**
     * Download small file directly
     */
    async downloadSmallFile(transfer) {
        const { blobId, fileName } = transfer;

        try {
            const response = await fetch(`/downloadFile/${blobId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/json'
                },
                signal: transfer.abortController.signal
            });

            if (!response.ok) {
                throw new Error(`Download failed: ${response.statusText}`);
            }

            const blob = await response.blob();
            this.triggerDownload(blob, fileName);
            
            transfer.progress = 100;
            // Allow a brief moment for download to initiate before marking complete
            setTimeout(() => {
                this.moveToCompleted(transfer);
            }, 100);

        } catch (error) {
            if (error.name === 'AbortError') {
                throw error;
            }
            throw new Error(`Download failed: ${error.message}`);
        }
    }

    /**
     * Start upload process
     */
    async startUpload(transfer) {
        const { file, fileName, fileSize } = transfer;

        // // Determine if we need chunked upload
        // if (fileSize >= 5 * 1024 * 1024) { // 5MB threshold
        //     await this.uploadLargeFile(transfer);
        // } else {
        //     await this.uploadSmallFile(transfer);
        // }
            // Determine if we need chunked upload
        await this.uploadLargeFile(transfer);
    }

    /**
     * Upload large file with chunking
     */
    async uploadLargeFile(transfer) {
        const { file, fileName, fileSize, uploadId } = transfer;
        const totalChunks = Math.ceil(fileSize / this.chunkSize);
        
        // Uploads cannot be resumed from saved state (File objects can't be persisted)
        // Always start from the beginning for uploads
        let startChunk = 0;

        for (let i = startChunk; i < totalChunks; i++) {
            if (transfer.abortController.signal.aborted) {
                throw new DOMException('Upload was aborted', 'AbortError');
            }

            const start = i * this.chunkSize;
            const end = Math.min(start + this.chunkSize, fileSize);
            const chunk = file.slice(start, end);

            // If this is the final chunk, show processing status immediately before upload
            if (i === totalChunks - 1) {
                transfer.status = 'finalizing';
                transfer.progress = 100;
                transfer.statusMessage = 'processing file...';
                this.updateUI();
            }

            try {
                const result = await this.uploadChunk(transfer, i, chunk, totalChunks);
                
                // Check if this was the last chunk and upload is completed
                if (result.completed) {
                    // Update status to show completion but KEEP in modal
                    transfer.status = 'finalizing';
                    transfer.progress = 100;
                    transfer.statusMessage = 'File uploaded, server combining chunks...';
                    this.updateUI();
                    
                    // Wait before showing success message
                    setTimeout(() => {
                        if (!this.activeTransfers.has(transfer.id)) {
                            return;
                        }
                        
                        transfer.statusMessage = 'Upload completed successfully!';
                        this.updateUI();
                        
                        // Wait before reloading to show the new file
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000); // Show success for 2 seconds
                    }, 1000); // Wait 1 second for server processing
                    return;
                }
                
                // If this is the last chunk but no completion confirmation, start fallback timer
                if (i === totalChunks - 1) {
                    // Keep transfer visible while we wait for server processing
                    setTimeout(async () => {
                        // Update status but KEEP in modal
                        transfer.status = 'finalizing';
                        transfer.progress = 100;
                        transfer.statusMessage = 'File chunks combined, finalizing...';
                        this.updateUI();
                        
                        // Wait a bit more before declaring complete
                        setTimeout(() => {
                            transfer.statusMessage = 'Upload processing completed';
                            this.updateUI();
                            
                            // Remove from modal after timeout
                            setTimeout(() => {
                                this.moveToCompleted(transfer);
                                setTimeout(() => window.location.reload(), 1000);
                            }, 3000);
                        }, 10000); // Additional 10 seconds for processing
                    }, 30000); // Initial 30 second wait
                    return;
                }
                
                // Update progress for non-final chunks
                transfer.uploadedBytes = end;
                transfer.progress = Math.min((transfer.uploadedBytes / fileSize) * 100, 99); // Cap at 99% until finalized
                this.updateTransferStats(transfer);
                this.updateUI();

            } catch (error) {
                if (error.name === 'AbortError') {
                    throw error;
                }
                
                // Handle finalization timeout specifically
                if (i === totalChunks - 1 && error.message.includes('finalization timed out')) {
                    transfer.status = 'finalizing';
                    transfer.progress = 100;
                    transfer.statusMessage = 'Upload timed out, but file may still be processing...';
                    transfer.error = 'Upload finalization timed out. The file may still be processing on the server.';
                    this.updateUI();
                    
                    // Keep visible much longer for timeout cases
                    setTimeout(() => {
                        // Update status to show likely completion but KEEP visible
                        transfer.statusMessage = 'Upload likely completed (check file list)';
                        this.updateUI();
                        
                        // Only remove after extended time
                        setTimeout(() => {
                            this.moveToCompleted(transfer);
                            setTimeout(() => window.location.reload(), 2000);
                        }, 15000); // Keep visible for 15 more seconds
                    }, 10000); // Initial 10 second wait
                    return;
                }
                
                transfer.status = 'error';
                transfer.error = `Chunk ${i + 1} failed: ${error.message}`;
                throw error;
            }
        }
    }

    /**
     * Upload small file directly
     */
    async uploadSmallFile(transfer) {
        const { file, fileName } = transfer;

        try {
            const formData = new FormData();
            formData.append('blob_file', file);
            formData.append('file_name', fileName);

            const response = await fetch('/addFile/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                signal: transfer.abortController.signal
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Upload failed');
            }

            transfer.progress = 100;
            this.moveToCompleted(transfer);

            // Refresh the page to show new file
            window.location.reload();

        } catch (error) {
            if (error.name === 'AbortError') {
                throw error;
            }
            throw new Error(`Upload failed: ${error.message}`);
        }
    }

    /**
     * Upload a single chunk
     */
    async uploadChunk(transfer, chunkIndex, chunkData, totalChunks) {
        const formData = new FormData();
        formData.append('upload_id', transfer.uploadId);
        formData.append('chunk_index', chunkIndex);
        formData.append('total_chunks', totalChunks);
        formData.append('file_name', transfer.fileName);
        formData.append('total_size', transfer.fileSize);
        formData.append('chunk', chunkData);

        // Use longer timeout for the final chunk that includes finalization
        const isLastChunk = chunkIndex === totalChunks - 1;
        const timeoutMs = isLastChunk ? 120000 : 60000; // 2 minutes for final chunk, 1 minute for others
        
        // Create timeout promise
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error(isLastChunk ? 'Upload finalization timed out (2 minutes). The file may still be processing.' : 'Chunk upload timed out'));
            }, timeoutMs);
        });

        // Create fetch promise
        const fetchPromise = fetch('/chunkedUpload/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': this.getCsrfToken()
            },
            credentials: 'same-origin',  // Include cookies for authentication
            signal: transfer.abortController.signal
        }).then(async response => {
            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // Could not parse error response as JSON
                }
                throw new Error(errorMessage);
            }
            const result = await response.json();
            return result;
        });

        // Race between fetch and timeout
        return Promise.race([fetchPromise, timeoutPromise]);
    }

    /**
     * Download a single chunk (similar to existing downloadManager)
     */
    async downloadChunk(blobId, start, end, signal) {
        const response = await fetch(`/downloadFile/${blobId}/`, {
            method: 'POST',
            headers: {
                'Range': `bytes=${start}-${end}`,
                'X-CSRFToken': this.getCsrfToken(),
                'Content-Type': 'application/json'
            },
            signal: signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.arrayBuffer();
    }

    /**
     * Pause a transfer
     */
    pauseTransfer(transferId) {
        console.log('Attempting to pause transfer:', transferId);
        
        const transfer = this.activeTransfers.get(transferId) || 
                        this.uploads.get(transferId) || 
                        this.downloads.get(transferId);

        if (!transfer) {
            console.warn('Transfer not found for ID:', transferId);
            return;
        }

        if (transfer.status === 'active') {
            console.log('Pausing active transfer:', transferId);
            transfer.abortController.abort();
            transfer.status = 'paused';
            this.updateUI();
            this.processQueue(); // Start next transfer
        } else {
            console.log('Transfer not in active state, current status:', transfer.status);
        }
    }

    /**
     * Resume a transfer
     */
    resumeTransfer(transferId) {
        const transfer = this.activeTransfers.get(transferId) || 
                        this.uploads.get(transferId) || 
                        this.downloads.get(transferId);

        if (transfer && transfer.status === 'paused') {
            // Create new abort controller
            transfer.abortController = new AbortController();
            transfer.status = 'queued';
            this.updateUI();
            this.processQueue();
        }
    }

    /**
     * Cancel a transfer
     */
    cancelTransfer(transferId) {
        const transfer = this.activeTransfers.get(transferId) || 
                        this.uploads.get(transferId) || 
                        this.downloads.get(transferId);

        if (transfer) {
            transfer.abortController.abort();
            this.activeTransfers.delete(transferId);
            this.uploads.delete(transferId);
            this.downloads.delete(transferId);
            this.updateUI();
            this.processQueue();
        }
    }

    /**
     * Move transfer to completed (track in history and remove from active)
     */
    moveToCompleted(transfer) {
        // Track completed transfer in history manager (commented out)
        /*
        if (window.historyManager) {
            if (transfer.type === 'download') {
                window.historyManager.trackDownload(transfer.fileName, transfer.fileSize, transfer.id, transfer.blobId);
            } else if (transfer.type === 'upload') {
                window.historyManager.trackUpload(transfer.fileName, transfer.fileSize, transfer.id);
            }
        }
        */
        
        // Remove from active transfers
        this.activeTransfers.delete(transfer.id);
        this.updateUI();
        this.processQueue();
    }

    /**
     * Update transfer statistics (speed, ETA)
     */
    updateTransferStats(transfer) {
        if (!transfer.startTime) return;

        const now = Date.now();
        const elapsed = (now - transfer.startTime) / 1000; // seconds
        const bytesTransferred = transfer.type === 'upload' ? transfer.uploadedBytes : transfer.downloadedBytes;
        
        if (elapsed > 0) {
            transfer.speed = bytesTransferred / elapsed; // bytes per second
            
            const remainingBytes = transfer.fileSize - bytesTransferred;
            if (transfer.speed > 0) {
                transfer.eta = remainingBytes / transfer.speed; // seconds
            }
        }
    }

    /**
     * Create the transfer manager modal UI
     */
    createModal() {
        const modalHTML = `
            <div id="transfer-manager-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50">
                <div class="flex items-center justify-center min-h-screen p-4">
                    <div class="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col">
                        <!-- Modal Header -->
                        <div class="flex items-center justify-between p-6 border-b">
                            <h3 class="text-lg font-medium text-gray-900">Transfer Manager</h3>
                            <button id="close-transfer-manager" class="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
                        </div>

                        <!-- Tab Navigation -->
                        <div class="flex border-b bg-gray-50 px-6">
                            <button class="transfer-tab px-4 py-2 text-sm font-medium border-b-2 border-transparent hover:text-blue-600 hover:border-blue-300" data-tab="all">
                                All Transfers
                            </button>
                            <button class="transfer-tab px-4 py-2 text-sm font-medium border-b-2 border-transparent hover:text-blue-600 hover:border-blue-300" data-tab="uploads">
                                Uploads
                            </button>
                            <button class="transfer-tab px-4 py-2 text-sm font-medium border-b-2 border-transparent hover:text-blue-600 hover:border-blue-300" data-tab="downloads">
                                Downloads
                            </button>
                        </div>

                        <!-- Modal Content -->
                        <div class="flex-1 overflow-y-auto p-6">
                            <!-- Active Transfers -->
                            <div id="active-transfers-section" class="mb-6">
                                <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center">
                                    <span class="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                                    In Progress
                                </h4>
                                <div id="active-transfers-list" class="space-y-3">
                                    <!-- Active transfers will be populated here -->
                                </div>
                            </div>

                            <!-- Queued Transfers -->
                            <div id="queued-transfers-section" class="mb-6">
                                <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center">
                                    <span class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
                                    Queue
                                </h4>
                                <div id="queued-transfers-list" class="space-y-3">
                                    <!-- Queued transfers will be populated here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        // Close modal
        $(document).on('click', '#close-transfer-manager', () => {
            this.hideModal();
        });

        // Tab switching
        $(document).on('click', '.transfer-tab', (e) => {
            const tab = $(e.target).data('tab');
            this.switchTab(tab);
        });

        // Transfer control buttons (will be bound dynamically)
        $(document).on('click', '.pause-transfer-btn', (e) => {
            const transferId = $(e.target).closest('.pause-transfer-btn').data('transfer-id');
            this.pauseTransfer(transferId);
        });

        $(document).on('click', '.resume-transfer-btn', (e) => {
            const transferId = $(e.target).closest('.resume-transfer-btn').data('transfer-id');
            this.resumeTransfer(transferId);
        });

        $(document).on('click', '.cancel-transfer-btn', (e) => {
            const transferId = $(e.target).closest('.cancel-transfer-btn').data('transfer-id');
            this.cancelTransfer(transferId);
        });

        // Click outside to close
        $(document).on('click', '#transfer-manager-modal', (e) => {
            if (e.target.id === 'transfer-manager-modal') {
                this.hideModal();
            }
        });
    }

    /**
     * Switch between tabs
     */
    switchTab(tab) {
        this.currentView = tab;
        
        // Update tab appearance
        $('.transfer-tab').removeClass('text-blue-600 border-blue-500').addClass('text-gray-500 border-transparent');
        $(`.transfer-tab[data-tab="${tab}"]`).removeClass('text-gray-500 border-transparent').addClass('text-blue-600 border-blue-500');
        
        this.updateUI();
    }

    /**
     * Show the transfer manager modal
     */
    showModal() {
        $('#transfer-manager-modal').removeClass('hidden');
        this.updateUI();
    }

    /**
     * Hide the transfer manager modal
     */
    hideModal() {
        $('#transfer-manager-modal').addClass('hidden');
    }

    /**
     * Update the modal UI
     */
    updateUI() {
        this.updateActiveTransfers();
        this.updateQueuedTransfers();
        
        // Auto-save transfer state after UI updates
        this.saveTransferState();
    }

    /**
     * Update active transfers display
     */
    updateActiveTransfers() {
        const container = $('#active-transfers-list');
        const activeTransfers = Array.from(this.activeTransfers.values()).filter(t => 
            t.status === 'active' || t.status === 'paused' || t.status === 'finalizing'
        );
        const filteredTransfers = this.filterTransfersByCurrentView(activeTransfers);

        if (filteredTransfers.length === 0) {
            container.html('<p class="text-gray-500 text-sm">No active transfers</p>');
            return;
        }

        const html = filteredTransfers.map(transfer => this.renderTransferItem(transfer)).join('');
        container.html(html);
    }

    /**
     * Update queued transfers display
     */
    updateQueuedTransfers() {
        const container = $('#queued-transfers-list');
        const queuedTransfers = Array.from(this.activeTransfers.values()).filter(t => t.status === 'queued');
        const filteredTransfers = this.filterTransfersByCurrentView(queuedTransfers);

        if (filteredTransfers.length === 0) {
            container.html('<p class="text-gray-500 text-sm">No queued transfers</p>');
            return;
        }

        const html = filteredTransfers.map(transfer => this.renderTransferItem(transfer)).join('');
        container.html(html);
    }

    /**
     * Filter transfers by current view
     */
    filterTransfersByCurrentView(transfers) {
        if (this.currentView === 'all') {
            return transfers;
        }
        return transfers.filter(t => t.type === this.currentView.slice(0, -1)); // remove 's' from 'uploads'/'downloads'
    }

    /**
     * Render a single transfer item
     */
    renderTransferItem(transfer) {
        const statusIcon = this.getStatusIcon(transfer.status);
        const statusColor = this.getStatusColor(transfer.status);
        const progressBar = this.renderProgressBar(transfer);
        const controls = this.renderTransferControls(transfer);
        const stats = this.renderTransferStats(transfer);

        return `
            <div class="bg-gray-50 rounded-lg p-4 border">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center space-x-3">
                        <span class="${statusIcon} ${statusColor}"></span>
                        <div>
                            <p class="font-medium text-sm text-gray-900">${transfer.fileName}</p>
                            <p class="text-xs text-gray-500">${transfer.type.charAt(0).toUpperCase() + transfer.type.slice(1)} • ${this.formatFileSize(transfer.fileSize)}</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        ${controls}
                    </div>
                </div>
                ${progressBar}
                ${stats}
                ${transfer.error ? `<p class="text-xs text-red-600 mt-2">${transfer.error}</p>` : ''}
            </div>
        `;
    }

    /**
     * Get status icon
     */
    getStatusIcon(status) {
        const icons = {
            'queued': 'fas fa-clock',
            'active': 'fas fa-spinner fa-spin',
            'paused': 'fas fa-pause',
            'finalizing': 'fas fa-cog fa-spin',
            'completed': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle'
        };
        return icons[status] || 'fas fa-question';
    }

    /**
     * Get status color
     */
    getStatusColor(status) {
        const colors = {
            'queued': 'text-yellow-500',
            'active': 'text-blue-500',
            'paused': 'text-orange-500',
            'finalizing': 'text-purple-500',
            'completed': 'text-green-500',
            'error': 'text-red-500'
        };
        return colors[status] || 'text-gray-500';
    }

    /**
     * Render progress bar
     */
    renderProgressBar(transfer) {
        if (transfer.status === 'completed') {
            return '<div class="w-full bg-green-200 rounded-full h-2"><div class="bg-green-500 h-2 rounded-full" style="width: 100%"></div></div>';
        }
        
        if (transfer.status === 'error') {
            return '<div class="w-full bg-red-200 rounded-full h-2"><div class="bg-red-500 h-2 rounded-full" style="width: 100%"></div></div>';
        }

        if (transfer.status === 'finalizing') {
            return `
                <div class="w-full bg-purple-200 rounded-full h-2">
                    <div class="bg-purple-500 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                </div>
                <p class="text-xs text-purple-600 mt-1">⚙️ Server is combining file chunks...</p>
            `;
        }

        const progress = Math.round(transfer.progress || 0);
        return `
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: ${progress}%"></div>
            </div>
        `;
    }

    /**
     * Render transfer controls
     */
    renderTransferControls(transfer) {
        if (transfer.status === 'error') {
            return `<button class="cancel-transfer-btn text-gray-400 hover:text-red-500 text-sm" data-transfer-id="${transfer.id}" title="Remove"><i class="fas fa-times"></i></button>`;
        }

        if (transfer.status === 'finalizing') {
            return `<span class="text-purple-500 text-sm" title="Processing file on server..."><i class="fas fa-cog fa-spin"></i></span>`;
        }

        if (transfer.status === 'active') {
            return `<button class="pause-transfer-btn text-gray-600 hover:text-orange-500 text-sm" data-transfer-id="${transfer.id}" title="Pause"><i class="fas fa-pause"></i></button>`;
        }

        if (transfer.status === 'paused') {
            return `
                <button class="resume-transfer-btn text-gray-600 hover:text-green-500 text-sm mr-2" data-transfer-id="${transfer.id}" title="Resume"><i class="fas fa-play"></i></button>
                <button class="cancel-transfer-btn text-gray-400 hover:text-red-500 text-sm" data-transfer-id="${transfer.id}" title="Cancel"><i class="fas fa-times"></i></button>
            `;
        }

        if (transfer.status === 'queued') {
            return `<button class="cancel-transfer-btn text-gray-400 hover:text-red-500 text-sm" data-transfer-id="${transfer.id}" title="Cancel"><i class="fas fa-times"></i></button>`;
        }

        return '';
    }

    /**
     * Render transfer statistics
     */
    renderTransferStats(transfer) {
        if (transfer.status === 'error') {
            return '<p class="text-xs text-red-600 mt-1">Transfer failed</p>';
        }

        if (transfer.status === 'finalizing') {
            if (transfer.error && transfer.error.includes('timed out')) {
                return '<p class="text-xs text-orange-600 mt-1">100% • Processing timed out</p>';
            }
            // Use custom status message if available, otherwise default message
            const message = transfer.statusMessage || 'Server processing file...';
            return `<p class="text-xs text-purple-600 mt-1">100% • ${message}</p>`;
        }

        if (transfer.status === 'active' && transfer.speed > 0) {
            const speed = this.formatSpeed(transfer.speed);
            const eta = this.formatTime(transfer.eta);
            const progress = Math.round(transfer.progress || 0);
            return `<p class="text-xs text-gray-600 mt-1">${progress}% • ${speed} • ${eta} remaining</p>`;
        }

        if (transfer.status === 'paused') {
            const progress = Math.round(transfer.progress || 0);
            return `<p class="text-xs text-orange-600 mt-1">${progress}% • Paused</p>`;
        }

        return '<p class="text-xs text-gray-600 mt-1">Waiting...</p>';
    }

    /**
     * Utility functions
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatSpeed(bytesPerSecond) {
        return this.formatFileSize(bytesPerSecond) + '/s';
    }

    formatTime(seconds) {
        if (!seconds || seconds === Infinity) return 'Unknown';
        if (seconds < 60) return Math.round(seconds) + 's';
        if (seconds < 3600) return Math.round(seconds / 60) + 'm';
        return Math.round(seconds / 3600) + 'h';
    }

    getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : null;
    }

    triggerDownload(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    loadStoredTransfers() {
        try {
            const stored = localStorage.getItem('cloudsync_transfers');
            if (!stored) return;
            
            const state = JSON.parse(stored);
            
            // Check version compatibility
            if (!state.version || state.version !== '1.0') {
                console.warn('Incompatible transfer state version, clearing...');
                localStorage.removeItem('cloudsync_transfers');
                return;
            }
            
            // Only restore transfers from last 24 hours to avoid stale data
            const twentyFourHours = 24 * 60 * 60 * 1000;
            const cutoff = Date.now() - twentyFourHours;
            
            let restoredCount = 0;
            
            // Restore active transfers (convert to paused for manual resume)
            if (state.activeTransfers) {
                state.activeTransfers
                    .filter(([id, transfer]) => transfer.createdAt > cutoff)
                    .forEach(([id, transfer]) => {
                        // Convert active transfers to paused state
                        transfer.status = transfer.status === 'active' ? 'paused' : transfer.status;
                        
                        // Recreate non-serializable objects
                        transfer.abortController = new AbortController();
                        
                        // Skip uploads without file data (can't be resumed)
                        if (transfer.type === 'upload' && !transfer.file) {
                            console.warn(`Skipping upload transfer ${id} - file data not available`);
                            return;
                        }
                        
                        this.activeTransfers.set(id, transfer);
                        
                        // Also add to type-specific maps
                        if (transfer.type === 'upload') {
                            this.uploads.set(id, transfer);
                        } else if (transfer.type === 'download') {
                            this.downloads.set(id, transfer);
                        }
                        
                        restoredCount++;
                    });
            }
            
            // Show notification if transfers were restored
            if (restoredCount > 0) {
                this.showRestorationNotification(restoredCount);
            }
            
            // Clean up old localStorage data to prevent storage bloat
            this.cleanupOldTransferData();
            
        } catch (error) {
            console.warn('Failed to load transfer state:', error);
            // Clear potentially corrupted data
            try {
                localStorage.removeItem('cloudsync_transfers');
            } catch (e) {
                console.warn('Failed to clear corrupted transfer state:', e);
            }
        }
    }

    /**
     * Clean up old transfer data from localStorage to prevent storage bloat
     */
    cleanupOldTransferData() {
        try {
            // No completed transfers to clean up since we don't store them anymore
            // Just handle localStorage size limit
            const storage = localStorage.getItem('cloudsync_transfers');
            if (storage && storage.length > 500000) { // ~500KB threshold
                console.warn('Transfer storage getting large, clearing to prevent issues');
                localStorage.removeItem('cloudsync_transfers');
            }
        } catch (error) {
            console.warn('Failed to cleanup old transfer data:', error);
        }
    }

    saveTransferState() {
        try {
            // Prepare transfer state for storage (exclude non-serializable data)
            const serializeTransfer = (transfer) => {
                const serialized = { ...transfer };
                // Remove non-serializable objects
                delete serialized.file; // File object can't be serialized
                delete serialized.abortController; // AbortController can't be serialized
                return serialized;
            };

            const state = {
                activeTransfers: Array.from(this.activeTransfers.entries()).map(([id, transfer]) => [id, serializeTransfer(transfer)]),
                uploads: Array.from(this.uploads.entries()).map(([id, transfer]) => [id, serializeTransfer(transfer)]),
                downloads: Array.from(this.downloads.entries()).map(([id, transfer]) => [id, serializeTransfer(transfer)]),
                timestamp: Date.now(),
                version: '1.0' // For future compatibility
            };
            
            localStorage.setItem('cloudsync_transfers', JSON.stringify(state));
        } catch (error) {
            console.warn('Failed to save transfer state:', error);
            // Clear potentially corrupted data
            try {
                localStorage.removeItem('cloudsync_transfers');
            } catch (e) {
                console.warn('Failed to clear corrupted transfer state:', e);
            }
        }
    }

    /**
     * Show notification when transfers are restored from previous session
     */
    showRestorationNotification(count) {
        // Create notification element if it doesn't exist
        let notification = $('#transfer-restoration-notification');
        if (notification.length === 0) {
            notification = $(`
                <div id="transfer-restoration-notification" class="fixed top-4 right-4 bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm">
                    <div class="flex items-start">
                        <i class="fas fa-info-circle mr-2 mt-0.5"></i>
                        <div class="flex-1">
                            <p class="font-medium">Transfers Restored</p>
                            <p class="text-sm">Restored ${count} paused transfer(s) from previous session. Open Transfer Manager to resume.</p>
                            <button class="mt-2 text-xs bg-blue-200 hover:bg-blue-300 px-2 py-1 rounded" onclick="window.transferManager.showModal();">
                                Open Transfer Manager
                            </button>
                        </div>
                        <button class="ml-2 text-blue-700 hover:text-blue-900" onclick="$(this).parent().parent().fadeOut()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `);
            $('body').append(notification);
        } else {
            // Update existing notification
            notification.find('p').last().text(`Restored ${count} paused transfer(s) from previous session. Open Transfer Manager to resume.`);
        }
        
        // Show notification and auto-hide after 15 seconds (longer for user to read)
        notification.fadeIn();
        setTimeout(() => {
            notification.fadeOut();
        }, 15000);
    }

    /**
     * Check if error message indicates a quota issue
     */
    isQuotaError(errorMessage) {
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

    /**
     * Show quota exceeded modal for upload transfer
     */
    showQuotaExceededModal(transfer) {
        // Update modal content with transfer-specific information
        $('#quota-error-message').text(transfer.error);
        $('#quota-file-size').text(this.formatFileSize(transfer.fileSize));
        
        // Show the modal
        $('#quota-exceeded-modal').removeClass('hidden');
        
        // Also hide the transfer manager modal if it's open
        this.hideModal();
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize global transfer manager
window.transferManager = new TransferManager();