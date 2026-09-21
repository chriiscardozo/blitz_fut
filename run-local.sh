#!/usr/bin/env bash

set -Eeuo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$project_root/backend"
frontend_dir="$project_root/frontend"
prepare_only=false

usage() {
  printf '%s\n' \
    "Usage: ./run-local.sh [--prepare-only]" \
    "" \
    "Build the frontend, migrate the local database, ensure an administrator" \
    "exists, validate Django, and run Blitz Fut locally." \
    "" \
    "Options:" \
    "  --prepare-only  Perform every preparation step without starting the server." \
    "  -h, --help      Show this help."
}

case "${1:-}" in
  "") ;;
  --prepare-only) prepare_only=true ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

export BLITZ_FUT_DEBUG="${BLITZ_FUT_DEBUG:-true}"
export BLITZ_FUT_SECRET_KEY="${BLITZ_FUT_SECRET_KEY:-blitz-fut-local-validation-only}"
export BLITZ_FUT_ALLOWED_HOSTS="${BLITZ_FUT_ALLOWED_HOSTS:-localhost,127.0.0.1}"

node_version="$(tr -d '[:space:]' < "$project_root/.node-version")"
shopt -s nullglob
local_node_bins=("$project_root"/.tools/node-v"$node_version"-*/bin)
shopt -u nullglob

if (( ${#local_node_bins[@]} > 0 )) && [[ -x "${local_node_bins[0]}/npm" ]]; then
  export PATH="${local_node_bins[0]}:$PATH"
elif ! command -v npm >/dev/null 2>&1; then
  printf '%s\n' \
    "Node.js $node_version is required but npm was not found." \
    "Install Node.js or place its distribution under .tools/node-v${node_version}-<platform>." >&2
  exit 1
fi

python="$backend_dir/.venv/bin/python"
if [[ ! -x "$python" ]]; then
  if command -v uv >/dev/null 2>&1; then
    printf '%s\n' "Creating the backend environment..."
    (cd "$backend_dir" && uv sync)
  else
    printf '%s\n' \
      "The backend virtual environment is missing and uv is unavailable." \
      "Install uv, then run this command again." >&2
    exit 1
  fi
fi

if [[ ! -d "$frontend_dir/node_modules" ]]; then
  printf '%s\n' "Installing frontend dependencies..."
  (cd "$frontend_dir" && npm ci)
fi

printf '%s\n' "Building the frontend..."
(cd "$frontend_dir" && npm run build)

printf '%s\n' "Preparing the local database..."
(cd "$backend_dir" && "$python" manage.py migrate --noinput)

if ! (
  cd "$backend_dir"
  "$python" -c 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings"); import django; django.setup(); from django.contrib.auth import get_user_model; raise SystemExit(0 if get_user_model().objects.filter(is_active=True, is_staff=True).exists() else 1)'
); then
  if [[ ! -t 0 ]]; then
    printf '%s\n' \
      "No active administrator exists and this terminal is not interactive." \
      "Run ./run-local.sh from an interactive terminal to create one." >&2
    exit 1
  fi
  printf '%s\n' "No local administrator exists. Create the single admin account now:"
  (cd "$backend_dir" && "$python" manage.py createsuperuser)
fi

printf '%s\n' "Checking the application..."
(cd "$backend_dir" && "$python" manage.py check)

if [[ "$prepare_only" == true ]]; then
  printf '%s\n' "Blitz Fut is prepared for local validation."
  exit 0
fi

local_address="${BLITZ_FUT_LOCAL_ADDRESS:-127.0.0.1:8000}"
printf '\n%s\n%s\n\n' \
  "Blitz Fut is available at http://$local_address" \
  "Press Ctrl+C to stop it."
cd "$backend_dir"
exec "$python" manage.py runserver "$local_address" --noreload
