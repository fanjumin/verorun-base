"""Fix site_builder/site_settings/models.py: ? -> %s and datetime('now') -> NOW()."""
fp = r'F:\Sites\VeroRun\site_builder\site_settings\models.py'
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

print(f'Before: {c.count("?")} question marks, {"datetime" in c and "now" in c} datetime')

# Fix all SQL ? -> %s in execute() calls
# These are all in SQL strings like '...WHERE site_key=?' or 'VALUES (?,?,?,?)'
import re

# Replace ? with %s ALL occurrences (they're all SQL placeholders in this file)
c = c.replace('?', '%s')

# Fix datetime('now') -> NOW()
c = c.replace("datetime('now')", "NOW()")

dt_check = "datetime('now')" in c
print(f'After: {c.count("?")} question marks, datetime={dt_check}')

with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
