$b64 = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content 'f:\Sites\VeroRun\diagnose_admin.py' -Raw)))
# Create a temp file with the base64 content
$b64File = 'f:\Sites\VeroRun\temp_b64.txt'
Set-Content -Path $b64File -Value $b64 -NoNewline -Encoding Ascii

# First write the script to server: cat the b64 file and pipe to plink
Get-Content $b64File | & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** "base64 -d > /tmp/diag5.py"

# Then run it
$output = & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** "python3 /tmp/diag5.py 2>&1"
$output | Out-File -FilePath 'f:\Sites\VeroRun\diag_result.txt' -Encoding utf8

Remove-Item $b64File -Force
Write-Output "Done"
