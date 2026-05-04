#!/bin/bash
# Grabs the IP of the eth0 interface in WSL
$env:HOST_IP = (Get-NetRoute -DestinationPrefix 0.0.0.0/0 | Select-Object -First 1).NextHop

docker compose up