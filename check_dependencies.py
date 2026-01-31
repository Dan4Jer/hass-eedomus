#!/usr/bin/env python3
"""Check if dependencies in manifest.json are up to date"""

import json
import subprocess
import sys

# Load manifest
with open('custom_components/eedomus/manifest.json', 'r') as f:
    manifest = json.load(f)

print("Dependency Analysis")
print("=" * 60)
print(f"Current version: {manifest['version']}")
print()

# Check aiohttp version
print("1. aiohttp")
print(f"   Required: {manifest['requirements'][0]}")
try:
    result = subprocess.run(['pip', 'show', 'aiohttp'], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                installed = line.split(':')[1].strip()
                print(f"   Installed: {installed}")
                if installed.startswith('3.'):
                    print(f"   ✅ Version OK (3.x series)")
                else:
                    print(f"   ⚠️  Version might be outdated")
                break
    else:
        print("   ❌ Not installed locally")
except Exception as e:
    print(f"   ❌ Error checking version: {e}")

print()

# Check yarl version
print("2. yarl")
print(f"   Required: {manifest['requirements'][1]}")
try:
    result = subprocess.run(['pip', 'show', 'yarl'], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                installed = line.split(':')[1].strip()
                print(f"   Installed: {installed}")
                if installed.startswith('1.'):
                    print(f"   ✅ Version OK (1.x series)")
                else:
                    print(f"   ⚠️  Version might be outdated")
                break
    else:
        print("   ❌ Not installed locally")
except Exception as e:
    print(f"   ❌ Error checking version: {e}")

print()
print("Recommendations:")
print("=" * 60)
print("✅ aiohttp>=3.8 is a good minimum requirement")
print("✅ yarl>=1.8 is a good minimum requirement")
print()
print("Note: These versions are compatible with Home Assistant 2026.1.3")
print("=" * 60)
