#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/multition_education"
ENV_FILE="/etc/multition.env"
BRANCH="${BRANCH:-master}"

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

cd "$APP_DIR"

log "Pulling latest from $BRANCH"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

log "Installing/updating dependencies"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt gunicorn --quiet

log "Loading env and running Django steps"
set -a
. "$ENV_FILE"
set +a

.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy || true

log "Restarting service"
sudo /bin/systemctl restart multition
sudo /bin/systemctl status multition --no-pager | head -10 || true

log "Deploy complete: $(git rev-parse --short HEAD)"
