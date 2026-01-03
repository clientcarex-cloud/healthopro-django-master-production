#!/bin/bash
# setup_db.sh

echo "----------------------------------------------------------------"
echo "This script will overwrite the 'healthopro' database if it exists."
echo "You will be prompted for your 'postgres' user password."
echo "----------------------------------------------------------------"

# 1. Create User and Database (Requires postgres password)
echo "Creating user 'healthoproadmin' and database 'healthopro'..."
/Library/PostgreSQL/18/bin/psql -U postgres -c "CREATE USER healthoproadmin WITH PASSWORD '0CgNjqMFaPTPnfp';"
/Library/PostgreSQL/18/bin/psql -U postgres -c "ALTER USER healthoproadmin CREATEDB;"
/Library/PostgreSQL/18/bin/psql -U postgres -c "CREATE DATABASE healthopro OWNER healthoproadmin;"
/Library/PostgreSQL/18/bin/psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE healthopro TO healthoproadmin;"

# 2. Import Backup (Uses the newly created user healthoproadmin)
echo "----------------------------------------------------------------"
echo "Importing backup from healthopro_backup_20260102_0200AM.sql..."
export PGPASSWORD='0CgNjqMFaPTPnfp'
/Library/PostgreSQL/18/bin/psql -h localhost -U healthoproadmin -d healthopro < healthopro_backup_20260102_0200AM.sql

echo "----------------------------------------------------------------"
echo "Database setup complete!"
echo "You can now start the server with:"
echo "export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:\$DYLD_FALLBACK_LIBRARY_PATH && venv/bin/python manage.py runserver"
