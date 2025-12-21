# Quick Deployment Reference

All deployment tools and documentation are in the **[deploy/](deploy/)** folder.

## Quick Commands

```bash
# Create deployment package with data
python deploy/deploy.py --with-data

# Create deployment package (code only)
python deploy/deploy.py

# Create and upload to FTP server
python deploy/deploy.py --with-data --send

# Export database
python deploy/export_db.py

# Import database
python deploy/import_db_from_sql.py backup.sql
```

## Documentation

See the **[deploy/](deploy/)** folder for complete documentation:

- **[deploy/README_DEPLOYMENT.md](deploy/README_DEPLOYMENT.md)** - Start here! Complete overview
- **[deploy/DEPLOY_QUICK_REF.md](deploy/DEPLOY_QUICK_REF.md)** - One-page reference
- **[deploy/DEPLOYMENT_GUIDE.md](deploy/DEPLOYMENT_GUIDE.md)** - Detailed scenarios
- **[deploy/DEPLOYMENT_CHECKLIST.md](deploy/DEPLOYMENT_CHECKLIST.md)** - Deployment checklist
- **[deploy/DEPLOYMENT_FLOW.txt](deploy/DEPLOYMENT_FLOW.txt)** - Visual workflows

## What Gets Deployed?

When you run `python deploy/deploy.py`, it creates a ZIP containing:

✅ **Included:**
- All code (`app/`, `migrations/`)
- Deploy tools (`deploy/` folder)
- Config template (`.env.example`)
- Documentation

❌ **Excluded:**
- Tests, cache, logs
- Your `.env` file (security!)
- Git files, backups
- Development artifacts

## Simple as SQLite

Just like copying your `.db` file before, but better:

```bash
# Old way (SQLite)
cp myapp.db /server/

# New way (MariaDB)
python deploy/deploy.py --with-data
# Upload deploy_YYYYMMDD_HHMMSS.zip to server
```

**See [deploy/README_DEPLOYMENT.md](deploy/README_DEPLOYMENT.md) for complete guide.**
