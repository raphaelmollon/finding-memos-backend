# Deployment Checklist

Use this checklist before each deployment to ensure smooth releases.

## Pre-Deployment (Local)

### Code Review
- [ ] All tests passing (`pytest`)
- [ ] No debug code or print statements left
- [ ] No hardcoded passwords or secrets
- [ ] `.env.example` is up to date with new variables

### Database
- [ ] Models changed? Created migration: `flask db migrate -m "description"`
- [ ] Migration tested locally: `flask db upgrade`
- [ ] Migration reviewed for data loss risks
- [ ] Migration files committed to git

### Dependencies
- [ ] New packages added to `requirements.txt`
- [ ] No unused dependencies

### Documentation
- [ ] README updated if setup process changed
- [ ] API changes documented
- [ ] Deployment notes added if special steps needed

---

## Create Deployment Package

### Choose Deployment Type

**First deployment or want to copy data:**
```bash
python deploy.py --with-data --output prod_vX.X.X.zip
```

**Regular update (migrations only):**
```bash
python deploy.py --output prod_vX.X.X.zip
```

### Verify Package
- [ ] ZIP created successfully
- [ ] Check file size is reasonable (< 5MB typically)
- [ ] Review included files list in output

---

## Backup Production (Before Deploying)

**CRITICAL: Always backup production before deploying!**

On production server:
```bash
python export_db.py pre_deploy_backup_YYYYMMDD.sql
```

- [ ] Production database backed up
- [ ] Backup file downloaded to safe location
- [ ] Backup file tested (can be imported if needed)

---

## Deploy to Server

### Upload and Extract
- [ ] Upload ZIP to server
- [ ] Extract: `unzip prod_vX.X.X.zip`
- [ ] Verify all files extracted correctly

### Configuration
- [ ] `.env` file configured with production values
- [ ] Database connection string correct
- [ ] Email settings configured
- [ ] CORS origins set correctly
- [ ] `FLASK_ENV=production` set
- [ ] Secret keys are production-grade (not dev keys)

### Database Setup

**If deployed with data (--with-data):**
- [ ] Import database: `python import_db_from_sql.py deploy_db_*.sql`
- [ ] Verify import successful

**If using migrations:**
- [ ] Run migrations: `flask db upgrade`
- [ ] Check migration output for errors
- [ ] If fresh install: Create superuser

### Dependencies
- [ ] Install packages: `pip install -r requirements.txt`
- [ ] Verify no installation errors
- [ ] Check Python version compatibility

### Application
- [ ] WSGI configured correctly
- [ ] Application starts without errors
- [ ] Check logs for startup issues

---

## Post-Deployment Verification

### Smoke Tests
- [ ] Application accessible via web
- [ ] Can login with existing user
- [ ] Can create new user (if auth enabled)
- [ ] Can create/read/update/delete memos
- [ ] Avatar upload works
- [ ] Email sending works (password reset)
- [ ] API endpoints responding correctly

### Database
- [ ] Data intact (spot check critical records)
- [ ] New migrations applied: `flask db current`
- [ ] No error logs related to database

### Monitoring
- [ ] Check error logs for issues
- [ ] Verify no unusual activity
- [ ] Monitor performance (response times)

---

## Rollback Plan (If Something Goes Wrong)

### Quick Rollback
1. Stop application
2. Restore previous code version
3. Restore database backup:
   ```bash
   python import_db_from_sql.py pre_deploy_backup_YYYYMMDD.sql
   ```
4. Restart application
5. Verify rollback successful

### If Migration Failed
```bash
flask db downgrade  # Rollback last migration
# Or restore from backup
```

---

## Post-Deployment Tasks

### Documentation
- [ ] Update deployment log with version and date
- [ ] Document any issues encountered
- [ ] Note any manual steps performed

### Cleanup
- [ ] Remove old deployment ZIPs from server (keep 2-3 recent)
- [ ] Archive old backups (keep last 7-14 days)
- [ ] Clean up temporary files

### Monitoring
- [ ] Monitor for first 24 hours
- [ ] Check error rates
- [ ] Verify user activity normal

---

## Emergency Contacts

Production Server:
- Host: _____________________
- SSH: _____________________
- Database: _____________________

Key People:
- Developer: _____________________
- DBA: _____________________
- DevOps: _____________________

---

## Common Issues & Solutions

**Issue: Migration fails**
- Solution: Restore backup, review migration, fix locally, redeploy

**Issue: Database connection fails**
- Solution: Check `.env` connection string, verify database service running

**Issue: Import errors (missing modules)**
- Solution: Ensure `pip install -r requirements.txt` ran successfully

**Issue: Permission errors**
- Solution: Check file permissions, ensure user has database access

**Issue: 502/504 Gateway errors**
- Solution: Check application logs, verify WSGI config, restart app server
