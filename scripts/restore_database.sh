#!/bin/bash

# CloudSynk Database Restore Script
# This script restores a database backup

set -e

# Configuration
DB_DIR="${DB_DIR:-/var/lib/cloudsynk}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/cloudsynk}"
DB_FILE="$DB_DIR/db_prod.sqlite3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 CloudSynk Database Restore Script${NC}"
echo "========================================"

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}❌ Backup directory not found: $BACKUP_DIR${NC}"
    exit 1
fi

# List available backups
echo -e "${GREEN}📚 Available backups:${NC}"
BACKUPS=($(find "$BACKUP_DIR" -name "db_prod_*.sqlite3.gz" -type f | sort -r))

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo -e "${RED}❌ No backups found!${NC}"
    exit 1
fi

# Display backups with numbers
i=1
for backup in "${BACKUPS[@]}"; do
    backup_date=$(basename "$backup" | sed 's/db_prod_\(.*\)\.sqlite3\.gz/\1/')
    backup_size=$(du -h "$backup" | cut -f1)
    echo "  $i) $backup_date ($backup_size)"
    i=$((i+1))
done

# Ask user to select backup or use parameter
if [ -z "$1" ]; then
    echo ""
    echo -e "${YELLOW}Select backup to restore (1-${#BACKUPS[@]}) or 'latest' for most recent:${NC}"
    read -r selection
    
    if [ "$selection" = "latest" ]; then
        BACKUP_FILE="${BACKUPS[0]}"
    elif [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#BACKUPS[@]} ]; then
        BACKUP_FILE="${BACKUPS[$((selection-1))]}"
    else
        echo -e "${RED}❌ Invalid selection!${NC}"
        exit 1
    fi
else
    if [ "$1" = "latest" ]; then
        BACKUP_FILE="${BACKUPS[0]}"
    elif [ -f "$1" ]; then
        BACKUP_FILE="$1"
    else
        echo -e "${RED}❌ Backup file not found: $1${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}⚠️  WARNING: This will replace the current database!${NC}"
echo -e "Selected backup: $(basename "$BACKUP_FILE")"
echo ""
echo -e "${RED}Do you want to continue? (yes/no):${NC}"
read -r confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Restore cancelled.${NC}"
    exit 0
fi

# Create a backup of current database before restoring
if [ -f "$DB_FILE" ]; then
    echo -e "${YELLOW}📦 Creating backup of current database...${NC}"
    CURRENT_BACKUP="$BACKUP_DIR/pre_restore_$(date +"%Y%m%d_%H%M%S").sqlite3"
    sqlite3 "$DB_FILE" ".backup '$CURRENT_BACKUP'"
    gzip "$CURRENT_BACKUP"
    echo -e "${GREEN}✅ Current database backed up to: ${CURRENT_BACKUP}.gz${NC}"
fi

# Restore the backup
echo -e "${YELLOW}🔄 Restoring database...${NC}"

# Decompress and restore
gunzip -c "$BACKUP_FILE" > /tmp/restore_db.sqlite3

# Verify integrity before restoring
if sqlite3 /tmp/restore_db.sqlite3 "PRAGMA integrity_check;" | grep -q "ok"; then
    echo -e "${GREEN}✅ Backup integrity verified${NC}"
    
    # Stop any services using the database
    echo -e "${YELLOW}⏸️  Stopping services...${NC}"
    sudo systemctl stop cloudsynk_production 2>/dev/null || true
    
    # Restore the database
    sudo mkdir -p "$DB_DIR"
    sudo mv /tmp/restore_db.sqlite3 "$DB_FILE"
    sudo chown utsingh:utsingh "$DB_FILE"
    sudo chmod 664 "$DB_FILE"
    
    # Optimize database
    echo -e "${YELLOW}⚙️  Optimizing database...${NC}"
    sqlite3 "$DB_FILE" "VACUUM;"
    sqlite3 "$DB_FILE" "PRAGMA optimize;"
    
    # Restart services
    echo -e "${YELLOW}▶️  Restarting services...${NC}"
    sudo systemctl start cloudsynk_production 2>/dev/null || true
    
    echo -e "${GREEN}✅ Database restored successfully!${NC}"
    
    # Create restore log
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Database restored from: $BACKUP_FILE" >> "$BACKUP_DIR/restore.log"
else
    echo -e "${RED}❌ Backup integrity check failed! Restore aborted.${NC}"
    rm /tmp/restore_db.sqlite3
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Restore completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
