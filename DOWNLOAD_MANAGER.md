# CloudSynk Download Manager

A modern, feature-rich download manager for the CloudSynk cloud storage application that provides Google Drive-like functionality.

## Features

### Core Functionality
- **Dual Download Strategy**: Automatic detection and handling of large files (≥5MB) vs small files (<5MB)
- **Chunked Downloads**: Large files are downloaded in 2MB chunks with resume support
- **Simple Downloads**: Small files use form submission for optimal performance
- **Queue Management**: Only 1 concurrent download with intelligent queue processing
- **Pause/Resume**: Full pause and resume support for large file downloads
- **Progress Tracking**: Real-time progress, speed, and ETA calculations

### User Interface
- **Modern Modal Interface**: Clean, responsive download manager modal
- **Active Downloads Section**: Shows currently downloading files with progress bars
- **Queue Section**: Displays waiting, paused, failed, and completed downloads
- **Individual Controls**: Pause, resume, cancel, retry, and remove buttons per download
- **Bulk Operations**: Clear functionality temporarily disabled

### Technical Features
- **Resume Data Persistence**: Downloads can be resumed across browser sessions
- **Error Handling**: Automatic retry with configurable attempts
- **Timeout Protection**: 5-minute timeout to prevent stuck downloads
- **Memory Management**: Efficient handling of large file chunks
- **Status Management**: Comprehensive status tracking (queued, downloading, paused, completed, failed, cancelled)

## Usage

### Basic Integration

The download manager automatically initializes when the page loads. To add a download:

```javascript
// Add a download to the queue
const downloadId = window.downloadManager.addDownload(blobId, fileName, fileSize, downloadBtn);

// Or use the global helper function
const downloadId = window.addDownload(blobId, fileName, fileSize, downloadBtn);
```

### Manual Controls

```javascript
// Show the download manager modal
window.downloadManager.showModal();

// Pause a specific download
window.downloadManager.pauseDownload(downloadId);

// Resume a specific download
window.downloadManager.resumeDownload(downloadId);

// Cancel a download
window.downloadManager.cancelDownload(downloadId);

// Clear all downloads
window.downloadManager.clearAllDownloads();
```

### Debug Functions

```javascript
// Check queue state
window.downloadManager.downloads;
window.downloadManager.queue;
window.downloadManager.activeDownloads;

// Force restart processing (if needed)
window.downloadManager.processQueue();
```

## File Structure

```
main/static/js/
├── downloadManager.js     # New modern download manager
└── index.js              # Updated to integrate with download manager
```

## Configuration

The download manager can be configured by modifying the constructor properties:

```javascript
class DownloadManager {
    constructor() {
        this.maxConcurrentDownloads = 1;        // Concurrent downloads
        this.chunkSize = 2 * 1024 * 1024;       // 2MB chunks
        this.smallFileThreshold = 5 * 1024 * 1024; // 5MB threshold
        this.retryAttempts = 3;                  // Retry attempts
        this.retryDelay = 1000;                  // 1 second retry delay
    }
}
```

## API Integration

The download manager works with the existing Django backend:

- **Small files**: Uses form submission to `/downloadFile/{blobId}/`
- **Large files**: Uses chunked requests with Range headers to `/downloadFile/{blobId}/`
- **Resume support**: Automatically includes Range headers for partial content requests

## Browser Compatibility

- **Modern browsers**: Full functionality with fetch API and modern JavaScript features
- **File download**: Uses Blob API and download attributes for seamless file saving
- **Local storage**: Resume data persisted using localStorage
- **Progress tracking**: Uses Performance API for accurate timing

## Migration from Old System

The new download manager replaces the previous queue system:

- ✅ **Improved UI**: Modern modal with better organization
- ✅ **Better error handling**: Comprehensive retry and timeout logic
- ✅ **Enhanced resume**: More reliable pause/resume functionality
- ✅ **Cleaner code**: Object-oriented design with better maintainability
- ✅ **Performance**: Optimized for both small and large file downloads

## Troubleshooting

### Common Issues

1. **Downloads stuck**: Use browser console to run `window.downloadManager.processQueue()`
2. **Modal not showing**: Check if downloadManager.js is loaded before index.js
3. **Resume not working**: Check browser's localStorage for resume data
4. **Slow downloads**: Check network connection and server response times

### Debug Commands

```javascript
// Check download manager state
console.log(window.downloadManager);

// View active downloads
console.log(Array.from(window.downloadManager.activeDownloads));

// View queue
console.log(window.downloadManager.queue);

// Check specific download
console.log(window.downloadManager.downloads.get('downloadId'));
```

## Future Enhancements

- **Bandwidth limiting**: Configurable download speed limits
- **Parallel downloads**: Support for multiple concurrent downloads
- **Download scheduling**: Queue prioritization and scheduling
- **Statistics**: Download history and performance metrics
- **Notifications**: Browser notifications for completed downloads