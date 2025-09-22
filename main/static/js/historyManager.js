// /**
//  * History Manager for CloudSynk
//  * Tracks and displays the last 10 user activities including uploads, downloads, deletions, etc.
//  */

// class HistoryManager {
//     constructor() {
//         this.activities = [];
//         this.maxHistoryItems = 10;
//         this.storageKey = 'cloudsynk_activity_history';
        
//         this.init();
//     }

//     init() {
//         this.loadHistoryFromStorage();
//         this.createModal();
//         this.bindEvents();
//     }

//     /**
//      * Add a new activity to the history
//      */
//     addActivity(type, fileName, fileSize = null, details = {}) {
//         const activity = {
//             id: Date.now() + Math.random().toString(36).substr(2, 9),
//             type: type, // 'upload', 'download', 'delete', 'login', 'signup', etc.
//             fileName: fileName,
//             fileSize: fileSize,
//             timestamp: Date.now(),
//             details: details,
//             status: 'completed' // 'completed', 'failed', 'in-progress'
//         };

//         // Add to beginning of array
//         this.activities.unshift(activity);
        
//         // Keep only last 10 activities
//         if (this.activities.length > this.maxHistoryItems) {
//             this.activities = this.activities.slice(0, this.maxHistoryItems);
//         }

//         this.saveHistoryToStorage();
//         this.updateUI();

//         console.log(`📝 Activity logged: ${type} - ${fileName}`);
//     }

//     /**
//      * Update activity status (for ongoing operations)
//      */
//     updateActivity(activityId, updates) {
//         const activity = this.activities.find(a => a.id === activityId);
//         if (activity) {
//             Object.assign(activity, updates);
//             this.saveHistoryToStorage();
//             this.updateUI();
//         }
//     }

//     /**
//      * Get activity icon based on type
//      */
//     getActivityIcon(type) {
//         const icons = {
//             'upload': 'fas fa-upload text-blue-500',
//             'download': 'fas fa-download text-green-500'
//         };
//         return icons[type] || 'fas fa-file text-gray-400';
//     }

//     /**
//      * Get activity description
//      */
//     getActivityDescription(activity) {
//         const { type, fileName, fileSize, details } = activity;

//         switch (type) {
//             case 'upload':
//                 return `Uploaded "${fileName}"${fileSize ? ` (${this.formatFileSize(fileSize)})` : ''}`;
//             case 'download':
//                 return `Downloaded "${fileName}"${fileSize ? ` (${this.formatFileSize(fileSize)})` : ''}`;
//             default:
//                 return `${type.charAt(0).toUpperCase() + type.slice(1)} action on "${fileName}"`;
//         }
//     }

//     /**
//      * Get status indicator
//      */
//     getStatusIndicator(status) {
//         const indicators = {
//             'completed': '<span class="w-2 h-2 bg-green-500 rounded-full"></span>',
//             'failed': '<span class="w-2 h-2 bg-red-500 rounded-full"></span>',
//             'in-progress': '<span class="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></span>'
//         };
//         return indicators[status] || '<span class="w-2 h-2 bg-gray-400 rounded-full"></span>';
//     }

//     /**
//      * Create the history modal UI
//      */
//     createModal() {
//         const modalHTML = `
//             <style>
//                 #history-modal .overflow-y-auto::-webkit-scrollbar {
//                     width: 8px;
//                 }
//                 #history-modal .overflow-y-auto::-webkit-scrollbar-track {
//                     background: #F7FAFC;
//                     border-radius: 4px;
//                 }
//                 #history-modal .overflow-y-auto::-webkit-scrollbar-thumb {
//                     background: #CBD5E0;
//                     border-radius: 4px;
//                 }
//                 #history-modal .overflow-y-auto::-webkit-scrollbar-thumb:hover {
//                     background: #A0AEC0;
//                 }
//             </style>
//             <div id="history-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50">
//                 <div class="flex items-center justify-center min-h-screen p-4">
//                     <div class="bg-white rounded-lg w-full max-w-2xl flex flex-col" style="height: 440px;">
//                         <!-- Modal Header -->
//                         <div class="flex items-center justify-between p-6 border-b flex-shrink-0">
//                             <div class="flex items-center space-x-3">
//                                 <i class="fas fa-history text-blue-500 text-xl"></i>
//                                 <h3 class="text-lg font-medium text-gray-900">Activity History</h3>
//                             </div>
//                             <button id="close-history" class="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
//                         </div>

//                         <!-- Modal Content - Scrollable Area (Limited to 3 items height) -->
//                         <div class="flex-1 overflow-y-auto p-6 min-h-0" style="max-height: 240px; scrollbar-width: thin; scrollbar-color: #CBD5E0 #F7FAFC;">
//                             <div id="history-list" class="space-y-3">
//                                 <!-- Activities will be populated here -->
//                             </div>
                            
//                             <!-- Empty State -->
//                             <div id="history-empty" class="text-center py-12 hidden">
//                                 <i class="fas fa-history text-gray-300 text-4xl mb-4"></i>
//                                 <p class="text-gray-500 text-lg">No activities yet</p>
//                                 <p class="text-gray-400 text-sm">Your recent activities will appear here</p>
//                             </div>
//                         </div>

//                         <!-- Modal Footer -->
//                         <div class="border-t p-4 bg-gray-50 rounded-b-lg flex-shrink-0">
//                             <!-- Scroll indicator -->
//                             <div id="scroll-indicator" class="text-center mb-2 hidden">
//                                 <p class="text-xs text-gray-400">
//                                     <i class="fas fa-chevron-up animate-bounce"></i>
//                                     Scroll up to view more activities
//                                 </p>
//                             </div>
//                             <div class="flex items-center justify-between">
//                                 <p class="text-sm text-gray-500">
//                                     Showing last ${this.maxHistoryItems} activities
//                                 </p>
//                                 <button id="clear-history" class="px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-700 rounded transition-colors">
//                                     Clear History
//                                 </button>
//                             </div>
//                         </div>
//                     </div>
//                 </div>
//             </div>
//         `;

//         document.body.insertAdjacentHTML('beforeend', modalHTML);
//     }

//     /**
//      * Bind event handlers
//      */
//     bindEvents() {
//         // Close modal
//         $(document).on('click', '#close-history', () => {
//             this.hideModal();
//         });

//         // Clear history
//         $(document).on('click', '#clear-history', () => {
//             this.clearHistory();
//         });

//         // Click outside to close
//         $(document).on('click', '#history-modal', (e) => {
//             if (e.target.id === 'history-modal') {
//                 this.hideModal();
//             }
//         });

//         // Escape key to close
//         $(document).on('keydown', (e) => {
//             if (e.key === 'Escape' && !$('#history-modal').hasClass('hidden')) {
//                 this.hideModal();
//             }
//         });

//         // Scroll detection for scroll indicator
//         $(document).on('scroll', '#history-modal .overflow-y-auto', () => {
//             this.updateScrollIndicator();
//         });
//     }

//     /**
//      * Update scroll indicator visibility
//      */
//     updateScrollIndicator() {
//         const scrollContainer = $('#history-modal .overflow-y-auto');
//         const indicator = $('#scroll-indicator');
        
//         if (scrollContainer.length && indicator.length) {
//             const element = scrollContainer[0];
//             const hasScrollableContent = element.scrollHeight > element.clientHeight;
//             const isScrolledToBottom = element.scrollTop + element.clientHeight >= element.scrollHeight - 10;
            
//             // Show indicator if there's scrollable content and user is at the bottom
//             if (hasScrollableContent && isScrolledToBottom) {
//                 indicator.removeClass('hidden');
//             } else {
//                 indicator.addClass('hidden');
//             }
//         }
//     }

//     /**
//      * Show the history modal
//      */
//     showModal() {
//         $('#history-modal').removeClass('hidden');
//         this.updateUI();
//         // Ensure scroll indicator is updated when modal is shown
//         setTimeout(() => this.updateScrollIndicator(), 200);
//     }

//     /**
//      * Hide the history modal
//      */
//     hideModal() {
//         $('#history-modal').addClass('hidden');
//     }

//     /**
//      * Update the modal UI
//      */
//     updateUI() {
//         const container = $('#history-list');
//         const emptyState = $('#history-empty');

//         if (this.activities.length === 0) {
//             container.empty();
//             emptyState.removeClass('hidden');
//             $('#scroll-indicator').addClass('hidden');
//             return;
//         }

//         emptyState.addClass('hidden');
        
//         const html = this.activities.map(activity => this.renderActivityItem(activity)).join('');
//         container.html(html);
        
//         // Update scroll indicator after content is rendered
//         setTimeout(() => this.updateScrollIndicator(), 100);
//     }

//     /**
//      * Render a single activity item
//      */
//     renderActivityItem(activity) {
//         const icon = this.getActivityIcon(activity.type);
//         const description = this.getActivityDescription(activity);
//         const timeAgo = this.formatTimeAgo(activity.timestamp);
//         const statusIndicator = this.getStatusIndicator(activity.status);

//         return `
//             <div class="bg-gray-50 rounded-lg p-4 border hover:bg-gray-100 transition-colors">
//                 <div class="flex items-start space-x-3">
//                     <div class="flex-shrink-0 mt-1">
//                         <i class="${icon}"></i>
//                     </div>
//                     <div class="flex-1 min-w-0">
//                         <div class="flex items-center justify-between">
//                             <p class="text-sm font-medium text-gray-900 truncate">
//                                 ${description}
//                             </p>
//                             <div class="flex items-center space-x-2 ml-4">
//                                 ${statusIndicator}
//                                 <span class="text-xs text-gray-500 whitespace-nowrap">${timeAgo}</span>
//                             </div>
//                         </div>
//                         ${activity.details && Object.keys(activity.details).length > 0 ? 
//                             `<p class="text-xs text-gray-600 mt-1">${this.formatDetails(activity.details)}</p>` : 
//                             ''
//                         }
//                     </div>
//                 </div>
//             </div>
//         `;
//     }

//     /**
//      * Format activity details
//      */
//     formatDetails(details) {
//         const parts = [];
//         if (details.transferId) parts.push(`Transfer ID: ${details.transferId}`);
//         if (details.speed) parts.push(`Speed: ${this.formatSpeed(details.speed)}`);
//         if (details.error) parts.push(`Error: ${details.error}`);
//         if (details.blobId) parts.push(`File ID: ${details.blobId}`);
        
//         return parts.join(' • ');
//     }

//     /**
//      * Clear all history
//      */
//     clearHistory() {
//         if (confirm('Are you sure you want to clear all activity history?')) {
//             this.activities = [];
//             this.saveHistoryToStorage();
//             this.updateUI();
//         }
//     }

//     /**
//      * Save history to localStorage
//      */
//     saveHistoryToStorage() {
//         try {
//             localStorage.setItem(this.storageKey, JSON.stringify(this.activities));
//         } catch (error) {
//             console.warn('Failed to save history to localStorage:', error);
//         }
//     }

//     /**
//      * Load history from localStorage
//      */
//     loadHistoryFromStorage() {
//         try {
//             const stored = localStorage.getItem(this.storageKey);
//             if (stored) {
//                 this.activities = JSON.parse(stored);
//                 // Ensure we don't exceed max items
//                 if (this.activities.length > this.maxHistoryItems) {
//                     this.activities = this.activities.slice(0, this.maxHistoryItems);
//                 }
//             }
//         } catch (error) {
//             console.warn('Failed to load history from localStorage:', error);
//             this.activities = [];
//         }
//     }

//     /**
//      * Format file size
//      */
//     formatFileSize(bytes) {
//         if (bytes === 0) return '0 Bytes';
//         const k = 1024;
//         const sizes = ['Bytes', 'KB', 'MB', 'GB'];
//         const i = Math.floor(Math.log(bytes) / Math.log(k));
//         return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
//     }

//     /**
//      * Format speed
//      */
//     formatSpeed(bytesPerSecond) {
//         return this.formatFileSize(bytesPerSecond) + '/s';
//     }

//     /**
//      * Format time ago
//      */
//     formatTimeAgo(timestamp) {
//         const now = Date.now();
//         const diff = now - timestamp;
//         const seconds = Math.floor(diff / 1000);
//         const minutes = Math.floor(seconds / 60);
//         const hours = Math.floor(minutes / 60);
//         const days = Math.floor(hours / 24);

//         if (days > 0) return `${days}d ago`;
//         if (hours > 0) return `${hours}h ago`;
//         if (minutes > 0) return `${minutes}m ago`;
//         return 'Just now';
//     }

//     /**
//      * Helper method to track common activities
//      */
//     trackUpload(fileName, fileSize, transferId) {
//         return this.addActivity('upload', fileName, fileSize, { transferId });
//     }

//     trackDownload(fileName, fileSize, transferId, blobId) {
//         return this.addActivity('download', fileName, fileSize, { transferId, blobId });
//     }
// }

// // Initialize global history manager
// window.historyManager = new HistoryManager();