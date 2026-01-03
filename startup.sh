
apt-get update

apt-get install -y redis-server

service redis-server start

apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info libglib2.0-0 fonts-liberation fonts-dejavu-core fonts-freefont-ttf fonts-urw-base35

daphne -b 0.0.0.0 -p 8000 healtho_pro.asgi:application

#daphne -u /tmp/daphne.sock healtho_pro.asgi:application



