FROM nginx:stable-alpine

# Install Python and the async Redis library
# (--break-system-packages is required in Alpine 3.15+ to install via pip as root)
RUN apk add --no-cache python3 py3-pip \
    && pip3 install --no-cache-dir redis asyncio --break-system-packages

WORKDIR /opt/watcher

# Copy your watcher python script and startup script
COPY watcher.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# The entrypoint will launch both NGINX and the Python script
ENTRYPOINT ["/opt/watcher/entrypoint.sh"]