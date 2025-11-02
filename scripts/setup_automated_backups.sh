#!/bin/bash

# Setup automated database backups using cron
# This script configures cron jobs for database backups

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🕐 Setting up automated database backups${NC}"
echo "========================================"

PROJECT_DIR="/home/utsingh/workspace/CloudSynk"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_database.sh"

# Make backup scripts executable
chmod +x "$PROJECT_DIR/scripts/backup_database.sh"
chmod +x "$PROJECT_DIR/scripts/restore_database.sh"

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}❌ Backup script not found: $BACKUP_SCRIPT${NC}"
    exit 1
fi

# Create cron job entry
# Schedule: Daily at 3:00 AM IST (21:30 UTC, since IST = UTC+5:30)
# System timezone: Cron uses UTC time
# To run at 3:00 AM IST = 21:30 previous day in UTC
CRON_JOB="30 21 * * * $BACKUP_SCRIPT >> /var/log/cloudsynk/backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo -e "${YELLOW}⚠️  Cron job already exists. Updating...${NC}"
    # Remove old entry and add new one
    (crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT"; echo "$CRON_JOB") | crontab -
else
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
fi

echo -e "${GREEN}✅ Automated backup scheduled!${NC}"
echo ""
echo -e "${GREEN}Backup schedule:${NC}"
echo "  • Daily at 3:00 AM IST (21:30 UTC)"
echo "  • Logs: /var/log/cloudsynk/backup.log"
echo ""
echo -e "${GREEN}Current cron jobs:${NC}"
crontab -l | grep -v "^#" | grep -v "^$"

echo ""
echo -e "${GREEN}Manual backup commands:${NC}"
echo "  • Create backup:  $BACKUP_SCRIPT"
echo "  • Restore backup: $PROJECT_DIR/scripts/restore_database.sh"
echo ""
echo -e "${GREEN}========================================${NC}"
