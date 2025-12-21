# Deployment Guide

Quick reference for deploying your Finding-Memo backend with MariaDB.

## Prerequisites
- MySQL/MariaDB client tools installed (`mysql`, `mysqldump`)
- `.env` file configured with `SQLALCHEMY_DATABASE_URI`

---

## 🎯 Quick Start: Automated Deployment

The easiest way to deploy is using the automated deployment script:

```bash
# Create deployment package with code only
python deploy/deploy.py

# Create deployment package with database export
python deploy/deploy.py --with-data

# Custom filename
python deploy/deploy.py --output prod_v2.zip --with-data
```

**This automatically:**
- ✓ Packages only production files (excludes tests, cache, logs)
- ✓ Includes all necessary code (`app/`, `migrations/`)
- ✓ Optionally exports and includes database
- ✓ Shows deployment instructions when done
- ✓ Creates clean ZIP ready to upload

**Then on server:** Extract ZIP and follow the instructions shown by the script.

---

## Common Deployment Scenarios

### 🚀 Scenario 1: First Time Deployment (Fresh Server)

**When:** Deploying to a new server with no existing database

**Steps:**
1. Create database on server:
   ```sql
   CREATE DATABASE finding_memo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Option A: Deploy with your local data**
   ```bash
   # Locally
   python deploy/export_db.py production_deploy.sql

   # On server (after uploading files)
   python deploy/import_db_from_sql.py production_deploy.sql
   ```

   **Option B: Deploy schema only (empty database)**
   ```bash
   # On server
   flask db upgrade
   flask shell  # Create superuser (see README step 5)
   ```

---

### 📦 Scenario 2: Regular Deployment (Server Already Running)

**When:** Deploying code changes to existing production server

**If database schema changed:**
```bash
# Locally (after making model changes)
flask db migrate -m "describe changes"
git add migrations/
git commit -m "Add migration: describe changes"

# On server (after deploying code)
flask db upgrade
```

**If only code changed (no schema changes):**
```bash
# Just deploy your code files
# No database steps needed!
```

---

### 🔄 Scenario 3: Copy Production Data to Local

**When:** You want to debug with production data locally

```bash
# On production server
python deploy/export_db.py prod_backup.sql
# Download prod_backup.sql to local machine

# Locally (⚠️ this will overwrite local data!)
python deploy/import_db_from_sql.py prod_backup.sql
```

---

### 💾 Scenario 4: Regular Backups

**Create automatic backup:**
```bash
python deploy/export_db.py  # Creates db_backup_YYYYMMDD_HHMMSS.sql
```

**Restore from backup:**
```bash
python deploy/import_db_from_sql.py db_backup_20231215_120000.sql
```

**Tip:** Add to crontab for automatic daily backups:
```bash
0 2 * * * cd /path/to/backend && python deploy/export_db.py
```

---

## Migration Commands Quick Reference

```bash
# Check current database version
flask db current

# View migration history
flask db history

# Create new migration after model changes
flask db migrate -m "description of changes"

# Apply pending migrations
flask db upgrade

# Rollback last migration (use with caution!)
flask db downgrade

# Show SQL that would be executed (without running)
flask db upgrade --sql
```

---

## Troubleshooting

### "mysqldump: command not found"
Install MySQL/MariaDB client:
- **Ubuntu/Debian:** `sudo apt install mysql-client`
- **macOS:** `brew install mysql-client`
- **Windows:** Install MySQL from mysql.com or use XAMPP/WAMP

### Import fails with "Access denied"
Check your `.env` file has correct credentials in `SQLALCHEMY_DATABASE_URI`

### Migration conflicts
If you get migration conflicts:
```bash
flask db merge heads  # Merge conflicting migration heads
flask db upgrade
```

---

## Best Practices

1. ✅ **Always backup before migrations in production**
   ```bash
   python deploy/export_db.py before_migration_backup.sql
   flask db upgrade
   ```

2. ✅ **Test migrations locally first**
   - Test on local database before production
   - Review generated migration files
   - Check for data loss risks

3. ✅ **Keep migrations in version control**
   - Commit migration files to git
   - Never edit applied migrations

4. ✅ **Use descriptive migration messages**
   ```bash
   flask db migrate -m "add user avatar and reset token fields"
   ```

5. ✅ **Regular backups**
   - Export database regularly (daily recommended)
   - Keep backups off-server
   - Test restore process occasionally

---

## File Summary

- **[export_db.py](export_db.py)** - Export database to SQL file
- **[import_db_from_sql.py](import_db_from_sql.py)** - Import SQL file to database
- **migrations/** - Alembic migration files (managed by Flask-Migrate)
