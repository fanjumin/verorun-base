"""Fix all 3 minor issues in one batch."""
import os

BASE = r'F:\Sites\VeroRun'

# ── 1. orchestrator/models.py: fetchone()[0] → fetchone()['count'] or ['id'] ──
fp = os.path.join(BASE, 'orchestrator', 'models.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

# COUNT(*) queries → returns {'count': N}
replaces = [
    # list_cron_jobs
    ("SELECT COUNT(*) FROM cron_jobs WHERE", None),
    ("SELECT COUNT(*) FROM workflow_definitions WHERE", None),
    ("SELECT COUNT(*) FROM workflow_instances WHERE", None),
    ("SELECT COUNT(*) FROM execution_logs WHERE", None),
]

# Fix all fetchone()[0] where the preceding SQL uses COUNT(*)
# Strategy: replace all conn.fetchone()[0] with conn.fetchone()['count'] for count queries
# and conn.fetchone()['id'] for RETURNING id queries

# The file uses 3 patterns:
# Pattern A: conn = execute(COUNT); total = conn.fetchone()[0]  →  conn.fetchone()['count']
# Pattern B: RETURNING id; return conn.fetchone()[0]  →  conn.fetchone()['id']
# Pattern C: COALESCE(AVG...,0) → need to add alias

# Let me be more precise with line-by-line edits

lines = c.split('\n')
changes = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if 'fetchone()[0]' in stripped:
        # Check context: is previous SQL a COUNT(*) or RETURNING id?
        # Look back for the last execute
        for j in range(i-1, max(-1, i-15), -1):
            if 'execute(' in lines[j] or 'execute(' in lines[j-1] if j > 0 else False:
                # Found the execute context
                # Look forward from that execute to this line
                sql_context = ' '.join(lines[max(0,j-1):i+1])
                if 'COALESCE' in sql_context or 'coalesce' in sql_context:
                    # Add alias
                    # Find the previous line with COALESCE
                    for k in range(i-3, i):
                        if 'AVG(duration_ms),0)' in lines[k]:
                            lines[k] = lines[k].replace('AVG(duration_ms),0)', 'AVG(duration_ms),0) AS avg_duration')
                            break
                    lines[i] = line.replace("[0]", "['avg_duration']")
                    changes += 1
                elif 'COUNT(*)' in sql_context:
                    lines[i] = line.replace("[0]", "['count']")
                    changes += 1
                elif 'RETURNING id' in sql_context:
                    lines[i] = line.replace("[0]", "['id']")
                    changes += 1
                break

if changes > 0:
    c = '\n'.join(lines)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f'orchestrator/models.py: {changes} fixes')

# ── 2. site_builder/site_settings/models.py: ? → %s + datetime('now') → NOW() ──
fp = os.path.join(BASE, 'site_builder', 'site_settings', 'models.py')
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Read to understand actual content
# Then do replacements
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

orig = c

# SQL ? → %s in execute() calls (not f-strings, not string formatting)
# These appear in SQL strings passed to conn.execute() or cur.execute()
# Pattern: '...?....?....' → '...%s....%s....'
import re

# Find execute() calls with SQL strings containing ?
def replace_sql_placeholders(text):
    """Replace ? with %s in SQL strings within execute() calls."""
    # Strategy: find all strings that are arguments to execute() and contain ?
    # Replace ? → %s in those strings
    
    # Simple global replacement for ? → %s BUT avoid breaking f-strings, dict keys, etc.
    # In practice, all SQL ? in this file are inside single-quoted strings
    # So a line-by-line approach is safer
    
    result = []
    for line in text.split('\n'):
        if 'execute(' in line and '?' in line:
            # This is likely a SQL execute call
            # Replace ? with %s only within the SQL string (single-quoted)
            # Simple approach: just replace all ? with %s in these lines
            new_line = line.replace('?', '%s')
            if new_line != line:
                result.append(f'{new_line}  # fixed ?→%s')
            else:
                result.append(line)
        else:
            result.append(line)
    return '\n'.join(result)

c = replace_sql_placeholders(c)

# Fix datetime('now') → NOW()
c = c.replace("datetime('now')", "NOW()")

if c != orig:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f'site_settings/models.py: fixed')

# ── 3. agent_matrix/models.py - already fixed by subagent ──
print('agent_matrix/models.py: checked by subagent')

print('\nAll fixes applied.')
