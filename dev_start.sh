#!/bin/bash
echo "Starting development environment..."

# Start Django Server in a new tab
osascript -e 'tell application "Terminal" to do script "cd /Users/fahadahmed/Django/healthopro-django-master-production && ./run_server.sh"'

# Start Angular Server in a new tab
osascript -e 'tell application "Terminal" to do script "cd /Users/fahadahmed/Django/HealthO_Pro_Angular-main && npm start"'

echo "Servers starting in new tabs..."
