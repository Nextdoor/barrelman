#!/bin/sh -e

/usr/sbin/nginx -c /app/nginx.conf -p /app/ &
exec python -u /app/src/app.py
