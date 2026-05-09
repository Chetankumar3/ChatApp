#!/bin/sh

# Start the Python watcher daemon in the background
python3 /opt/watcher/watcher.py &

# Start NGINX in the foreground (required to keep the Docker container alive)
exec nginx -g 'daemon off;'