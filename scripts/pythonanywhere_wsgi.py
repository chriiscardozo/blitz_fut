"""WSGI entry point installed outside the repository on PythonAnywhere."""

import os
import sys
from pathlib import Path


home = Path.home()
project_path = home / "blitz_fut" / "backend"
environment_file = home / "blitz-fut-data" / "deployment.env"

for raw_line in environment_file.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    name, separator, value = line.partition("=")
    if not separator or not name:
        raise RuntimeError(f"Invalid deployment environment entry: {raw_line!r}")
    os.environ[name] = value

sys.path.insert(0, str(project_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application


application = get_wsgi_application()
