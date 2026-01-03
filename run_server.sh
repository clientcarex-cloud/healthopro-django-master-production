#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set environment variables for WeasyPrint
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"

# Add PostgreSQL to PATH
export PATH="/Library/PostgreSQL/18/bin:$PATH"

# Run Django server
python manage.py runserver
