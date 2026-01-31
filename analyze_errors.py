#!/usr/bin/env python3
"""Analyze potential errors in the code"""

import os
import re

errors = []

# Check for common issues
with open('custom_components/eedomus/const.py', 'r') as f:
    content = f.read()
    if 'DEFAULT_API_HOST = "xxx.XXX.xxx.XXX"' in content:
        errors.append('⚠️  WARNING: DEFAULT_API_HOST contains placeholder value')
        errors.append('   This should be replaced by private_const.py on the Raspberry Pi')

# Check for missing imports
with open('custom_components/eedomus/__init__.py', 'r') as f:
    content = f.read()
    if 'from homeassistant' in content:
        errors.append('ℹ️  INFO: Code requires Home Assistant environment')
        errors.append('   This is normal - code is designed to run in Home Assistant')

# Check for TODO/FIXME
for root, dirs, files in os.walk('custom_components/eedomus'):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                todos = re.findall(r'(TODO|FIXME|XXX|HACK).*?(?=\n|$)', content, re.IGNORECASE | re.DOTALL)
                for todo in todos:
                    errors.append(f'⚠️  TODO in {file}: {todo[:50]}...')

print('Code Analysis Results:')
print('=' * 60)
if errors:
    for error in errors:
        print(error)
else:
    print('✅ No critical errors found')
print('=' * 60)
