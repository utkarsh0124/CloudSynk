#!/bin/bash

# CloudSynk Database Backup Script
# This script creates backups of the production SQLite database
# For production use, consider using a proper database with built-in backup solutions

set -e

# Configuration
DB_DIR="${DB_DIR:-/var/lib/cloudsynk}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/cloudsynk}"
DB_FILE="$DB_DIR/db_prod.sqlite3"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=${RETENTION_DAYS:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔒 CloudSynk Database Backup Script${NC}"
echo "========================================"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}❌ Database file not found: $DB_FILE${NC}"
    exit 1
fi

# Create backup directory if it doesn't exist
sudo mkdir -p "$BACKUP_DIR"
sudo chown utsingh:utsingh "$BACKUP_DIR"

# Get database size
DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
echo -e "${GREEN}📊 Database size: $DB_SIZE${NC}"

# Create backup
BACKUP_FILE="$BACKUP_DIR/db_prod_${TIMESTAMP}.sqlite3"
echo -e "${YELLOW}📦 Creating backup...${NC}"

# Use sqlite3 to create a proper backup (handles locks)
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"

if [ $? -eq 0 ]; then
    # Compress the backup
    echo -e "${YELLOW}🗜️  Compressing backup...${NC}"
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
    echo -e "${GREEN}   Backup size: $BACKUP_SIZE${NC}"
    
    # Create a 'latest' symlink for easy access
    sudo ln -sf "$BACKUP_FILE" "$BACKUP_DIR/latest_backup.sqlite3.gz"
    
    # Clean up old backups
    echo -e "${YELLOW}🧹 Cleaning up backups older than $RETENTION_DAYS days...${NC}"
    find "$BACKUP_DIR" -name "db_prod_*.sqlite3.gz" -type f -mtime +$RETENTION_DAYS -delete
    
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "db_prod_*.sqlite3.gz" -type f | wc -l)
    echo -e "${GREEN}📚 Total backups retained: $BACKUP_COUNT${NC}"
    
    # Create backup log
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup created: $BACKUP_FILE" >> "$BACKUP_DIR/backup.log"
    
    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

# Show recent backups
echo ""
echo -e "${GREEN}📋 Recent backups:${NC}"
ls -lht "$BACKUP_DIR"/db_prod_*.sqlite3.gz 2>/dev/null | head -5 || echo "No backups found"

# Integrity check
echo ""
echo -e "${YELLOW}🔍 Running integrity check on backup...${NC}"
gunzip -c "$BACKUP_FILE" > /tmp/check_db.sqlite3
if sqlite3 /tmp/check_db.sqlite3 "PRAGMA integrity_check;" | grep -q "ok"; then
    echo -e "${GREEN}✅ Backup integrity verified${NC}"
    rm /tmp/check_db.sqlite3
else
    echo -e "${RED}⚠️  Warning: Backup integrity check failed!${NC}"
    rm /tmp/check_db.sqlite3
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup Summary:${NC}"
echo -e "  Database: $DB_FILE"
echo -e "  Backup: $BACKUP_FILE"
echo -e "  Size: $BACKUP_SIZE"
echo -e "  Retention: $RETENTION_DAYS days"
echo -e "${GREEN}========================================${NC}"
