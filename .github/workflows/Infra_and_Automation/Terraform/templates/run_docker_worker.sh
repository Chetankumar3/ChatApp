#!/bin/bash
set -e

export HOST_IP=$(ip route get 1 | awk '{print $7;exit}')

# Poll GCS until manager has written the token
echo "Waiting for swarm token..."
until gcloud storage cp gs://ping-configs/swarm-worker-token /tmp/swarm-token 2>/dev/null; do
  sleep 5
done
echo "Got the swarm token"

WORKER_TOKEN=$(cat /tmp/swarm-token)
if [ -z "$WORKER_TOKEN" ] || [ ${#WORKER_TOKEN} -lt 10 ]; then
  echo "ERROR: Invalid or empty swarm token" >&2
  exit 1
fi

if [ -f /ping/.env ]; then
  set -a
  source /ping/.env
  set +a
else
  echo "ERROR: /ping/.env file not found!" >&2
  exit 1
fi

if [ -z "$MANAGER_IP" ]; then
  echo "ERROR: Manager instance not found. Exiting." >&2
  exit 1
fi

docker swarm join --token "$WORKER_TOKEN" "$MANAGER_IP":2377

echo "Joined swarm successfully"