#!/bin/sh
export SERVICE_ADVERTISE_HOST=$(hostname -i | awk '{print $1}')
exec "$@"