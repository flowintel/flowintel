# Flowintel backup and restore

## Introduction

Regular backups are essential for protecting your Flowintel case management data against hardware failures, data corruption, accidental deletion, or security incidents. This document describes best practices for backing up and restoring Flowintel installations.

A complete Flowintel backup consists of two components:

1. **File system backup**: Application files, uploads, configurations, and logs
2. **Database backup**: Case data, users, tasks, and audit information

## Backup strategy

### Backup frequency and retention

Flowintel uses a daily backup approach:

- **Daily backups**: Full backup of database and file system
- **Retention**: Backups are retained for 14 days

Adjust the retention period based on your organisation's compliance requirements and available storage capacity.

### Backup storage location

All backups are stored in `/opt/flowintel/backups`:

```
/opt/flowintel/backups/
└── daily/          # Daily database and file backups
```

**Important**: The backup directory is on the same server as Flowintel. This provides fast local recovery but does not protect against server-level failures. See the "External backup storage" section for offsite backup options.

## Virtual machine snapshots

### Overview

If Flowintel is running on a virtual machine (VMware, Hyper-V, Proxmox, KVM, Azure, AWS, etc.), configure regular VM snapshots as an additional layer of protection.

**Important**: VM snapshots are not a replacement for file and database backups. They complement each other:

- **VM snapshots**: Fast disaster recovery, complete system restoration
- **File/database backups**: Granular recovery, long-term retention, platform-independent

## Prerequisites

Before configuring backups, ensure you have:

- [ ] Sufficient disk space in `/opt/flowintel` for backup storage
- [ ] Root or sudo access for backup configuration
- [ ] PostgreSQL administrative access (for database backups)
- [ ] Flowintel installation at `/opt/flowintel/flowintel`

Check available disk space:

```bash
df -h /opt/flowintel
```

You need at least 2-3 times the current data size available for backups and rotation.

## Prepare your system for backups

### Create backup directory structure

Set up the backup directory structure with permissions that allow both the Flowintel user and postgres user to write backups:

```bash
# Create backup directory
sudo mkdir -p /opt/flowintel/backups/daily

# Set ownership (replace 'yourusername' with the Flowintel user)
sudo chown -R yourusername:postgres /opt/flowintel/backups

# Set group write permissions
sudo chmod 775 /opt/flowintel/backups
sudo chmod 775 /opt/flowintel/backups/daily

# Create log file with group write permissions
sudo touch /opt/flowintel/backups/backup.log
sudo chown yourusername:postgres /opt/flowintel/backups/backup.log
sudo chmod 664 /opt/flowintel/backups/backup.log

# Add Flowintel user to postgres group
sudo usermod -a -G postgres yourusername
```

**Note**: The backup directory is owned by the Flowintel user with the postgres group, allowing both users to write backups to the same location.

### Daily backup script

Install the daily backup script

```bash
# Copy from Flowintel
sudo cp /opt/flowintel/flowintel/doc/backup.sh /opt/flowintel/backups/backup.sh

# Make it executable
sudo chmod +x /opt/flowintel/backups/backup.sh

# Test the backup script:
sudo /opt/flowintel/backups/backup.sh
```

## Backup scheduling

Set up automated daily backups using cron. The script runs as root because it needs to stop/start Flowintel:

```bash
sudo vi /etc/crontab
```

Add:

```bash
# Daily backup at 2:00 AM
0 2 * * * root /opt/flowintel/backups/backup.sh
```

## Verifying backups

### Test backup integrity

Verify file and database backup:

```bash
# File system
tar -tzf /opt/flowintel/backups/daily/flowintel_files_20260130_020001.tar.gz | head -20

# Database
gunzip -c /opt/flowintel/backups/daily/flowintel_db_20260130_020001.sql.gz | head -20
```

### Monitor backup logs

Check backup logs regularly:

```bash
tail -50 /opt/flowintel/backups/backup.log
```

## External backup storage

Backups stored on the same server as Flowintel do not protect against server failures, disk failures, or site-level disasters. You should implement one or more of the following external backup strategies:

- **Remote server sync with rsync**: Synchronise backups to a remote backup server using rsync over SSH
- **Mount remote storage**: Mount a remote NFS or CIFS/SMB share at `/opt/flowintel/backups`
- **Cloud storage**: Upload backups to cloud providers such as Azure Blob Storage, AWS S3, or Google Cloud Storage

## Restore procedures

### Database restore

Stop Flowintel:

```bash
sudo systemctl stop flowintel
```

Drop and recreate the database (optional, only if restoring to a clean state):

```bash
sudo -u postgres psql

DROP DATABASE flowintel;
CREATE DATABASE flowintel OWNER flowintel;
\q
```

Restore from backup:

```bash
gunzip -c /opt/flowintel/backups/daily/flowintel_db_20260130_020001.sql.gz | sudo -u postgres psql flowintel
```

### File system restore

Extract the backup:

```bash
cd /opt/flowintel
tar -xzf backups/daily/flowintel_files_20260130_030001.tar.gz
```

Set correct permissions:

```bash
sudo chown -R yourusername:yourusername /opt/flowintel/flowintel
sudo chmod 750 /opt/flowintel/flowintel
```

### Restart services

Restart Flowintel:

```bash
sudo systemctl start flowintel
```
