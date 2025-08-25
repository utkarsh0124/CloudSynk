StorageApp — Release notes & developer setup

Release: DRF migration (branch: django-rest-fw-enabling)
---------------------------------------------------
This release migrates the application's HTTP endpoints to Django REST Framework (DRF). The DRF-based views are implemented in `main/views.py` and serializers are in `main/serializers.py`.

Key points
 - DRF is the canonical interface for REST endpoints in this branch.
 - The DRF handlers live in `main/views.py`. The older `main/api_views.py` (if present) is deprecated and will be removed once consumers update.
 - Tests cover both legacy and DRF flows; new DRF-specific tests are in `main/tests/test_api_views.py`.

Developer setup
---------------
1. Create and activate a virtualenv (project convention uses `.storage-env`):

```bash
python3 -m venv .storage-env
. .storage-env/bin/activate
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Run tests:

```bash
python manage.py test
```

Continuous integration
----------------------
This branch adds a GitHub Actions CI workflow at `.github/workflows/ci.yml` which:
 - installs the Python environment,
 - ensures DRF-only routing (fails if `main/urls.py` still contains the old template fallback),
 - runs `python manage.py test`.

Logging and permissions
------------------------
The app's logger prefers writing to `log/` in the repo root. If the process can't create files there (common in shared or root-owned workspaces), the logger will fallback to a per-user directory under `/tmp/` (e.g. `/tmp/StorageApp-logs-<user>/...`) so file logging remains available without changing repo permissions.

If you want in-repo logs, adjust ownership from root to your user (requires root):

```bash
sudo chown -R $(whoami):$(whoami) /workspace/StorageApp/log
chmod -R u+w /workspace/StorageApp/log
```

Using the `/api/` endpoints from JS
----------------------------------

This project exposes API-friendly endpoints under `/api/` (for example `/api/login/`, `/api/signup/`, `/api/addFile/`). These routes are intended for browser XHR/fetch calls and are still protected by session cookies and CSRF.

Basic usage notes:

- Send the CSRF token with state-changing requests (POST/PUT/DELETE). In templates the token is available in a hidden input named `csrfmiddlewaretoken`.
- Mark requests as XHR so the server returns JSON rather than HTML. Include the header `X-Requested-With: XMLHttpRequest` and `Accept: application/json`.
- Example (fetch):

```js
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
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

If you prefer jQuery `$.ajax`, ensure the same headers are provided (see `main/static/js/login.js` for an example). Keep CORS disabled unless you intentionally need cross-origin clients.

Feature flag: ENABLE_API_ENDPOINTS
---------------------------------

The project uses an environment-driven feature flag `ENABLE_API_ENDPOINTS` to control whether explicit `/api/` routes are registered. Default behavior is conservative: the flag is `false` unless set in the environment. During development the code will still enable APIs when `DEBUG=True` to keep things convenient, but you can control the flag explicitly in any environment.

To run tests or start the dev server with API endpoints enabled for the duration of the command, use the helper script:

```bash
scripts/run_tests_with_api.sh
```

This script sets `ENABLE_API_ENDPOINTS=true`, runs `manage.py test`, then restores the environment.
