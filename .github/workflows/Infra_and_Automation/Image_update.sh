cd "/mnt/d/IIIT Naya Raipur/Dev/Ping/backend/cm_service"
docker build -t us-central1-docker.pkg.dev/project-cdd074dc-6291-4d7f-a2a/ping/ping-cm:2.1 .
docker push us-central1-docker.pkg.dev/project-cdd074dc-6291-4d7f-a2a/ping/ping-cm:2.1
echo "CM service pushed succesfully"

cd "/mnt/d/IIIT Naya Raipur/Dev/Ping/backend/main_service"
docker build -t us-central1-docker.pkg.dev/project-cdd074dc-6291-4d7f-a2a/ping/ping-main:2.1 .
docker push us-central1-docker.pkg.dev/project-cdd074dc-6291-4d7f-a2a/ping/ping-main:2.1
echo "Main service pushed succesfully"

cd "/mnt/d/IIIT Naya Raipur/Dev/Ping"
docker build -f backend/gateway/Dockerfile -t us-central1-docker.pkg.dev/project-cdd074dc-6291-4d7f-a2a/ping/ping-gateway:2.1 .
docker push us-central1-docker.pkg.dev/project-cdd074dc-6291-4d7f-a2a/ping/ping-gateway:2.1
echo "Gateway service pushed succesfully"

sudo systemctl stop docker.service docker.socket