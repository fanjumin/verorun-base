@echo off
C:\PROGRA~1\PuTTY\plink.exe -ssh -pw ***REMOVED*** easykai@***REMOVED*** "pgrep -f 'gunicorn.*8084' | head -1"
