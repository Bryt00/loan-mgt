#!/bin/bash
# Kelstech Systems Deployment Script
# Supports: Ubuntu/Debian, Nginx, Gunicorn, PostgreSQL/SQLite, Cloudflare Strict SSL

set -e

# Configuration
PROJECT_NAME="loan-mgt"
USER="ajhope"           # Replace with your server username if different
PROJECT_DIR="/home/$USER/$PROJECT_NAME"
DOMAIN="loan-mgt.njuascogh.org" # Replace with actual domain
GUNICORN_WORKERS=3

echo "========================================================="
echo "Starting deployment for $PROJECT_NAME on $DOMAIN"
echo "========================================================="

# 1. Update system and install dependencies
echo "=> Updating system and installing dependencies..."
sudo apt-get update -y
sudo apt-get install -y build-essential python3-dev python3-venv libjpeg-dev zlib1g-dev nginx redis-server


# 2. Setup Project Directory
echo "=> Setting up project directory..."
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# Note: Assuming code is already in $PROJECT_DIR via Git or SFTP
# If using git, uncomment and modify below:
# if [ ! -d ".git" ]; then
#     git clone https://github.com/yourusername/kelstechsystems.git .
# else
#     git pull origin main
# fi

# 3. Create Virtual Environment and Install Requirements
echo "=> Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvicorn setproctitle

# 4. Django setup (Migrations, Static files)
echo "=> Running Django setup tasks..."
# Note: set your environment variables (SECRET_KEY, DEBUG=False, ALLOWED_HOSTS) here or in a .env file
sudo mkdir -p $PROJECT_DIR/staticfiles
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# 4b. Set correct file/folder permissions
echo "=> Setting file and folder permissions..."

# -- staticfiles: readable by Nginx (www-data), owned by app user

sudo chown -R $USER:www-data $PROJECT_DIR/staticfiles
sudo chmod -R 755 $PROJECT_DIR/staticfiles

# -- media: readable & writable by app user, readable by Nginx (www-data)
sudo mkdir -p $PROJECT_DIR/media
sudo chown -R $USER:www-data $PROJECT_DIR/media
sudo chmod -R 775 $PROJECT_DIR/media

# -- db.sqlite3: readable/writable by app user only (NOT by www-data or others)
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    sudo chown $USER:$USER $PROJECT_DIR/db.sqlite3
    sudo chmod 640 $PROJECT_DIR/db.sqlite3
fi
# Also ensure the project directory itself is traversable by Gunicorn
sudo chown $USER:www-data $PROJECT_DIR
sudo chmod 750 $PROJECT_DIR

# 5. Setup Gunicorn Systemd Service
echo "=> Configuring Gunicorn service..."
sudo bash -c "cat > /etc/systemd/system/gunicorn_${PROJECT_NAME}.service << EOF
[Unit]
Description=gunicorn daemon for $PROJECT_NAME
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin" "DJANGO_SETTINGS_MODULE=config.settings.prod"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --access-logfile - --workers $GUNICORN_WORKERS -k uvicorn.workers.UvicornWorker --bind unix:$PROJECT_DIR/$PROJECT_NAME.sock config.asgi:application

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable gunicorn_${PROJECT_NAME}
sudo systemctl restart gunicorn_${PROJECT_NAME}

# 5b. Setup Celery Systemd Service
echo "=> Configuring Celery service..."
sudo bash -c "cat > /etc/systemd/system/celery_${PROJECT_NAME}.service << EOF
[Unit]
Description=Celery worker daemon for $PROJECT_NAME
After=network.target redis-server.service

[Service]
Type=simple
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin" "DJANGO_SETTINGS_MODULE=config.settings.prod"
ExecStart=$PROJECT_DIR/venv/bin/celery -A config worker --loglevel=INFO
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl enable celery_${PROJECT_NAME}
sudo systemctl restart celery_${PROJECT_NAME}

# 6. Setup Cloudflare SSL Certificates (Strict Mode)
echo "=> Setting up Cloudflare SSL certificates..."
sudo mkdir -p /etc/nginx/ssl

echo ""
echo "========================================================="
echo "  STEP: Paste your Cloudflare ORIGIN CERTIFICATE below."
echo "  Go to Cloudflare Dashboard → SSL/TLS → Origin Server"
echo "  → Create Certificate → copy the certificate (.pem)."
echo "  Paste it here, then press ENTER and Ctrl+D when done:"
echo "========================================================="
sudo bash -c "cat > /etc/nginx/ssl/$DOMAIN.pem"
echo "✓ Certificate saved."

echo ""
echo "========================================================="
echo "  STEP: Paste your Cloudflare PRIVATE KEY below."
echo "  (This is shown only once when you created the cert.)"
echo "  Paste it here, then press ENTER and Ctrl+D when done:"
echo "========================================================="
sudo bash -c "cat > /etc/nginx/ssl/$DOMAIN.key"
sudo chmod 400 /etc/nginx/ssl/$DOMAIN.key
echo "✓ Private key saved and locked (chmod 400)."

# Cloudflare Authenticated Origin Pulls
echo "=> Downloading Cloudflare Authenticated Origin Pull CA..."
sudo curl -s https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem -o /etc/nginx/ssl/cloudflare_origin_pull_ca.pem
echo "✓ Cloudflare Origin Pull CA saved."

# 7. Setup Nginx with Cloudflare Security
echo "=> Configuring Nginx..."
sudo bash -c "cat > /etc/nginx/sites-available/$PROJECT_NAME << EOF
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # Cloudflare Strict SSL
    ssl_certificate /etc/nginx/ssl/$DOMAIN.pem;
    ssl_certificate_key /etc/nginx/ssl/$DOMAIN.key;
    
    # Authenticated Origin Pulls
    ssl_client_certificate /etc/nginx/ssl/cloudflare_origin_pull_ca.pem;
    ssl_verify_client on;

    # SSL Security Enhancements
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header X-Frame-Options \"SAMEORIGIN\";
    add_header X-XSS-Protection \"1; mode=block\";
    add_header X-Content-Type-Options \"nosniff\";
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;

    # Cloudflare Real IP Handling
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    set_real_ip_from 2400:cb00::/32;
    set_real_ip_from 2606:4700::/32;
    set_real_ip_from 2803:f800::/32;
    set_real_ip_from 2405:b500::/32;
    set_real_ip_from 2405:8100::/32;
    set_real_ip_from 2a06:98c0::/29;
    set_real_ip_from 2c0f:f248::/32;
    real_ip_header CF-Connecting-IP;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;
    }
}
EOF"

sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 8. Fix Nginx → Gunicorn socket permissions
# Nginx (www-data) needs to traverse /home/softivite/ to reach the socket.
# Without this, Nginx gets "Permission denied (13)" on the socket.
echo "=> Fixing socket permissions for Nginx..."
sudo usermod -a -G $USER www-data
sudo chmod g+x /home/$USER
echo "✓ www-data added to group '$USER' and home dir made traversable."

# 9. Setup UFW Firewall
echo "=> Setting up UFW firewall..."
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
# Enable firewall (uncomment below if running via terminal interaction, otherwise it might prompt)
# echo "y" | sudo ufw enable

echo "========================================================="
echo "Deployment setup complete!"
echo "Next Steps:"
echo "1. Upload your Cloudflare Origin Certificate to /etc/nginx/ssl/$DOMAIN.pem"
echo "2. Upload your Cloudflare Private Key to /etc/nginx/ssl/$DOMAIN.key"
echo "3. Restart Nginx: sudo systemctl restart nginx"
echo "4. Update your ALLOWED_HOSTS and set DEBUG=False in settings.py"
echo "========================================================="
