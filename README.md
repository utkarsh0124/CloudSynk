# CloudSynk

CloudSynk is a Django-based cloud storage web application with a modern frontend and RESTful API endpoints powered by Django REST Framework (DRF). It supports user authentication, file upload/download, and Azure Blob Storage integration.

## Features

- User signup, login, logout, and account deactivation (with all data removal)
- File upload, download, and management
- Modern UI (Tailwind CSS, jQuery, FontAwesome)
- REST API endpoints for all major actions
- Azure Blob Storage backend
- **Django Admin Panel** with automatic storage quota management
- Subscription-based storage quotas with admin controls
- Automated tests for backend and frontend

## Developer Setup

1. **Clone the repository** and enter the project directory.

2. **Create and activate a virtual environment:**
	```bash
	python3 -m venv .storage-env
	source .storage-env/bin/activate
	```

3. **Install dependencies:**
	```bash
	pip install --upgrade pip
	pip install -r requirements.txt
	npm install
	```

4. **Set up environment variables as needed** 
    ```bash
	source env-setup
	```

5. **Run the development server:**
	```bash
	python manage.py runserver
	```

6. **Run all tests (backend and frontend):**
	```bash
	./scripts/run_all_tests.sh
	```

7. **Create admin user for Django admin panel:**
	```bash
	# Create admin user with generated secure password
	python manage.py shell -c "
	from django.contrib.auth.models import User
	from main.models import UserInfo
	from main.subscription_config import SUBSCRIPTION_VALUES
	import secrets, string
	
	# Generate secure password
	password = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(20))
	print(f'Generated password: {password}')
	
	# Create admin user
	user = User.objects.create_user('admin', 'admin@cloudsynk.com', password, is_staff=True, is_superuser=True)
	UserInfo.objects.create(user=user, user_name='admin', subscription_type='OWNER', container_name='admin-admin', storage_quota_bytes=SUBSCRIPTION_VALUES['OWNER'], email_id='admin@cloudsynk.com')
	print('Admin user created. Access admin panel at /admin/')
	"
	```

## Admin Panel

- **Access**: Navigate to `/admin/` and login with admin credentials
- **User Management**: View and manage all user accounts
- **Subscription Management**: 
  - Change user subscription types (TESTER, STARTER, STANDARD, PREMIUM, PREMIUM_PLUS, OWNER)
  - **Storage quotas automatically update** based on subscription type from `subscription_config.py`
  - Storage quota field is read-only to prevent manual errors
- **Audit Logging**: All subscription changes are logged for security
- **Enhanced Display**: Storage shown in GB for better readability

### Subscription Types & Storage Quotas:
- **TESTER**: 1 MB
- **STARTER**: 1 GB
- **STANDARD**: 2 GB
- **PREMIUM**: 10 GB
- **PREMIUM_PLUS**: 100 GB
- **OWNER**: 1 TB (1024 GB)

## Logging and Permissions

- Logs are written to the `log/` directory by default. If you encounter permission issues, adjust ownership:

## API Usage

- API endpoints are available under `/api/` (e.g., `/api/login/`, `/api/signup/`, `/api/addFile/`).
- Use CSRF tokens and mark requests as XHR (`X-Requested-With: XMLHttpRequest`) for JSON responses.
- Example (using fetch in JS):
  ```js
  fetch('/api/login/', {
	 method: 'POST',
	 headers: {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'X-Requested-With': 'XMLHttpRequest',
		'X-CSRFToken': csrftoken,
	 },
	 credentials: 'same-origin',
	 body: JSON.stringify({ username: 'me', password: 'secret' })
  }).then(r => r.json()).then(console.log)
  ```

## Supported API Endpoints

**API endpoints in `api_urls.py` (for JS clients, XHR/fetch): Currently under ENABLE_API_ENDPOINTS feature flags**

- `POST /api/signup/` — Register a new user
- `POST /api/login/` — User login
- `POST /api/logout/` — User logout
- `POST /api/deactivate/` — Deactivate (delete) user account and all data
- `POST /api/addFile/` — Upload a file
- `POST /api/deleteFile/<blob_name>/` — Delete a file

**HTML & browser endpoints in `urls.py` (for HTML forms and navigation):**

- `GET /` or `/home/` — Home page (file list, dashboard)
- `POST /signup/` — Register a new user (form)
- `POST /login/` — User login (form)
- `POST /logout/` — User logout (form)
- `POST /deactivate/` — Deactivate (delete) user account and all data (form)
- `POST /addFile/` — Upload a file (form)
- `POST /deleteFile/<blob_name>/` — Delete a file (form)

All endpoints require authentication except signup and login. Deactivation will remove all user data and files. For JS clients, use appropriate headers and CSRF tokens. For HTML, use Django forms with `{% csrf_token %}`.

## Feature Flags

- The `ENABLE_API_ENDPOINTS` environment variable controls whether `/api/` routes are enabled.
- During development, APIs are enabled if `DEBUG=True`.
- Use `scripts/run_tests_with_api.sh` to run tests with API endpoints enabled.

## Contributing

- Fork the repo and create a feature branch.
- Add or update tests for your changes.
- Run all tests before submitting a pull request.
