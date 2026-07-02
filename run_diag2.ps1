$scriptPath = 'f:\Sites\VeroRun\diagnose_admin.py'
Get-Content $scriptPath -Raw | & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** "python3 -c 'import sys; exec(sys.stdin.read())'" | Out-File -FilePath f:\Sites\VeroRun\diag_result.txt -Encoding utf8
Write-Output "Exit code: $LASTEXITCODE"
