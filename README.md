# CloudSynk

**cloud storage platform built with Django with Azure Blob Storage integration, chunked file uploads, email OTP-based authentication, and admin management.**

## 🎯 **Project Overview**

CloudSynk is a cloud storage solution that demonstrates modern web development practices with Django REST Framework, Azure cloud integration. It features a scalable subscription-based architecture with real-time file management capabilities.

## 🏗️ **Core Architecture**

**Backend**: Django REST Framework  
**Cloud Storage**: Azure Blob Storage with streaming uploads/downloads  
**Frontend**: Tailwind CSS, jQuery  
**Database**: SQLite  
**Authentication**: Session-based + OTP verification  
**Admin**: Custom Django Admin with automated quota management  

## 🚀 **Key Features**

### **Authentication & Security**
- **Dual Authentication**: Password-based or passwordless OTP login via email
- **Admin Security**: Comprehensive user management with audit logging

### **File Management**
- **Chunked Uploads**: Direct-to-Azure streaming with progress tracking
- **Blob Validation**: Azure-compliant naming with sanitization
- **Storage Quotas**: Automated enforcement by subscription tier

### **Subscription System**
- **Tiered Storage**: TESTER (1MB) → OWNER (1TB) with 6 levels
- **Auto-quota Management**: Storage limits auto-update on subscription changes
- **Real-time Usage**: Live storage calculation and enforcement

### **Admin Dashboard**
- **User Management**: Full CRUD operations with cascade deletion
- **Subscription Control**: Tier management with automatic quota updates
- **System Monitoring**: Comprehensive logging and audit trails
- **Enhanced UX**: Storage displayed in human-readable formats

## 📊 **Technical Highlights**

### **Database Design**
```python
# Core Models with optimized relationships
UserInfo (1:1 User) → subscription_type, storage_quotas
Blob → user_id, blob_name, size, timestamps
Directory → hierarchical structure support
OTP/LoginOTP → time-based verification systems
```

### **Azure Integration**
- **BlobServiceClient**: Direct container management
- **Streaming Operations**: Chunked upload/download with cancellation
- **SAS Token Generation**: Secure direct client access
- **Container Isolation**: User-specific blob containers

### **API Design**
- **RESTful Endpoints**: Full CRUD operations via DRF
- **Dual Response Format**: JSON for SPA, HTML for traditional forms  
- **CSRF Protection**: Token-based security for all mutations
- **Feature Flags**: Environment-controlled API availability

## 🛠️ **Development Setup**

```bash
# Environment setup
python3 -m venv .storage-env && source .storage-env/bin/activate
pip install -r requirements.txt && npm install

# Configure Azure credentials
source env-setup  # Sets AZURE_* environment variables

# Database & admin setup
python manage.py migrate
python manage.py shell -c "from django.contrib.auth.models import User; from main.models import UserInfo; User.objects.create_superuser('admin', 'admin@example.com', 'secure_password')"

# Development server
python manage.py runserver
```

## 🧪 **Testing Strategy**

```bash
# Comprehensive test suite
./scripts/run_all_tests.sh  # Backend (Django) + Frontend (Jest)

# Coverage includes:
# - API endpoint validation
# - Azure integration mocking  
# - Authentication flows
# - File upload/download operations
# - Admin functionality
```

## 📁 **Project Structure**

```
CloudSynk/
├── main/                   # Core Django app
│   ├── models.py          # User, Blob, Directory, OTP models
│   ├── views.py           # API views with dual format support
│   ├── admin.py           # Enhanced admin interfaces
│   └── api_tests/         # Comprehensive test suite
├── az_intf/               # Azure Blob Storage integration
│   ├── api_utils/         # Container, Auth, utils modules
│   └── testing_dummy.py   # Mock Azure client for testing
├── storage_webapp/        # Django project configuration
└── scripts/               # Deployment and testing scripts
```

## 🔧 **Production Considerations**

- **Environment Variables**: Azure credentials, secret keys externalized
- **Logging**: Structured logging with severity levels to `log/` directory
- **Security**: CSRF protection, session security, input validation
- **Scalability**: Chunked operations prevent memory issues with large files
- **Monitoring**: Admin audit trails and comprehensive error logging

## 🎯 **Interview Talking Points**

- **Cloud Integration**: Real Azure Blob Storage with streaming operations
- **Modern Django**: DRF, custom admin, model relationships, migrations
- **Security**: OTP authentication, CSRF protection, input validation
- **Testing**: Mock Azure services, comprehensive API testing
- **UX**: Progressive enhancement, dual authentication methods
- **DevOps**: Feature flags, environment configuration, automated testing

---

**Total Project Size**: ~50 files, 3,000+ lines of Python, comprehensive test coverage  
**Development Time**: Demonstrates 2-3 months of full-stack development  
**Complexity Level**: Mid-senior backend developer showcase project
