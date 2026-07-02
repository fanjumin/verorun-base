$b64 = [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes('f:\Sites\VeroRun\diagnose_admin.py'))
$cmd = "echo $b64 | base64 -d > /tmp/diag.py && python3 /tmp/diag.py > /tmp/diag_out.txt 2>&1 && cat /tmp/diag_out.txt"
& 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** $cmd | Out-File -FilePath f:\Sites\VeroRun\diag_result.txt -Encoding utf8
Write-Output "Done. Exit code: $LASTEXITCODE"
