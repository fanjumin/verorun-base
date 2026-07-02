$ErrorActionPreference = 'Stop'
$puttyDir = 'C:\PROGRA~1\PuTTY'
$script = 'f:\Sites\VeroRun\diagnose_admin.py'
$hostDest = 'easykai@***REMOVED***:/tmp/diag.py'

# Step 1: Copy script to server
Write-Output "=== Copying script to server ==="
& "$puttyDir\pscp.exe" -pw ***REMOVED*** $script $hostDest
$exit1 = $LASTEXITCODE
Write-Output "pscp exit: $exit1"

# Step 2: Run the script
Write-Output "=== Running script ==="
$output = & "$puttyDir\plink.exe" -ssh -pw ***REMOVED*** easykai@***REMOVED*** "python3 /tmp/diag.py 2>&1"
$exit2 = $LASTEXITCODE
$output | Out-File -FilePath 'f:\Sites\VeroRun\diag_result.txt' -Encoding utf8
Write-Output "plink exit: $exit2"
Write-Output "=== Done ==="
