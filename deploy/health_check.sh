#!/bin/bash
# VeroRun service health check
# Usage: health_check.sh <port>
# Waits up to 90 seconds for the service on 127.0.0.1:<port>/health to return 200.
# Exits 0 on success, 1 on timeout.

PORT="${1:-8081}"
MAX_WAIT=90
INTERVAL=1

for i in $(seq 1 "${MAX_WAIT}"); do
    if curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; then
        exit 0
    fi
    sleep "${INTERVAL}"
done

exit 1