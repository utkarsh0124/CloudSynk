# CloudSynk Transfer Manager

The Transfer Manager is a unified system for handling both file uploads and downloads in CloudSynk, providing a Google Drive-like experience for managing file transfers.

## Features

### 🚀 Unified Interface
- **Single Modal**: One interface for all file transfers (uploads and downloads)
- **Tabbed Views**: Filter by All Transfers, Uploads, or Downloads
- **Real-time Updates**: Live progress tracking with speed and ETA

### 📤 Upload Management
- **Chunked Uploads**: Large files (≥5MB) split into 2MB chunks for reliability
- **Direct Uploads**: Small files (<5MB) uploaded directly for speed
- **Resume Support**: Interrupted uploads can be resumed from where they left off
- **Queue Management**: Up to 3 concurrent uploads with automatic queue processing

### 📥 Download Management
- **Chunked Downloads**: Large files downloaded with range requests for reliability
- **Direct Downloads**: Small files downloaded directly via browser
- **Resume Support**: Interrupted downloads can be resumed
- **Queue Management**: Up to 3 concurrent downloads with automatic queue processing

### ⚡ Smart Features
- **Auto File Detection**: Automatically determines optimal transfer method based on file size
- **Progress Tracking**: Real-time progress with transfer speed and estimated time remaining
- **Error Handling**: Comprehensive error handling with retry capabilities
- **Pause/Resume**: Individual transfer control with pause and resume functionality
- **Cancel Transfers**: Ability to cancel ongoing or queued transfers

## User Interface

### Transfer Modal Structure
```
Transfer Manager
├── Tab Navigation (All/Uploads/Downloads)
├── In Progress Section
├── Queue Section
└── Completed Section
```

### Transfer Item Display
- **File Icon**: Based on file type and transfer direction
- **File Info**: Name, type, size
- **Progress Bar**: Visual progress indicator
- **Transfer Stats**: Speed, ETA, percentage complete
- **Controls**: Pause, Resume, Cancel buttons
- **Status Indicators**: Queued, Active, Paused, Completed, Error

## Technical Implementation

### Class Structure
```javascript
class TransferManager {
    constructor()
    
    // Transfer Management
    addUpload(file)
    addDownload(blobId, fileName, fileSize)
    pauseTransfer(transferId)
    resumeTransfer(transferId)
    cancelTransfer(transferId)
    
    // Processing
    processQueue()
    startTransfer(transfer)
    startUpload(transfer)
    startDownload(transfer)
    
    // UI Management
    showModal()
    hideModal()
    updateUI()
    switchTab(tab)
    
    // Utility Functions
    formatFileSize(bytes)
    formatSpeed(bytesPerSecond)
    formatTime(seconds)
}
```

### Backend Integration
- **Upload Endpoint**: `/chunkedUpload/` for chunked uploads, `/addFile/` for direct uploads
- **Download Endpoint**: `/downloadFile/<blob_id>/` with Range header support
- **Resume Support**: Upload status checking via GET requests to `/chunkedUpload/`

### File Size Thresholds
- **Small Files**: < 5MB - Direct transfer
- **Large Files**: ≥ 5MB - Chunked transfer (2MB chunks)

## Usage Examples

### JavaScript Integration
```javascript
// Upload a file
const transferId = window.transferManager.addUpload(file);

// Download a file
const transferId = window.transferManager.addDownload(blobId, fileName, fileSize);

// Show transfer manager
window.transferManager.showModal();

// Control transfers
window.transferManager.pauseTransfer(transferId);
window.transferManager.resumeTransfer(transferId);
window.transferManager.cancelTransfer(transferId);
```

### HTML Integration
```html
<!-- Transfer Manager Button -->
<button id="transfer-manager-btn">
    <i class="fas fa-exchange-alt"></i>
    <span>Transfers</span>
</button>

<!-- Include Script -->
<script src="{% static 'js/transferManager.js' %}"></script>
```

## Configuration

### Constants
- `maxConcurrentTransfers`: 3 (maximum simultaneous transfers)
- `chunkSize`: 2MB (chunk size for large file transfers)
- `sizeThreshold`: 5MB (threshold for chunked vs direct transfer)

### Customization
The Transfer Manager can be customized by modifying:
- Transfer queue limits
- Chunk sizes
- UI styling
- Progress update intervals
- Error handling strategies

## Browser Compatibility
- Modern browsers with ES6 support
- Fetch API support
- AbortController support for cancellation
- File API and Blob API support

## Dependencies
- jQuery (for DOM manipulation)
- Font Awesome (for icons)
- Tailwind CSS (for styling)

## Migration from Download Manager
The new Transfer Manager replaces the previous Download Manager with:
- Enhanced UI with tabbed interface
- Upload functionality integration
- Improved error handling
- Better progress tracking
- Unified experience for all file operations

## Future Enhancements
- Drag & drop upload zone
- Bulk transfer operations
- Transfer history persistence
- Bandwidth throttling controls
- Advanced filtering and search
- Desktop notifications for completed transfers