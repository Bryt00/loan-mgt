#!/bin/bash
# update.sh - Use this for pushing code changes
set -e

PROJECT_NAME="electronic-toll"
USER="r4v3n_00"           # Replace with your server username if different
PROJECT_DIR="/home/$USER/$PROJECT_NAME"

cd $PROJECT_DIR

# 1. Pull latest code (if using git)
# git pull origin main

# 2. Update dependencies and migrate
. venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# 3. Restart services
sudo systemctl restart gunicorn_${PROJECT_NAME}
# Only restart Nginx if you changed the nginx config
# sudo systemctl restart nginx

echo "Update complete!"