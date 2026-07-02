$pyScript = Get-Content 'f:\Sites\VeroRun\diagnose_admin.py' -Raw
$bytes = [System.Text.Encoding]::UTF8.GetBytes($pyScript)
$b64 = [System.Convert]::ToBase64String($bytes)
$remoteCmd = "echo $b64 | base64 -d > /tmp/diag3.py 2>&1 && python3 /tmp/diag3.py 2>&1"
$output = & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** $remoteCmd
$output | Out-File -FilePath 'f:\Sites\VeroRun\diag_result.txt' -Encoding utf8
Write-Output "Exit: $LASTEXITCODE"
