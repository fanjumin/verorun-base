#!/usr/bin/env python3
"""Extract real inline JS and check with node --check"""
import re, subprocess

with open('/tmp/admin_rendered_check.cjs', 'r') as f:
    content = f.read()

# The file already contains raw HTML. Find the first <script> without src=
idx = content.find('<script>')
# Actually, the saved file starts from js_start_idx in the original script
# Let me just look for </script> in first 50 chars
print('FIRST_50:', repr(content[:50]))
print('LAST_50:', repr(content[-50:]))
print('TOTAL_LEN:', len(content))
