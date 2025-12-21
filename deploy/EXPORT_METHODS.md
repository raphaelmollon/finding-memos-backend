# Database Export Methods

This folder includes two database export methods to ensure maximum compatibility.

## Method 1: mysqldump (Preferred)

**File:** [export_db.py](export_db.py)

Uses the native `mysqldump` command-line tool for fast, reliable exports.

**Advantages:**
- ✅ Fast and efficient
- ✅ Industry standard
- ✅ Handles large databases well
- ✅ Includes triggers, procedures, events

**Requirements:**
- MySQL/MariaDB client tools installed

## Method 2: Pure Python (Fallback)

**File:** [export_db_python.py](export_db_python.py)

Pure Python implementation that connects directly to the database.

**Advantages:**
- ✅ No external tools required
- ✅ Works on any system with Python
- ✅ Automatically used as fallback

**Limitations:**
- ⚠️ May be slower for very large databases
- ⚠️ Doesn't export triggers/procedures/events

## How It Works

When you run `python deploy/export_db.py`:

1. **First try:** Use `mysqldump` (fast, full-featured)
2. **If mysqldump not found:** Automatically fallback to Python method
3. **Result:** You get a SQL export either way!

```bash
# This command works on any system
python deploy/export_db.py

# Output if mysqldump not found:
# ⚠️  mysqldump not found. Trying Python-based export instead...
# Exporting database to 'db_backup_20231219_120000.sql'...
# ✓ Database exported successfully
```

## Manual Method Selection

If you want to explicitly use the Python method:

```bash
# Use Python method directly
python deploy/export_db_python.py my_backup.sql
```

## Installation Options

### Windows

**Option 1: Install MySQL Client**
1. Download MySQL installer from mysql.com
2. Choose "MySQL Client" during installation
3. Add to PATH

**Option 2: Use Python method**
- No installation needed! It already works.

### Linux

```bash
# Ubuntu/Debian
sudo apt install mysql-client

# Or just use Python method (already works)
```

### macOS

```bash
# Install with Homebrew
brew install mysql-client

# Or just use Python method (already works)
```

## Which Method Am I Using?

Check the output when exporting:

**If using mysqldump:**
```
Exporting database 'finding_memo' to 'backup.sql'...
✓ Database exported successfully to 'backup.sql'
```

**If using Python fallback:**
```
Exporting database 'finding_memo' to 'backup.sql'...
⚠️  mysqldump not found. Trying Python-based export instead...
Exporting database to 'backup.sql'...
Found 5 tables to export
  Exporting table: categories
  Exporting table: memos
  ...
✓ Database exported successfully to 'backup.sql'
```

## Recommendations

- **Small to medium databases (< 100MB):** Python method works great
- **Large databases (> 100MB):** Install mysqldump for better performance
- **CI/CD pipelines:** Python method (no dependencies)
- **Production backups:** mysqldump (more features)

## Both Methods Work!

The automatic fallback means **you don't need to worry about it** - the export will work regardless of your system configuration.

Just run:
```bash
python deploy/export_db.py
```

And you'll get a working SQL export! 🎉
