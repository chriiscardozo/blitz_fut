#!/usr/bin/env bash

set -Eeuo pipefail

username="${PYTHONANYWHERE_USERNAME:?PYTHONANYWHERE_USERNAME must be set}"
domain="${BLITZ_FUT_DOMAIN:-${username}.pythonanywhere.com}"
home_dir="/home/${username}"
project_dir="${home_dir}/blitz_fut"
data_dir="${home_dir}/blitz-fut-data"
environment_file="${data_dir}/deployment.env"
archive="${home_dir}/blitz-fut-deploy.tar.gz"
virtualenv_dir="${home_dir}/.virtualenvs/blitz-fut"

if [[ ! -f "$archive" ]]; then
  printf 'Deployment archive not found: %s\n' "$archive" >&2
  exit 1
fi

mkdir -p "$project_dir" "$data_dir/backups" "$(dirname "$virtualenv_dir")"
tar -xzf "$archive" -C "$project_dir"

if [[ ! -x "$virtualenv_dir/bin/python" ]]; then
  python3.13 -m venv "$virtualenv_dir"
fi

"$virtualenv_dir/bin/python" -m pip install \
  --disable-pip-version-check \
  --require-hashes \
  -r "$project_dir/backend/requirements.txt"

if [[ ! -f "$environment_file" ]]; then
  secret_key="$($virtualenv_dir/bin/python -c 'import secrets; print(secrets.token_urlsafe(64))')"
  umask 077
  printf '%s\n' \
    'BLITZ_FUT_DEBUG=false' \
    "BLITZ_FUT_SECRET_KEY=${secret_key}" \
    "BLITZ_FUT_ALLOWED_HOSTS=${domain}" \
    "BLITZ_FUT_CSRF_TRUSTED_ORIGINS=https://${domain}" \
    "BLITZ_FUT_DB_PATH=${data_dir}/db.sqlite3" \
    "BLITZ_FUT_BACKUP_DIR=${data_dir}/backups" \
    > "$environment_file"
fi
chmod 600 "$environment_file"

set -a
# shellcheck disable=SC1090
source "$environment_file"
set +a

cd "$project_dir/backend"
"$virtualenv_dir/bin/python" manage.py migrate --noinput
"$virtualenv_dir/bin/python" manage.py check --deploy

if [[ -f "$data_dir/db.sqlite3" ]]; then
  chmod 600 "$data_dir/db.sqlite3"
fi

printf '%s\n' 'BLITZ_FUT_DEPLOYMENT_READY'
