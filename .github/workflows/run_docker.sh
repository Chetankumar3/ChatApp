#!/bin/bash
# Grabs the IP of the eth0 interface in WSL
sudo apt update

export HOST_IP=$(ip route get 1 | awk '{print $7;exit}')

docker compose up