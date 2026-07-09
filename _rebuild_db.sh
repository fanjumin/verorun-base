#!/bin/bash
# Step 1: Restart all services
echo "Restarting all services..."
sudo supervisorctl restart all 2>&1 || supervisorctl restart all 2>&1
sleep 3

# Step 2: Wait for DB to be created and check
echo "=== Checking if DB was created ==="
ls -la /home/easykai/easykai-workspace/easykai.cn/data/verorun.db 2>&1

# Step 3: Verify all tables exist
echo "=== Table count ==="
sqlite3 /home/easykai/easykai-workspace/easykai.cn/data/verorun.db ".tables" 2>&1 | wc -w

# Step 4: Disable legacy agents
echo "=== Disabling legacy agents ==="
sqlite3 /home/easykai/easykai-workspace/easykai.cn/data/verorun.db "UPDATE agent_matrix SET is_active=0, updated_at=datetime('now','localtime') WHERE name IN ('Voice Agent','Video Agent','Image Agent','Ticket Agent');"
echo "Legacy agents disabled."

# Step 5: Check active agent count
echo "=== Active agents ==="
sqlite3 /home/easykai/easykai-workspace/easykai.cn/data/verorun.db "SELECT id,name,is_active FROM agent_matrix WHERE is_active=1 ORDER BY id;" 2>&1

# Step 6: Verify key new tables exist
echo "=== Key new tables ==="
for table in site_domains alert_silences fix_audit_log agent_silence_windows user_agent_upgrades; do
    count=$(sqlite3 /home/easykai/easykai-workspace/easykai.cn/data/verorun.db "SELECT COUNT(*) FROM sqlite_master WHERE name='$table';" 2>&1)
    if [ "$count" = "1" ]; then
        echo "  ✅ $table exists"
    else
        echo "  ❌ $table MISSING"
    fi
done

# Step 7: Check service status
echo "=== Service status ==="
sudo supervisorctl status 2>&1 || supervisorctl status 2>&1

echo ""
echo "=== DONE ==="
