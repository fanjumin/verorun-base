$ErrorActionPreference = 'Stop'
$outFile = 'f:\Sites\VeroRun\diag_result.txt'

# Step 1: Get JWT secret and generate token, then fetch admin page
$step1 = & 'C:\PROGRA~1\PuTTY\plink.exe' -ssh -pw ***REMOVED*** easykai@***REMOVED*** "python3 -c '
import subprocess, os
p = subprocess.run([\"pgrep\",\"-f\",\"gunicorn.*8084\"],capture_output=True,text=True).stdout.strip().split()[0]
e = subprocess.run([\"strings\",f\"/proc/{p}/environ\"],capture_output=True,text=True).stdout
j = [l.split(\"=\",1)[1] for l in e.split(chr(10)) if \"JWT_SECRET\" in l][0]
print(\"JWT:\"+j[:20])
'"
$step1 | Out-File $outFile -Encoding utf8
Write-Output "Step1 exit: $LASTEXITCODE"
