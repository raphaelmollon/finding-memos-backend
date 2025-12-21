# Deployment Tools

All deployment-related scripts and documentation for the Finding-Memo backend.

## Quick Start

```bash
# Create deployment package (from backend/ directory)
python deploy/deploy.py --with-data
```

## Files in This Folder

### Scripts
- **[deploy.py](deploy.py)** - Automated deployment packager
- **[export_db.py](export_db.py)** - Database export tool
- **[import_db_from_sql.py](import_db_from_sql.py)** - Database import tool

### Documentation
- **[README_DEPLOYMENT.md](README_DEPLOYMENT.md)** - **START HERE** - Overview and quick reference
- **[DEPLOY_QUICK_REF.md](DEPLOY_QUICK_REF.md)** - One-page quick reference card
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Detailed deployment scenarios
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Pre/post deployment checklist
- **[deployment_summary.txt](deployment_summary.txt)** - Complete feature summary
- **[DEPLOYMENT_FLOW.txt](DEPLOYMENT_FLOW.txt)** - Visual workflow diagrams

## Common Commands

All commands should be run from the `backend/` directory (parent of this folder):

```bash
# Deploy with data
python deploy/deploy.py --with-data

# Deploy code only
python deploy/deploy.py

# Export database
python deploy/export_db.py

# Import database
python deploy/import_db_from_sql.py backup.sql
```

## Documentation Guide

**New to deployment?** Read [README_DEPLOYMENT.md](README_DEPLOYMENT.md)

**Need quick reference?** Check [DEPLOY_QUICK_REF.md](DEPLOY_QUICK_REF.md)

**Detailed scenarios?** See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**About to deploy?** Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

**Visual learner?** Look at [DEPLOYMENT_FLOW.txt](DEPLOYMENT_FLOW.txt)
