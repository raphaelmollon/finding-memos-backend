# Deployment Tools

## TL;DR - Quick Deploy

```bash
python deploy/deploy.py --with-data
```

Upload the ZIP to your server, extract, and import the database. Done!

---

## What's This?

This folder contains automated deployment tools for your Finding-Memo backend with MariaDB.

### The Problem
Previously with SQLite, you just copied the `.db` file with your code and deployed. With MariaDB, you need to handle database separately.

### The Solution
Simple scripts that automate everything:

1. **[deploy.py](deploy.py)** - Creates clean deployment packages
2. **[export_db.py](export_db.py)** - Exports database to SQL file
3. **[import_db_from_sql.py](import_db_from_sql.py)** - Imports SQL file to database

---

## Quick Commands

| What you want | Command | Result |
|---------------|---------|--------|
| Deploy with data | `python deploy/deploy.py --with-data` | ZIP with code + database |
| Deploy code only | `python deploy/deploy.py` | ZIP with code only |
| Backup database | `python deploy/export_db.py` | SQL backup file |
| Restore database | `python deploy/import_db_from_sql.py backup.sql` | Database restored |

---

## Documentation Files

- **[deployment_summary.txt](deployment_summary.txt)** - Start here! Overview of everything
- **[DEPLOY_QUICK_REF.md](DEPLOY_QUICK_REF.md)** - One-page reference card
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Detailed scenarios and troubleshooting
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Pre/post deployment checklist

---

## Two Deployment Approaches

### Approach 1: Data Export (Like SQLite)
**When:** First deployment, or copying local data to server

```bash
# Locally
python deploy/deploy.py --with-data

# On server
python deploy/import_db_from_sql.py deploy_db_*.sql
```

### Approach 2: Migrations (Better for Updates)
**When:** Schema changes, updating production

```bash
# Locally
flask db migrate -m "changes"
python deploy/deploy.py

# On server
flask db upgrade
```

---

## What Gets Deployed?

### Included ✅
- All your code (`app/`, `migrations/`)
- Dependencies (`requirements.txt`)
- Config template (`.env.example`)
- Database tools (export/import scripts)
- Documentation

### Excluded ❌
- Tests
- Your actual `.env` file (security!)
- Cache, logs, backups
- Git files
- Local databases

---

## Examples

**First time deploying:**
```bash
python deploy/deploy.py --with-data --output production_v1.0.0.zip
```

**Regular code update:**
```bash
python deploy/deploy.py --output update_v1.0.1.zip
```

**Schema changed (added new column):**
```bash
flask db migrate -m "add new column"
python deploy/deploy.py --output update_v1.1.0.zip
# On server: flask db upgrade
```

**Just backup database:**
```bash
python deploy/export_db.py backup_before_changes.sql
```

---

## Need Help?

1. Read [deployment_summary.txt](deployment_summary.txt) for complete overview
2. Check [DEPLOY_QUICK_REF.md](DEPLOY_QUICK_REF.md) for quick reference
3. See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed scenarios
4. Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) before deploying

---

## Safety Features

- Database imports require confirmation (can't accidentally overwrite)
- `.env` file never included in packages (security)
- Shows all included files before creating ZIP
- Provides deployment instructions after package creation
- Excludes test files and development artifacts automatically

---

## Requirements

- Python 3.x
- MySQL/MariaDB client tools (`mysql`, `mysqldump`)
- Configured `.env` file with database connection

---

**That's it! Your MariaDB deployment is now as simple as SQLite was.**
