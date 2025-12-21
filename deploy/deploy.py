"""
Deployment Package Builder
===========================
Creates a clean deployment package containing only production-ready files.

Usage:
    python deploy/deploy.py [--with-data] [--output filename.zip] [--send]

Options:
    --with-data     Include database export in deployment package
    --output FILE   Specify output filename (default: deploy_YYYYMMDD_HHMMSS.zip)
    --send          Upload package to FTP server after creation (requires FTP config in .env)

Examples:
    python deploy/deploy.py
    python deploy/deploy.py --with-data
    python deploy/deploy.py --output production_v2.zip --with-data
    python deploy/deploy.py --with-data --send
"""

import os
import sys
import zipfile
import subprocess
from datetime import datetime
from pathlib import Path
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Files and directories to INCLUDE in deployment
INCLUDE_PATTERNS = [
    'app/**/*.py',
    'app/**/*.json',
    'migrations/**/*.py',
    'migrations/**/*.ini',
    'migrations/**/*.mako',
    '*.py',  # Root level Python files
    'requirements.txt',
    'README.md',
    'DEPLOYMENT_GUIDE.md',
    '.env.example',
    'pytest.ini',
]

# Files and directories to EXCLUDE (override includes)
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.pytest_cache',
    'htmlcov',
    '.coverage',
    'tests/',
    '.git',
    '.gitignore',
    '.claude',
    '*.db',
    '*.sql',
    '*.zip',
    'instance/',
    'log/',
    'old/',
    '.env',  # IMPORTANT: Never deploy actual .env file
    'app/static/avatars/*',  # Exclude user-uploaded avatars
]

# Root-level files to explicitly include
ROOT_FILES = [
    'run.py',
    'wsgi.py',
    'requirements.txt',
    'README.md',
    '.env.example',
    'pytest.ini',
]

# Deploy folder files to include
DEPLOY_FILES = [
    'deploy/export_db.py',
    'deploy/export_db_python.py',
    'deploy/import_db_from_sql.py',
    'deploy/DEPLOYMENT_GUIDE.md',
    'deploy/DEPLOY_QUICK_REF.md',
    'deploy/README_DEPLOYMENT.md',
]


def should_include(path):
    """Check if a file should be included in deployment."""
    path_str = str(path)

    # Check exclusions first
    for pattern in EXCLUDE_PATTERNS:
        if pattern.endswith('/'):
            # Directory pattern
            if pattern.rstrip('/') in path.parts:
                return False
        elif '*' in pattern:
            # Wildcard pattern
            from fnmatch import fnmatch
            if fnmatch(path_str, pattern) or fnmatch(path.name, pattern):
                return False
        else:
            # Exact match
            if pattern in path.parts or path.name == pattern:
                return False

    return True


def get_files_to_deploy():
    """Get list of files to include in deployment package."""
    files = []
    # Work from parent directory (backend/)
    base_path = Path('..' if Path('deploy').exists() and Path.cwd().name == 'deploy' else '.')

    # Add root-level files
    for filename in ROOT_FILES:
        file_path = base_path / filename
        if file_path.exists() and should_include(file_path):
            files.append(file_path)

    # Add deploy folder files
    for filename in DEPLOY_FILES:
        file_path = base_path / filename
        if file_path.exists() and should_include(file_path):
            files.append(file_path)

    # Add app directory (recursively)
    app_path = base_path / 'app'
    if app_path.exists():
        for item in app_path.rglob('*'):
            if item.is_file() and should_include(item):
                files.append(item)

    # Add migrations directory (recursively)
    migrations_path = base_path / 'migrations'
    if migrations_path.exists():
        for item in migrations_path.rglob('*'):
            if item.is_file() and should_include(item):
                files.append(item)

    return sorted(set(files))


def export_database():
    """Export database and return filename."""
    print("\n📦 Exporting database...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_file = f"deploy_db_{timestamp}.sql"

    try:
        # Import and run export function from deploy folder
        deploy_dir = Path(__file__).parent
        sys.path.insert(0, str(deploy_dir))
        from export_db import export_database as do_export
        do_export(db_file)
        return db_file
    except Exception as e:
        print(f"⚠️  Warning: Database export failed: {e}")
        print("   Continuing without database export...")
        return None


def upload_to_ftp(local_file):
    """Upload deployment package to FTP server."""
    # Get FTP configuration from environment
    ftp_host = os.getenv('FTP_HOST')
    ftp_port = int(os.getenv('FTP_PORT', 21))
    ftp_user = os.getenv('FTP_USER')
    ftp_password = os.getenv('FTP_PASSWORD')
    ftp_remote_path = os.getenv('FTP_REMOTE_PATH', '/')

    if not all([ftp_host, ftp_user, ftp_password]):
        print("\n❌ FTP configuration missing in .env file")
        print("   Required: FTP_HOST, FTP_USER, FTP_PASSWORD")
        print("   Optional: FTP_PORT (default: 21), FTP_REMOTE_PATH (default: /)")
        return False

    print("\n" + "=" * 60)
    print("📤 UPLOADING TO FTP SERVER")
    print("=" * 60)
    print(f"   Host: {ftp_host}:{ftp_port}")
    print(f"   User: {ftp_user}")
    print(f"   Remote path: {ftp_remote_path}")
    print(f"   File: {os.path.basename(local_file)}")

    try:
        # Connect to FTP server
        print("\n🔌 Connecting to FTP server...")
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_user, ftp_password)
        print("   ✓ Connected successfully")

        # Change to remote directory (create if needed)
        try:
            ftp.cwd(ftp_remote_path)
        except:
            print(f"   📁 Creating remote directory: {ftp_remote_path}")
            # Try to create directory path
            parts = ftp_remote_path.strip('/').split('/')
            current = ''
            for part in parts:
                current += '/' + part
                try:
                    ftp.cwd(current)
                except:
                    ftp.mkd(current)
                    ftp.cwd(current)

        # Upload file
        remote_filename = os.path.basename(local_file)
        file_size = os.path.getsize(local_file) / 1024 / 1024  # MB
        print(f"\n📤 Uploading {remote_filename} ({file_size:.2f} MB)...")

        with open(local_file, 'rb') as f:
            ftp.storbinary(f'STOR {remote_filename}', f)

        print("   ✓ Upload completed successfully")

        # Verify upload
        remote_files = ftp.nlst()
        if remote_filename in remote_files:
            print(f"   ✓ File verified on server: {remote_filename}")

        ftp.quit()

        print("\n" + "=" * 60)
        print("✅ FTP UPLOAD SUCCESSFUL")
        print("=" * 60)
        print(f"   Remote location: {ftp_remote_path}/{remote_filename}")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ FTP upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_deployment_package(output_file=None, include_data=False, send_ftp=False):
    """Create deployment ZIP package."""
    # Create dist directory if it doesn't exist
    dist_dir = Path('dist')
    dist_dir.mkdir(exist_ok=True)

    # Generate output filename
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"deploy_{timestamp}.zip"

    # Ensure .zip extension
    if not output_file.endswith('.zip'):
        output_file += '.zip'

    # Put output file in dist directory
    output_file = str(dist_dir / output_file)

    print("=" * 60)
    print("🚀 DEPLOYMENT PACKAGE BUILDER")
    print("=" * 60)

    # Get files to deploy
    files = get_files_to_deploy()

    # Export database if requested
    db_file = None
    if include_data:
        db_file = export_database()
        if db_file and os.path.exists(db_file):
            files.append(Path(db_file))

    # Create ZIP file
    print(f"\n📦 Creating deployment package: {output_file}")
    print(f"   Files to include: {len(files)}")

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            # Add file to ZIP with relative path
            arcname = str(file_path)
            zipf.write(file_path, arcname)
            print(f"   ✓ {arcname}")

    # Clean up temporary database export
    if db_file and os.path.exists(db_file):
        os.remove(db_file)
        print(f"\n   🗑️  Cleaned up temporary file: {db_file}")

    # Show summary
    file_size = os.path.getsize(output_file) / 1024 / 1024  # MB
    print("\n" + "=" * 60)
    print(f"✅ Deployment package created successfully!")
    print(f"   File: {output_file}")
    print(f"   Size: {file_size:.2f} MB")
    print(f"   Files: {len(files)}")
    print("=" * 60)

    # Upload to FTP if requested
    upload_success = False
    if send_ftp:
        upload_success = upload_to_ftp(output_file)
        if not upload_success:
            print("\n⚠️  Package created but FTP upload failed")
            print("   You can manually upload the file or try again")

    # Show deployment instructions
    if not send_ftp or not upload_success:
        print("\n📋 DEPLOYMENT INSTRUCTIONS:")
        print("=" * 60)
        print(f"1. Upload '{output_file}' to your server")
        print("2. Extract the package:")
        print(f"   unzip {os.path.basename(output_file)}")
    else:
        print("\n📋 NEXT STEPS ON SERVER:")
        print("=" * 60)
        print("1. Connect to your server")
        print("2. Extract the package:")
        print(f"   unzip {os.path.basename(output_file)}")

    print("3. Configure environment:")
    print("   cp .env.example .env")
    print("   # Edit .env with production values")

    if include_data:
        print("4. Import database:")
        print(f"   python deploy/import_db_from_sql.py deploy_db_*.sql")
    else:
        print("4. Run migrations:")
        print("   flask db upgrade")
        print("   # Create superuser if needed (see README)")

    print("5. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("6. Start application:")
    print("   # See README for WSGI setup")
    print("=" * 60)

    return output_file


def main():
    """Parse arguments and create deployment package."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Create deployment package for Finding-Memo backend',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy/deploy.py                              # Basic deployment (code only)
  python deploy/deploy.py --with-data                  # Include database export
  python deploy/deploy.py --output prod_v2.zip         # Custom filename
  python deploy/deploy.py --with-data -o prod_v2.zip   # Both options
  python deploy/deploy.py --with-data --send           # Create and upload to FTP
        """
    )

    parser.add_argument(
        '--with-data',
        action='store_true',
        help='Include database export in package'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output filename (default: deploy_YYYYMMDD_HHMMSS.zip)'
    )

    parser.add_argument(
        '--send',
        action='store_true',
        help='Upload package to FTP server after creation (requires FTP config in .env)'
    )

    args = parser.parse_args()

    try:
        create_deployment_package(
            output_file=args.output,
            include_data=args.with_data,
            send_ftp=args.send
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error creating deployment package: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
