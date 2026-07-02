$puttyDir = 'C:\PROGRA~1\PuTTY'
$script = 'f:\Sites\VeroRun\diagnose_admin.py'
$userHost = 'easykai@***REMOVED***'

Write-Output "=== Step 1: Copy script to server ==="
& "$puttyDir\pscp.exe" -pw ***REMOVED*** -batch $script "${userHost}:/tmp/diag_run.py"
Write-Output "pscp exit: $LASTEXITCODE"

Write-Output "=== Step 2: Run script on server ==="
& "$puttyDir\plink.exe" -ssh -pw ***REMOVED*** -batch easykai@***REMOVED*** 'python3 /tmp/diag_run.py > /tmp/diag_out.txt 2>&1'
Write-Output "plink exit: $LASTEXITCODE"

Write-Output "=== Step 3: Retrieve result file ==="
& "$puttyDir\pscp.exe" -pw ***REMOVED*** -batch "${userHost}:/tmp/diag_out.txt" 'f:\Sites\VeroRun\diag_result.txt'
Write-Output "pscp exit: $LASTEXITCODE"

Write-Output "=== Done ==="
