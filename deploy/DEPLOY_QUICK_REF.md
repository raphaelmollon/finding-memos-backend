# Deployment Quick Reference

## Single Command Deployment

```bash
python deploy/deploy.py
```
Creates: `deploy_YYYYMMDD_HHMMSS.zip` (code only)

```bash
python deploy/deploy.py --with-data
```
Creates: `deploy_YYYYMMDD_HHMMSS.zip` (code + database)

```bash
python deploy/deploy.py --output production_v2.zip --with-data
```
Creates: `production_v2.zip` (code + database, custom name)

---

## What Happens

### ✅ INCLUDED in ZIP
```
deploy_YYYYMMDD_HHMMSS.zip
├── app/                    # All your application code
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── ...
├── migrations/             # Database migrations (IMPORTANT!)
│   ├── versions/
│   └── env.py
├── run.py                  # Application entry point
├── wsgi.py                 # Production WSGI entry
├── requirements.txt        # Dependencies
├── export_db.py            # Database export tool
├── import_db_from_sql.py   # Database import tool
├── README.md               # Documentation
├── DEPLOYMENT_GUIDE.md     # This guide
├── .env.example            # Environment template
└── deploy_db_*.sql         # Database export (if --with-data used)
```

### ❌ EXCLUDED from ZIP
- `tests/` - Test files
- `__pycache__/`, `.pytest_cache/` - Cache files
- `log/`, `htmlcov/` - Log and coverage files
- `.env` - Your actual environment file (security!)
- `*.db`, `*.sql` - Local database files (unless --with-data)
- `.git/`, `.gitignore` - Git files
- `instance/` - Flask instance folder
- `old/`, `*.zip` - Old backups

---

## On Server After Upload

### Option 1: With Data (--with-data was used)
```bash
unzip deploy_YYYYMMDD_HHMMSS.zip
cp .env.example .env
# Edit .env with production values
python deploy/import_db_from_sql.py deploy_db_*.sql
pip install -r requirements.txt
# Configure WSGI and start
```

### Option 2: Migrations Only (no --with-data)
```bash
unzip deploy_YYYYMMDD_HHMMSS.zip
cp .env.example .env
# Edit .env with production values
flask db upgrade
flask shell  # Create superuser if needed
pip install -r requirements.txt
# Configure WSGI and start
```

---

## Common Use Cases

| Scenario | Command | On Server |
|----------|---------|-----------|
| **First deployment** | `python deploy/deploy.py --with-data` | Import database |
| **Code update only** | `python deploy/deploy.py` | Just extract |
| **Schema changed** | `python deploy/deploy.py` | Run `flask db upgrade` |
| **Fresh install** | `python deploy/deploy.py` | Run migrations, create superuser |
| **Production backup** | `python deploy/deploy.py --with-data -o backup.zip` | Keep safe |

---

## Pro Tips

1. **Always backup before deploying to production:**
   ```bash
   # On production server before deploying
   python deploy/export_db.py pre_deploy_backup.sql
   ```

2. **Test migrations locally first:**
   ```bash
   flask db migrate -m "description"
   flask db upgrade  # Test locally
   python deploy/deploy.py  # Then deploy
   ```

3. **Version your deployments:**
   ```bash
   python deploy/deploy.py --output prod_v1.2.3.zip
   ```

4. **Keep deployment ZIPs as rollback points**
   - Store them safely off-server
   - Name them clearly (dates or versions)

---

## Troubleshooting

**"No module named 'export_db'"**
- You're not in the backend directory
- Run `cd` to backend folder first

**"Database export failed"**
- Check `.env` has `SQLALCHEMY_DATABASE_URI`
- Ensure `mysqldump` is installed
- Script continues without database if export fails

**ZIP is too large**
- Check that `old/`, `log/`, `*.db` are excluded
- Large ZIP = you might have extra files

**Missing files in ZIP**
- Check the script output - it lists all included files
- Modify `EXCLUDE_PATTERNS` in `deploy.py` if needed
