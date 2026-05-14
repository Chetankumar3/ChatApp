#!/bin/bash
set -e

# Poll GCS until manager has written the token
echo "Waiting for swarm token..."
until gcloud storage cp gs://ping-configs/swarm-worker-token /tmp/swarm-token 2>/dev/null; do
  sleep 5
done

WORKER_TOKEN=$(cat /tmp/swarm-token)
if [ -z "$WORKER_TOKEN" ] || [ ${#WORKER_TOKEN} -lt 10 ]; then
  echo "ERROR: Invalid or empty swarm token" >&2
  exit 1
fi

MANAGER_IP=$(gcloud compute instances list \
  --filter="labels.role=swarm-manager AND zone:us-central1-c" \
  --format='get(networkInterfaces[0].networkIP)' \
  --limit=1)

if [ -z "$MANAGER_IP" ]; then
  echo "ERROR: Manager instance not found. Exiting." >&2
  exit 1
fi

docker swarm join --token "$WORKER_TOKEN" "$MANAGER_IP":2377

echo "Joined swarm successfully"