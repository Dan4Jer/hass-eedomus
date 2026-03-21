#!/usr/bin/env python3
"""
Simple script to check if frontend files are in place.
"""

import sys
import os

def check_frontend_files():
    """Check if frontend files exist."""
    print("🔍 Checking Eedomus Frontend Files")
    print("=" * 35)
    
    base_path = '/homeassistant/custom_components/hass-eedomus/www'
    
    files_to_check = [
        'eedomus-rich-editor.js',
        'manifest.json',
        'eedomus-frontend-config.json'
    ]
    
    all_ok = True
    
    for filename in files_to_check:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✅ {filename} - {size} bytes")
        else:
            print(f"❌ {filename} - NOT FOUND")
            all_ok = False
    
    if all_ok:
        print(f"\n🎉 All {len(files_to_check)} frontend files are in place!")
        print(f"📁 Location: {base_path}")
    else:
        print(f"\n⚠️  Some frontend files are missing!")
        print(f"📁 Expected location: {base_path}")
    
    return all_ok

if __name__ == "__main__":
    success = check_frontend_files()
    sys.exit(0 if success else 1)