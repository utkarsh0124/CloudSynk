#!/bin/bash

# CloudSynk Production Deployment Script
# This script sets up and starts the production environment with Nginx and Gunicorn

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running from correct directory
if [ ! -f "env-setup-prod" ]; then
    error "env-setup-prod script not found. Please run this script from the CloudSynk root directory."
fi

# Parse command line arguments
FORCE_RESTART=false
SKIP_ENV_SETUP=false
VERBOSE=false

for arg in "$@"; do
    case $arg in
        --force-restart)
            FORCE_RESTART=true
            ;;
        --skip-env-setup)
            SKIP_ENV_SETUP=true
            ;;
        --verbose)
            VERBOSE=true
            ;;
        --help|-h)
            echo "CloudSynk Production Deployment Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force-restart     Force restart services even if they're running"
            echo "  --skip-env-setup    Skip environment setup (use existing venv)"
            echo "  --verbose           Show detailed output"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "This script will:"
            echo "  1. Set up production environment"
            echo "  2. Collect Django static files"
            echo "  3. Run database migrations"
            echo "  4. Start/restart Gunicorn service"
            echo "  5. Start/restart Nginx service"
            echo "  6. Perform health checks"
            exit 0
            ;;
    esac
done

log "🚀 Starting CloudSynk Production Deployment"
log "=============================================="

# Step 1: Environment Setup
if [ "$SKIP_ENV_SETUP" = false ]; then
    log "📦 Setting up production environment..."
    
    # Source the production environment setup
    if [ "$VERBOSE" = true ]; then
        source ./env-setup-prod
    else
        source ./env-setup-prod > /dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        log "✅ Production environment setup completed"
    else
        error "Failed to set up production environment"
    fi
else
    info "⏭️  Skipping environment setup as requested"
    # Still need to activate the venv
    source .storage-env-prod/bin/activate
fi

# Step 2: Verify Django Settings
log "🔧 Verifying Django configuration..."

export DJANGO_SECRET_KEY='b6$p5f5b%=-8!nifx9u2t&jxdel2ec&7n7b31qr&ag1wxx^h_m'
ALLOWED_HOSTS_LIST=("localhost" "127.0.0.1" "ubuntu-24")
if [ -n "$EXTERNAL_IP" ]; then
    ALLOWED_HOSTS_LIST+=("$EXTERNAL_IP")
fi
ALLOWED_HOSTS_LIST+=("www.cloudsynk.org.in" "cloudsynk.org.in")
export ALLOWED_HOSTS=$(IFS=,; echo "${ALLOWED_HOSTS_LIST[*]}")
export DJANGO_SETTINGS_MODULE='storage_webapp.settings_prod'

# Test Django configuration
python manage.py check --deploy --settings=storage_webapp.settings_prod > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log "✅ Django configuration is valid"
else
    warn "Django deployment check found issues (continuing anyway)"
fi

# Step 3: Database Migrations
log "🗄️  Running database migrations..."
python manage.py migrate --settings=storage_webapp.settings_prod
if [ $? -eq 0 ]; then
    log "✅ Database migrations completed"
else
    error "Database migrations failed"
fi

# Step 4: Collect Static Files
log "📁 Collecting static files..."
python manage.py collectstatic --noinput --settings=storage_webapp.settings_prod
if [ $? -eq 0 ]; then
    log "✅ Static files collected successfully"
else
    error "Failed to collect static files"
fi

# Step 5: Set up proper permissions
log "🔐 Setting up permissions..."
chmod 755 /home/utsingh/
chmod 755 /home/utsingh/run/
chown -R utsingh:www-data /home/utsingh/workspace/CloudSynk/log/
chown -R utsingh:www-data /home/utsingh/workspace/CloudSynk/staticfiles/
chown -R utsingh:www-data /home/utsingh/workspace/CloudSynk/media/
log "✅ Permissions set correctly"

# Step 6: Gunicorn Service Management
log "🦄 Managing Gunicorn service..."

# Check if Gunicorn service exists
if systemctl list-unit-files | grep -q "gunicorn_cloudsynk.service"; then
    if [ "$FORCE_RESTART" = true ] || ! systemctl is-active --quiet gunicorn_cloudsynk; then
        info "Restarting Gunicorn service..."
        sudo systemctl daemon-reload
        sudo systemctl restart gunicorn_cloudsynk
    else
        info "Gunicorn service is already running"
    fi
else
    error "Gunicorn service not found. Please ensure systemd service is installed."
fi

# Verify Gunicorn is running
sleep 3
if systemctl is-active --quiet gunicorn_cloudsynk; then
    log "✅ Gunicorn service is running"
else
    error "Gunicorn service failed to start"
fi

# Step 7: Nginx Service Management
log "🌐 Managing Nginx service..."

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    error "Nginx is not installed. Please install nginx first."
fi

# Check if CloudSynk site is enabled
if [ ! -L "/etc/nginx/sites-enabled/cloudsynk" ]; then
    warn "CloudSynk Nginx site not enabled. Please check Nginx configuration."
fi

# Restart Nginx
if [ "$FORCE_RESTART" = true ] || ! systemctl is-active --quiet nginx; then
    info "Starting/restarting Nginx..."
    sudo systemctl restart nginx
else
    info "Nginx is already running, reloading configuration..."
    sudo systemctl reload nginx
fi

# Verify Nginx is running
if systemctl is-active --quiet nginx; then
    log "✅ Nginx service is running"
else
    error "Nginx service failed to start"
fi

# Step 8: Health Checks
log "🏥 Performing health checks..."

# Check socket file
if [ -S "/home/utsingh/run/gunicorn_cloudsynk.sock" ]; then
    log "✅ Gunicorn socket file exists"
else
    error "Gunicorn socket file not found"
fi

# Test HTTP response
info "Testing HTTP response..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")

case $HTTP_STATUS in
    200)
        log "✅ Application responding with HTTP 200"
        ;;
    301|302)
        log "✅ Application responding with HTTP $HTTP_STATUS (redirect - this is normal for HTTPS redirect)"
        ;;
    000)
        error "Cannot connect to application"
        ;;
    *)
        warn "Application responding with HTTP $HTTP_STATUS (may indicate an issue)"
        ;;
esac

# Step 9: Service Status Summary
log "📊 Service Status Summary"
log "========================="

echo -e "\n${BLUE}Gunicorn Status:${NC}"
systemctl status gunicorn_cloudsynk --no-pager -l | head -10

echo -e "\n${BLUE}Nginx Status:${NC}"
systemctl status nginx --no-pager -l | head -10

# Step 10: Final Information
log "🎉 CloudSynk Production Deployment Completed!"
log "=============================================="

echo -e "\n${GREEN}✅ Your application is now running at:${NC}"
echo -e "   • HTTP:  http://localhost/"
echo -e "   • HTTP:  http://127.0.0.1/"
echo -e "   • HTTP:  http://ubuntu-24/ (if accessible)"

echo -e "\n${BLUE}📋 Service Management Commands:${NC}"
echo -e "   • Restart Gunicorn: sudo systemctl restart gunicorn_cloudsynk"
echo -e "   • Restart Nginx:    sudo systemctl restart nginx"
echo -e "   • View logs:        journalctl -u gunicorn_cloudsynk -f"
echo -e "   • Check status:     systemctl status gunicorn_cloudsynk nginx"

echo -e "\n${BLUE}📂 Important Paths:${NC}"
echo -e "   • Socket:      /home/utsingh/run/gunicorn_cloudsynk.sock"
echo -e "   • Static files: /home/utsingh/workspace/CloudSynk/staticfiles/"
echo -e "   • Logs:        /home/utsingh/workspace/CloudSynk/log/"
echo -e "   • Nginx config: /etc/nginx/sites-available/cloudsynk"

echo -e "\n${YELLOW}⚠️  Security Reminders:${NC}"
echo -e "   • Set up SSL/TLS certificates for HTTPS"
echo -e "   • Configure firewall (ufw allow 80/tcp 443/tcp)"
echo -e "   • Consider using a production database (PostgreSQL/MySQL)"
echo -e "   • Set up monitoring and log rotation"

log "🚀 Production deployment script completed successfully!"