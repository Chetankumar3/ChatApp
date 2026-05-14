# Old:
#!/bin/bash

# export HOST_IP=$(ip route get 1 | awk '{print $7;exit}')
# docker compose up -d

#!/bin/bash
set -e

export HOST_IP=$(ip route get 1 | awk '{print $7;exit}')

docker compose up -d