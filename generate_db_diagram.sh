#!/bin/bash
# Set environment variables for WeasyPrint/cairo/pango
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"

source venv/bin/activate
echo "Generating Database Diagram for Core Apps..."

# Generating diagram for key apps only to avoid graphviz complexity limits
python manage.py graph_models healtho_pro_user accounts pro_laboratory pro_pharmacy pro_hospital -g -o db_schema_core.png

echo "Done. Created db_schema_core.png"
