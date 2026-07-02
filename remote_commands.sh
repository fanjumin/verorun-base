echo "Starting diagnostic..."
PID=$(pgrep -f 'gunicorn.*8084' | head -1)
echo "PID: $PID"
strings /proc/$PID/environ | grep JWT_SECRET
