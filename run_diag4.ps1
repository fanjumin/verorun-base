$b64 = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content 'f:\Sites\VeroRun\diagnose_admin.py' -Raw)))
# Step 1: Write script to server
$b64 | & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** "base64 -d > /tmp/diag4.py 2>/tmp/diag_err.txt"
$exit1 = $LASTEXITCODE
# Step 2: Run the script
$output = & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** "python3 /tmp/diag4.py 2>&1"
$output | Out-File -FilePath 'f:\Sites\VeroRun\diag_result.txt' -Encoding utf8
Write-Output "Write exit: $exit1, Run exit: $LASTEXITCODE"
