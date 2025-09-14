# CloudSynk AI Development Instructions

## Project Overview
CloudSynk is a Django-based cloud storage web application with Azure Blob Storage backend. It provides dual-interface architecture: traditional HTML forms and REST API endpoints controlled by `ENABLE_API_ENDPOINTS` feature flag.

## Architecture & Key Components

### Dual Interface Pattern
- **HTML endpoints** (`main/urls.py`): Traditional Django forms for browser navigation
- **API endpoints** (`main/api_urls.py`): REST API for XHR/AJAX requests
- Use `_is_api_request()` helper in views to detect XHR vs browser requests
- API routes are feature-flagged via `ENABLE_API_ENDPOINTS` setting

### Azure Integration (`az_intf/`)
- **Container pattern**: Each user gets a unique Azure blob container
- **Singleton management**: Global `CONTAINER_INSTANCE` for Azure connections
- **API abstraction**: `az_intf/api.py` provides high-level operations
- **Utils layer**: `az_intf/api_utils/` handles Azure SDK specifics

### Data Models (`main/models.py`)
- **UserInfo**: Extends Django User with subscription, quota, and container mapping
- **Blob**: File metadata with auto-generated hash IDs (`blob_id` via MD5)
- **Directory/Sharing**: Support for folder structure and access control
- Hash-based primary keys for blobs/directories ensure uniqueness

## Development Workflows

### Environment Setup
```bash
source env-setup                    # Sets up venv and Azure credentials
python manage.py runserver          # Start development server
./scripts/run_all_tests.sh          # Run both Django and Jest tests
```

### Testing Strategy
- **Backend**: Django test suite in `main/api_tests/`
- **Frontend**: Jest tests in `js_tests/` and `tests/`
- **Dual testing**: Scripts support running with/without API endpoints enabled
- **Test runner**: `scripts/run_all_tests.sh` handles both test suites

### Feature Flag Pattern
```python
# In settings.py
ENABLE_API_ENDPOINTS = os.environ.get('ENABLE_API_ENDPOINTS', 'false').lower() == 'true'

# In views
if not _is_api_request(request):
    return render(request, 'template.html')  # Browser request
return Response({'data': ...})               # API request
```

## Code Conventions

### View Structure
- Inherit from `APIView` for dual HTML/API support
- Use `_is_api_request()` to branch logic
- Return `Response()` for API, `render()` for HTML
- Apply `@csrf_exempt` only when necessary for API endpoints

### Error Handling
- Custom logging via `storage_webapp.logger` with severity levels
- Azure operations wrapped in try/catch with detailed logging
- API responses include `success` boolean and `message` fields

### Model Patterns
- Auto-generated hash IDs using `save()` override
- Foreign key relationships use Django's built-in User model
- Subscription system with choices defined in `subscription_config.py`

### Azure Integration
- Container names must be lowercase (Azure requirement)
- Blob operations go through `Container` class abstraction
- Connection management via singleton pattern to avoid repeated auth

## Key Files to Understand
- `main/views.py`: Dual-interface view pattern
- `az_intf/api.py`: Azure service facade
- `storage_webapp/settings.py`: Feature flags and Azure config
- `main/models.py`: Data model with hash ID generation
- `scripts/run_all_tests.sh`: Comprehensive test runner

## Common Tasks
- **Add new endpoint**: Create in both `urls.py` and `api_urls.py` if needed
- **Azure operations**: Use `az_intf.api` functions, not direct Azure SDK calls
- **Testing**: Run `./scripts/run_all_tests.sh` to verify both backend and frontend
- **Feature flags**: Check `ENABLE_API_ENDPOINTS` for API-related changes