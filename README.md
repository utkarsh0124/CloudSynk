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

Deprecation note
----------------
`main/views.py` remains for backward compatibility but is marked deprecated. Plan to remove it once all consumers and frontends are using the DRF endpoints.

Contact / next steps
--------------------
- I can remove `main/views.py` and the old templates after a stabilization period.
- I can add more DRF-focused tests (blobs, user removal, edge cases) or add a CI matrix for Python versions.

Thanks — if you'd like, I can open a PR with these changes and enable the workflow for branch protection.
