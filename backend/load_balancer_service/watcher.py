import os
import asyncio
import subprocess
import redis.asyncio as redis

# Global variables with Docker fallbacks
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
NGINX_CONF_PATH = os.getenv("NGINX_CONF_PATH", "/etc/nginx/conf.d/default.conf")
POLL_INTERVAL = 10  # seconds

# Template with double braces {{ }} to escape them for Python's .format()
NGINX_TEMPLATE = """http {{
    upstream main-service {{
        least_conn;
{main_servers}
    }}

    upstream cm-service {{
        least_conn;
{cm_servers}
    }}

    server {{
        listen 80;
        location / {{
            return 301 /ping/;
        }}

        location /ping/ {{
            alias /usr/share/nginx/html/;
            index index.html;
            try_files $uri $uri/ /ping/index.html;
        }}

        location /main_service/ {{
            proxy_pass http://main-service;
        }}

        location /cm_service/ {{
            proxy_pass http://cm-service;
            
            # Websocket specific directives
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;

            # Logging and debugging headers
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}
}}"""

async def get_servers(r: redis.Redis, service_type: str) -> list[str]:
    servers = []
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor, match=f"service:{service_type}:*")
        if keys:
            addresses = await r.mget(keys)
            # Filter out None values in case keys expired between scan and mget
            servers.extend([addr.decode('utf-8') for addr in addresses if addr])
        if cursor == 0:
            break
    return servers

def reload_nginx():
    """Test syntax and trigger NGINX reload."""
    try:
        # Step 1: Validate syntax before applying
        subprocess.run(["nginx", "-t", "-c", NGINX_CONF_PATH], check=True, capture_output=True)
        # Step 2: Issue reload signal
        subprocess.run(["nginx", "-s", "reload", "-c", NGINX_CONF_PATH], check=True, capture_output=True)
        print("NGINX reloaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"NGINX reload failed.\nStdout: {e.stdout.decode()}\nStderr: {e.stderr.decode()}")

async def service_watcher():
    r = await redis.from_url(REDIS_URL)
    last_main_servers = set()
    last_cm_servers = set()

    while True:
        try:
            main_servers = await get_servers(r, "main_http") # Match your register_service input
            cm_servers = await get_servers(r, "cm_http")

            current_main = set(main_servers)
            current_cm = set(cm_servers)

            # Only rewrite and reload if the infrastructure state changed
            if current_main != last_main_servers or current_cm != last_cm_servers:
                
                # Format server strings. Use a dummy down server if empty to prevent syntax errors.
                main_lines = "\n".join([f"        server {addr} max_fails=8 fail_timeout=10s;" for addr in main_servers]) or "        server 127.0.0.1:65535 down;"
                cm_lines = "\n".join([f"        server {addr} max_fails=8 fail_timeout=10s;" for addr in cm_servers]) or "        server 127.0.0.1:65535 down;"

                new_conf = NGINX_TEMPLATE.format(
                    main_servers=main_lines,
                    cm_servers=cm_lines
                )

                # Overwrite config
                with open(NGINX_CONF_PATH, "w") as f:
                    f.write(new_conf)

                reload_nginx()

                last_main_servers = current_main
                last_cm_servers = current_cm

        except Exception as e:
            print(f"Watcher loop error: {e}")
        
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(service_watcher())