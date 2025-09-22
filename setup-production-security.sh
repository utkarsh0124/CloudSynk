#!/bin/bash

# CloudSynk Production Security Configuration
# Run this script to apply security hardening measures

echo "🔒 CloudSynk Production Security Configuration"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create secure directory
create_secure_dir() {
    local dir=$1
    local owner=${2:-www-data}
    local perms=${3:-755}
    
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        chown "$owner:$owner" "$dir"
        chmod "$perms" "$dir"
        echo "✅ Created secure directory: $dir"
    fi
}

# 1. File Permissions
echo "1. Setting secure file permissions..."
chmod 600 env-setup-prod  # Only owner can read/write
chmod 644 storage_webapp/settings_prod.py
chmod 755 manage.py

# Create secure directories
create_secure_dir "logs" "www-data" "755"
create_secure_dir "media" "www-data" "755"
create_secure_dir "staticfiles" "www-data" "755"
create_secure_dir "cache" "www-data" "755"

# 2. Environment Variable Template
echo "2. Creating environment variable template..."
cat > .env.production.template << 'EOF'
# CloudSynk Production Environment Variables
# Copy this to .env.production and fill in the values

# Django Core Settings
DJANGO_SECRET_KEY=your-super-secret-key-here-generate-new-one
DEBUG=false
DJANGO_ENV=production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/cloudsynk_prod
# DATABASE_URL=mysql://user:password@localhost:3306/cloudsynk_prod

# Security Settings
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true

# Email Configuration (for error notifications)
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com

# Cache Configuration
REDIS_URL=redis://localhost:6379/0

# File Upload Limits
FILE_UPLOAD_MAX_SIZE=52428800  # 50MB in bytes
MAX_UPLOAD_SIZE=52428800

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn-here

# Azure Configuration (from ../az_intf)
# These should already be available from source ../az_intf
# AZURE_STORAGE_ACCOUNT_NAME=
# AZURE_STORAGE_ACCOUNT_KEY=
# AZURE_STORAGE_ENDPOINT_SUFFIX=
EOF

echo "✅ Created .env.production.template"

# 3. Nginx Configuration Template
echo "3. Creating nginx configuration template..."
cat > nginx.cloudsynk.conf << 'EOF'
# CloudSynk Nginx Configuration
# Place this in /etc/nginx/sites-available/cloudsynk

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self';" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /login/ {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /path/to/cloudsynk/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /path/to/cloudsynk/media/;
        # Security: Don't execute files in media directory
        location ~* \.(php|py|pl|sh)$ {
            deny all;
        }
    }
}
EOF

echo "✅ Created nginx.cloudsynk.conf"

# 4. Systemd Service File
echo "4. Creating systemd service file..."
cat > cloudsynk.service << 'EOF'
[Unit]
Description=CloudSynk Django Application
After=network.target postgresql.service redis.service
Requires=postgresql.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/cloudsynk
Environment=DJANGO_SETTINGS_MODULE=storage_webapp.settings_prod
EnvironmentFile=/path/to/cloudsynk/.env.production
ExecStart=/path/to/cloudsynk/.storage-env-prod/bin/gunicorn storage_webapp.wsgi:application --bind 127.0.0.1:8000 --workers 3 --worker-class sync --timeout 60 --max-requests 1000 --max-requests-jitter 100
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/path/to/cloudsynk/logs /path/to/cloudsynk/media /path/to/cloudsynk/cache
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created cloudsynk.service"

# 5. Log Rotation Configuration
echo "5. Creating logrotate configuration..."
cat > cloudsynk.logrotate << 'EOF'
/path/to/cloudsynk/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload cloudsynk
    endscript
}
EOF

echo "✅ Created cloudsynk.logrotate"

# 6. Security Check Script
echo "6. Creating security check script..."
cat > check-security.sh << 'EOF'
#!/bin/bash

echo "🔍 CloudSynk Security Check"
echo "=========================="

# Check Django deployment
echo "1. Checking Django deployment settings..."
python manage.py check --deploy --settings=storage_webapp.settings_prod

# Check file permissions
echo "2. Checking file permissions..."
find . -name "*.py" -perm /022 -exec echo "WARNING: {} has world-writable permissions" \;
find . -name "env-setup*" -perm /044 -exec echo "WARNING: {} should not be readable by others" \;

# Check for hardcoded secrets
echo "3. Checking for potential hardcoded secrets..."
grep -r "password\|secret\|key" --include="*.py" . | grep -v "settings_prod.py" | grep -v "SECRET_KEY = os.environ" || echo "No hardcoded secrets found"

# Check SSL certificate (if nginx is configured)
echo "4. Checking SSL configuration..."
if command -v nginx >/dev/null 2>&1; then
    nginx -t && echo "✅ Nginx configuration is valid" || echo "❌ Nginx configuration has errors"
fi

echo "Security check completed!"
EOF

chmod +x check-security.sh
echo "✅ Created check-security.sh"

# 7. Deployment Script
echo "7. Creating deployment script..."
cat > deploy-prod.sh << 'EOF'
#!/bin/bash

set -e  # Exit on any error

echo "🚀 CloudSynk Production Deployment"
echo "=================================="

# Load production environment
source env-setup-prod

# Check environment variables
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "❌ DJANGO_SECRET_KEY not set"
    exit 1
fi

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --settings=storage_webapp.settings_prod

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --settings=storage_webapp.settings_prod

# Create superuser if needed
if [ "$1" = "--create-superuser" ]; then
    echo "👤 Creating superuser..."
    python manage.py createsuperuser --settings=storage_webapp.settings_prod
fi

# Run security checks
echo "🔍 Running security checks..."
python manage.py check --deploy --settings=storage_webapp.settings_prod

echo "✅ Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy systemd service: sudo cp cloudsynk.service /etc/systemd/system/"
echo "2. Enable service: sudo systemctl enable cloudsynk"
echo "3. Start service: sudo systemctl start cloudsynk"
echo "4. Configure nginx: sudo cp nginx.cloudsynk.conf /etc/nginx/sites-available/cloudsynk"
echo "5. Enable nginx site: sudo ln -s /etc/nginx/sites-available/cloudsynk /etc/nginx/sites-enabled/"
echo "6. Restart nginx: sudo systemctl restart nginx"
EOF

chmod +x deploy-prod.sh
echo "✅ Created deploy-prod.sh"

echo ""
echo "🎉 Production security configuration completed!"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Review and edit .env.production.template"
echo "2. Copy to .env.production and set real values"
echo "3. Update paths in nginx.cloudsynk.conf and cloudsynk.service"
echo "4. Run ./check-security.sh to verify configuration"
echo "5. Run ./deploy-prod.sh to deploy"
echo ""
echo "⚠️  IMPORTANT: Test everything in a staging environment first!"