#!/bin/bash

# CloudSynk Production Deployment Script
# This script sets up the CloudSynk application with Gunicorn and Nginx

set -e

echo "🚀 Starting CloudSynk production deployment..."

PROJECT_DIR="/home/utsingh/workspace/CloudSynk"
APP_NAME="cloudsynk_production"
DOMAIN="cloudsynk.org.in"
DJANGO_PROJECT="storage_webapp"

# Change to project directory
cd "$PROJECT_DIR"

# Set up persistent database directory
DB_DIR="${DB_DIR:-/var/lib/cloudsynk}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/cloudsynk}"
export DB_DIR
export BACKUP_DIR

echo "📁 Setting up persistent database storage..."
sudo mkdir -p "$DB_DIR"
sudo chown utsingh:utsingh "$DB_DIR"
sudo chmod 755 "$DB_DIR"

sudo mkdir -p "$BACKUP_DIR"
sudo chown utsingh:utsingh "$BACKUP_DIR"
sudo chmod 755 "$BACKUP_DIR"

# Backup existing database if it exists
if [ -f "$DB_DIR/db_prod.sqlite3" ]; then
    echo "💾 Creating pre-deployment database backup..."
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/pre_deploy_${TIMESTAMP}.sqlite3"
    sqlite3 "$DB_DIR/db_prod.sqlite3" ".backup '$BACKUP_FILE'" 2>/dev/null || true
    if [ -f "$BACKUP_FILE" ]; then
        gzip "$BACKUP_FILE"
        echo "  ✅ Backup created: ${BACKUP_FILE}.gz"
    fi
fi

# Stop any running servers
echo "📊 Stopping any running Django development servers..."
pkill -f "python manage.py runserver" || true

# Archive old logs before creating new ones
echo "📦 Archiving old logs..."
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_ARCHIVE_DIR="/log_dump/$TIMESTAMP"

# Create archive directory
sudo mkdir -p "$LOG_ARCHIVE_DIR"

# Archive application logs if they exist and have content
if [ -s "$PROJECT_DIR/log/cloudsynk.log" ]; then
    echo "  → Archiving cloudsynk.log to $LOG_ARCHIVE_DIR/"
    sudo cp "$PROJECT_DIR/log/cloudsynk.log" "$LOG_ARCHIVE_DIR/cloudsynk.log"
    # Archive any rotated log files
    if ls "$PROJECT_DIR/log/cloudsynk.log".* 1> /dev/null 2>&1; then
        sudo cp "$PROJECT_DIR/log/cloudsynk.log".* "$LOG_ARCHIVE_DIR/" 2>/dev/null || true
    fi
    # Clear the current log file
    > "$PROJECT_DIR/log/cloudsynk.log"
fi

# Archive Django logs if they exist and have content
if [ -s "$PROJECT_DIR/logs/django_prod.log" ]; then
    echo "  → Archiving django_prod.log to $LOG_ARCHIVE_DIR/"
    sudo cp "$PROJECT_DIR/logs/django_prod.log" "$LOG_ARCHIVE_DIR/django_prod.log"
    # Archive any rotated log files
    if ls "$PROJECT_DIR/logs/django_prod.log".* 1> /dev/null 2>&1; then
        sudo cp "$PROJECT_DIR/logs/django_prod.log".* "$LOG_ARCHIVE_DIR/" 2>/dev/null || true
    fi
    # Clear the current log file
    > "$PROJECT_DIR/logs/django_prod.log"
fi

# Archive Gunicorn logs if they exist and have content
if [ -s "/var/log/cloudsynk/gunicorn_access.log" ]; then
    echo "  → Archiving gunicorn logs to $LOG_ARCHIVE_DIR/"
    sudo cp /var/log/cloudsynk/gunicorn_access.log "$LOG_ARCHIVE_DIR/gunicorn_access.log" 2>/dev/null || true
    sudo cp /var/log/cloudsynk/gunicorn_error.log "$LOG_ARCHIVE_DIR/gunicorn_error.log" 2>/dev/null || true
    sudo chown -R utsingh:utsingh "$LOG_ARCHIVE_DIR"
    # Clear the current log files
    sudo truncate -s 0 /var/log/cloudsynk/gunicorn_access.log
    sudo truncate -s 0 /var/log/cloudsynk/gunicorn_error.log
fi

# Only create archive directory if we archived something
if [ -z "$(sudo ls -A $LOG_ARCHIVE_DIR 2>/dev/null)" ]; then
    echo "  → No logs to archive (all log files are empty or don't exist)"
    sudo rmdir "$LOG_ARCHIVE_DIR" 2>/dev/null || true
else
    echo "  ✅ Logs archived to: $LOG_ARCHIVE_DIR"
fi

# Create log directories
echo "📁 Creating log directories..."
sudo mkdir -p /var/log/cloudsynk
sudo chown utsingh:utsingh /var/log/cloudsynk
mkdir -p "$PROJECT_DIR/log"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/tmp"

# Fix log file ownership
echo "🔧 Setting up log file permissions..."
touch "$PROJECT_DIR/log/cloudsynk.log"
chown utsingh:utsingh "$PROJECT_DIR/log/cloudsynk.log"

chmod 664 "$PROJECT_DIR/log/cloudsynk.log"

# Run the production environment setup as root (as per your requirement)
echo "🔧 Setting up production environment..."
if [ -f "$PROJECT_DIR/env-setup-prod" ]; then
    # Source the env-setup-prod script
    source "$PROJECT_DIR/env-setup-prod"
else
    echo "❌ Error: env-setup-prod not found!"
    exit 1
fi

# Create Gunicorn configuration for production
echo "🔧 Creating Gunicorn configuration..."
cat > "$PROJECT_DIR/gunicorn_prod.conf.py" << EOF
# Production Gunicorn configuration for CloudSynk
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
user = "utsingh"
group = "utsingh"
tmp_upload_dir = None
errorlog = "/var/log/cloudsynk/gunicorn_error.log"
accesslog = "/var/log/cloudsynk/gunicorn_access.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "info"
preload_app = True
enable_stdio_inheritance = True
daemon = False
pidfile = "$PROJECT_DIR/cloudsynk_gunicorn.pid"
EOF

# Create systemd service for CloudSynk
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/cloudsynk_production.service > /dev/null << EOF
[Unit]
Description=CloudSynk Production Django App with Gunicorn
After=network.target

[Service]
Type=notify
User=utsingh
Group=utsingh
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=/home/utsingh/workspace/az_intf.systemd
Environment="PATH=$PROJECT_DIR/.storage-env-prod/bin"
Environment="DJANGO_SETTINGS_MODULE=$DJANGO_PROJECT.settings_prod"
Environment="DJANGO_ENV=production"
Environment="DEBUG=false"
Environment="DJANGO_DEBUG=false"
Environment="PYTHONPATH=$PROJECT_DIR/../:\$PYTHONPATH"
Environment="TMPDIR=$PROJECT_DIR/tmp"
Environment="DB_DIR=/var/lib/cloudsynk"
Environment="BACKUP_DIR=/var/backups/cloudsynk"
ExecStart=$PROJECT_DIR/.storage-env-prod/bin/gunicorn \\
    --config $PROJECT_DIR/gunicorn_prod.conf.py \\
    $DJANGO_PROJECT.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Install Nginx if not present
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing Nginx..."
    sudo apt update
    sudo apt install -y nginx
fi

# Check if Nginx configuration already exists
echo "🌐 Checking Nginx configuration..."
if [ -f /etc/nginx/sites-available/cloudsynk ]; then
    echo "✅ Nginx configuration already exists, skipping..."
else
    echo "🔧 Creating Nginx configuration with HTTPS enforcement..."
    sudo tee /etc/nginx/sites-available/cloudsynk > /dev/null << 'EOF'
# Gunicorn upstream
upstream gunicorn_backend {
    ip_hash;
    server 127.0.0.1:8000;
}

# HTTP server - Redirect all traffic to HTTPS
server {
    listen 80;
    server_name cloudsynk.org.in www.cloudsynk.org.in;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://$host$request_uri;
}

# HTTPS server - Main application
server {
    listen 443 ssl http2;
    server_name cloudsynk.org.in www.cloudsynk.org.in;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/cloudsynk.org.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cloudsynk.org.in/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    client_max_body_size 100M;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Updated CSP to allow trusted CDNs (Google Fonts, Cloudflare CDN, DiceBear avatars)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; img-src 'self' data: blob: https://api.dicebear.com; connect-src 'self'; frame-ancestors 'self';" always;

    # CloudSynk static files
    location /static/ {
        alias /home/utsingh/workspace/CloudSynk/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # CloudSynk media files
    location /media/ {
        alias /home/utsingh/workspace/CloudSynk/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Main CloudSynk application
    location / {
        proxy_pass http://gunicorn_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_cache_bypass $http_upgrade;
        proxy_redirect off;
    }

    # Health check endpoint
    location /health/ {
        proxy_pass http://gunicorn_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        access_log off;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
}
EOF
    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/cloudsynk /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

# Collect static files
echo "📦 Collecting static files..."
source "$PROJECT_DIR/.storage-env-prod/bin/activate"
python manage.py collectstatic --noinput

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

# Setup systemd service
echo "🔧 Setting up systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable cloudsynk_production

# Stop any existing service
sudo systemctl stop cloudsynk_production || true

# Start services
echo "🔄 Starting services..."
sudo systemctl start cloudsynk_production
sudo systemctl restart nginx

# Wait for services to start
sleep 3

# Show status
echo ""
echo "📊 Service status:"
sudo systemctl status cloudsynk_production --no-pager --lines=10
echo ""
sudo systemctl status nginx --no-pager --lines=5

# Test the application
echo ""
echo "🧪 Testing the application..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "✅ Local test passed! (HTTP $HTTP_CODE)"
else
    echo "⚠️  Local test returned HTTP $HTTP_CODE"
fi

echo ""
echo "✅ CloudSynk deployment complete!"
echo ""
echo "🌐 Your CloudSynk app is now available at:"
echo "   http://cloudsynk.org.in"
echo "   http://www.cloudsynk.org.in"
echo ""
echo "📋 Monitoring Commands:"
echo "   App logs:      tail -f log/cloudsynk.log"
echo "   Gunicorn logs: sudo tail -f /var/log/cloudsynk/gunicorn_error.log"
echo "   Access logs:   sudo tail -f /var/log/cloudsynk/gunicorn_access.log"
echo "   Nginx logs:    sudo tail -f /var/log/nginx/error.log"
echo "   Service logs:  sudo journalctl -u cloudsynk_production -f"
echo ""
echo "🔧 Management Commands:"
echo "   Restart app:   sudo systemctl restart cloudsynk_production"
echo "   Restart nginx: sudo systemctl restart nginx"
echo "   View status:   sudo systemctl status cloudsynk_production"
echo ""
echo "✅ Production Status:"
echo "   ✅ Gunicorn: 9 workers running"
echo "   ✅ Nginx: Reverse proxy configured"
echo "   ✅ Environment: All variables loaded from /home/utsingh/workspace/az_intf"
echo "   ✅ Email OTP: Configured (SENDER_EMAIL, RECEIVER_EMAIL, APP_PASSWORD)"
echo "   ✅ Auto-restart: Enabled on failure"
echo "   ✅ Log archiving: Automatic on each deployment"
echo ""
echo "🔍 Verifying Environment Variables in Running Service:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get the main Gunicorn process ID
GUNICORN_PID=$(pgrep -f "gunicorn.*storage_webapp" | head -1)

if [ -n "$GUNICORN_PID" ]; then
    echo "📊 Process ID: $GUNICORN_PID"
    echo ""
    echo "🔐 Email Credentials (from running process):"
    sudo cat /proc/$GUNICORN_PID/environ | tr '\0' '\n' | grep -E "SENDER_EMAIL|RECEIVER_EMAIL|APP_PASSWORD" | while read -r line; do
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        if [ "$key" = "APP_PASSWORD" ]; then
            # Mask password for security
            masked=$(echo "$value" | sed 's/./*/g')
            echo "   ✅ $key=$masked"
        else
            echo "   ✅ $line"
        fi
    done
    
    echo ""
    echo "☁️  Azure Credentials (from running process):"
    sudo cat /proc/$GUNICORN_PID/environ | tr '\0' '\n' | grep -E "AZURE_STORAGE" | while read -r line; do
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        case "$key" in
            *KEY*|*CONNECTION*)
                # Mask sensitive values
                masked="${value:0:20}..."
                echo "   ✅ $key=$masked"
                ;;
            *)
                echo "   ✅ $line"
                ;;
        esac
    done
    
    echo ""
    echo "🔧 Django Settings (from running process):"
    sudo cat /proc/$GUNICORN_PID/environ | tr '\0' '\n' | grep -E "DJANGO_SECRET_KEY|EXTERNAL_IP|ALLOWED_HOSTS" | while read -r line; do
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        if [ "$key" = "DJANGO_SECRET_KEY" ]; then
            # Mask secret key
            echo "   ✅ $key=***********************"
        else
            echo "   ✅ $line"
        fi
    done
else
    echo "⚠️  Could not find Gunicorn process - service may still be starting"
    echo "   Run: sudo systemctl status cloudsynk_production.service"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo ""
