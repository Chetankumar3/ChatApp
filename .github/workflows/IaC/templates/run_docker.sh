# Old:
#!/bin/bash

# export HOST_IP=$(ip route get 1 | awk '{print $7;exit}')
# docker compose up -d

#!/bin/bash
set -e

export HOST_IP=$(ip route get 1 | awk '{print $7;exit}')

# 1. Init Swarm (idempotent — fails silently if already a swarm node)
docker swarm init --advertise-addr "$HOST_IP" 2>/dev/null \
  && echo "Swarm initialized" \
  || echo "Already a swarm member, continuing..."

# After docker swarm init succeeds, save the worker token to GCS
WORKER_TOKEN=$(docker swarm join-token worker -q)
echo "$WORKER_TOKEN" | gcloud storage cp - gs://ping-configs/swarm-worker-token

# 2. Create overlay network (idempotent)
docker network create \
  --driver overlay \
  --attachable \
  ping-overlay 2>/dev/null || echo "Network ping-overlay already exists"

# 3. Deploy (or update) the stack
# --with-registry-auth passes GCR credentials to worker nodes (essential for multi-node later)
docker stack deploy \
  --with-registry-auth \
  --compose-file docker-stack.yaml \
  ping

echo "Stack deployed. Check with: docker stack ps ping"