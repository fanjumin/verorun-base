#!/bin/bash
# Login and test
LOGIN=$(curl -s -X POST http://localhost:8084/admin/login -H 'Content-Type: application/json' -d '{"username":"***REMOVED***","password":"***REMOVED***","client_type":"browser"}' -o /tmp/lr.json -w '%{http_code}')
echo "Login: $LOGIN"
TOKEN=$(python3 -c "import json; print(json.load(open('/tmp/lr.json'))['data']['token'])")
echo "Token: ${TOKEN:0:20}..."

# Test AI Chat
echo ""
echo "=== AI Chat ==="
curl -s -H "Authorization: Bearer $TOKEN" -X POST http://localhost:8084/admin/agent-matrix/chat -H 'Content-Type: application/json' -d '{"message":"say hi"}' | python3 -m json.tool
