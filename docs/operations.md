# Blitz Fut — Operations Runbook

Last updated: 2026-09-17

This runbook covers the single live PythonAnywhere environment. There is no hosted staging environment. Replace every value in angle brackets before running a command.

## 1. Operational layout

Recommended PythonAnywhere paths:

```text
/home/<username>/blitz_fut/                 application repository
/home/<username>/blitz-fut-data/db.sqlite3 live database
/home/<username>/blitz-fut-data/backups/   rolling SQLite backups
/home/<username>/.virtualenvs/blitz-fut/   Python virtual environment
```

The database and backups deliberately live outside the Git checkout.

## 2. Initial PythonAnywhere deployment

PythonAnywhere's current `innit` system image supports Python 3.13. Confirm the account's system image under `Account > System image` before continuing.

1. Upload or clone the repository into `/home/<username>/blitz_fut`.
2. Build `frontend/dist` locally and upload that directory separately after cloning the repository. The generated build is intentionally excluded from the portfolio branch. Do not install the frontend toolchain on a free PythonAnywhere account; its storage and CPU requirements can exceed the free allowance.
3. Open a PythonAnywhere Bash console and create the data directories and virtual environment:

```bash
mkdir -p /home/<username>/blitz-fut-data/backups
mkvirtualenv blitz-fut --python=python3.13
pip install -r /home/<username>/blitz_fut/backend/requirements.txt
```

4. In the Web tab, create a web app with `Manual configuration` and Python 3.13. Configure `/home/<username>/.virtualenvs/blitz-fut` as its virtual environment.
5. Configure the Web tab source and working directories as `/home/<username>/blitz_fut/backend`.
6. Edit the PythonAnywhere-managed WSGI file from the Web tab. Keep the secrets in that file, which is outside the repository:

```python
import os
import sys

project_path = "/home/<username>/blitz_fut/backend"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["BLITZ_FUT_DEBUG"] = "false"
os.environ["BLITZ_FUT_SECRET_KEY"] = "<long-random-secret>"
os.environ["BLITZ_FUT_ALLOWED_HOSTS"] = "<username>.pythonanywhere.com"
os.environ["BLITZ_FUT_CSRF_TRUSTED_ORIGINS"] = "https://<username>.pythonanywhere.com"
os.environ["BLITZ_FUT_DB_PATH"] = "/home/<username>/blitz-fut-data/db.sqlite3"
os.environ["BLITZ_FUT_BACKUP_DIR"] = "/home/<username>/blitz-fut-data/backups"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

Generate `BLITZ_FUT_SECRET_KEY` locally with a cryptographically secure generator and transfer it without committing it.

7. In a Bash console, run the initial database setup:

```bash
workon blitz-fut
cd /home/<username>/blitz_fut/backend
export BLITZ_FUT_DEBUG=false
export BLITZ_FUT_SECRET_KEY='<same-secret-as-wsgi>'
export BLITZ_FUT_ALLOWED_HOSTS='<username>.pythonanywhere.com'
export BLITZ_FUT_CSRF_TRUSTED_ORIGINS='https://<username>.pythonanywhere.com'
export BLITZ_FUT_DB_PATH='/home/<username>/blitz-fut-data/db.sqlite3'
export BLITZ_FUT_BACKUP_DIR='/home/<username>/blitz-fut-data/backups'
python manage.py migrate
python manage.py check --deploy
python manage.py createsuperuser --username '<admin-username>'
```

Use a unique password stored in a password manager. Do not create additional staff or superuser accounts.

8. In the Web tab, add this static mapping:

```text
URL:       /assets/
Directory: /home/<username>/blitz_fut/frontend/dist/assets
```

9. Reload the web app, visit HTTPS, sign in, and perform the smoke checks in section 6.

The deployment procedure follows PythonAnywhere's official guides for [existing Django projects](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject), [virtual environments](https://help.pythonanywhere.com/pages/VirtualEnvForWebsites), and [static mappings](https://help.pythonanywhere.com/pages/StaticFiles).

## 3. Deploying an update

1. Run the complete local verification suite.
2. Build the frontend locally.
3. Create and download a live database backup before changing the application.
4. Upload or pull the new source, then upload the locally generated `frontend/dist` directory separately.
5. In the PythonAnywhere Bash console:

```bash
workon blitz-fut
cd /home/<username>/blitz_fut/backend
pip install -r requirements.txt
python manage.py migrate
python manage.py check --deploy
```

6. Reload the web app in the Web tab.
7. Perform the smoke checks.

If the release fails before any migration or live write, restore the previous source/build and reload. If data must also be rolled back, follow section 5.

## 4. SQLite backup policy

The free plan no longer provides scheduled tasks for newly created free accounts, so the MVP uses deliberate manual backups.

- Run a backup before every deployment.
- Run a backup before a result-entry session and after finalizing a stage or completing a competition.
- Retain the seven newest managed backups on PythonAnywhere.
- Download the newest backup after each competition event and retain it outside PythonAnywhere.
- Never make a live backup by copying the database file directly during possible writes.

Create a consistent backup with SQLite's backup API:

```bash
workon blitz-fut
cd /home/<username>/blitz_fut/backend
python manage.py backup_sqlite --retain 7
```

The command runs `PRAGMA quick_check`, writes with owner-only permissions, and prints the created path. Download that file using PythonAnywhere's Files tab.

## 5. Restoring SQLite

Restoration replaces live data. Coordinate downtime and preserve the current state first.

1. Disable or stop the web app from the PythonAnywhere Web tab so no request can write to SQLite.
2. Upload the chosen backup outside the repository.
3. Run:

```bash
workon blitz-fut
cd /home/<username>/blitz_fut/backend
python manage.py restore_sqlite /absolute/path/to/backup.sqlite3 --confirmed
python manage.py migrate
python manage.py check --deploy
```

The restore command validates the backup and creates a timestamped `pre-restore` safety copy beside the live database before replacement.

4. Reload the web app and perform the smoke checks.
5. Keep the safety copy until the restored application has been verified.

## 6. Live smoke checks

- `/api/health` returns `{"status": "ok"}`.
- The public competition list loads without authentication.
- The administrator can sign in over HTTPS.
- An anonymous state-changing API request is rejected.
- The current competition's teams, tables, matches, and leaderboards load.
- A known static asset under `/assets/` loads directly.
- The PythonAnywhere error log has no new traceback.
- `python manage.py backup_sqlite --retain 7` completes successfully.

## 7. Administrator password change

There is no web password-recovery flow. From a PythonAnywhere Bash console:

```bash
workon blitz-fut
cd /home/<username>/blitz_fut/backend
python manage.py changepassword '<admin-username>'
```

This uses Django's configured Argon2id password hasher. Never place a password on the command line or in the repository.

## 8. Free-plan maintenance

- Observe the CPU, disk, and expiry information shown in the PythonAnywhere dashboard.
- Renew the free web app whenever the dashboard requests it.
- Build React locally; PythonAnywhere only needs the generated `frontend/dist` files.
- The free app has one web worker. Keep administrative requests short and avoid running maintenance commands while results are being entered.
- Review this runbook against PythonAnywhere's current help and pricing pages before the first deployment because free-plan limits may change.

Relevant current references:

- [Supported Python versions](https://help.pythonanywhere.com/pages/PythonVersions)
- [Scheduled-task availability](https://help.pythonanywhere.com/pages/ScheduledTasks)
- [PythonAnywhere database types](https://help.pythonanywhere.com/pages/KindsOfDatabases)
- [React deployment caveat](https://help.pythonanywhere.com/pages/React)
