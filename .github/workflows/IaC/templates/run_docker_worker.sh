#!/bin/bash
set -e

# Poll GCS until manager has written the token
echo "Waiting for swarm token..."
until gcloud storage cp gs://ping-configs/swarm-worker-token /tmp/swarm-token 2>/dev/null; do
  sleep 5
done

WORKER_TOKEN=$(cat /tmp/swarm-token)
MANAGER_IP=$(gcloud compute instances describe ping-gce-01 \
  --zone=us-central1-c \
  --format='get(networkInterfaces[0].networkIP)')

docker swarm join --token "$WORKER_TOKEN" "$MANAGER_IP":2377

echo "Joined swarm successfully"