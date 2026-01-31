#!/usr/bin/env python3
"""
Script to copy static files for Eedomus Lovelace card.

This script copies the JavaScript files from the lovelace directory
to the www directory so they can be served by Home Assistant.
"""

import os
import shutil
import sys

def copy_static_files():
    """Copy static files to www directory."""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        component_dir = os.path.join(script_dir, '..', 'custom_components', 'eedomus')
        www_dir = os.path.join(component_dir, 'www')
        lovelace_dir = os.path.join(component_dir, 'lovelace')
        
        print(f"Copying static files from {lovelace_dir} to {www_dir}")
        
        # Create www directory if it doesn't exist
        os.makedirs(www_dir, exist_ok=True)
        
        # Copy Lovelace JS file
        src_js = os.path.join(lovelace_dir, 'config_panel.js')
        dst_js = os.path.join(www_dir, 'config_panel.js')
        
        if os.path.exists(src_js):
            shutil.copy2(src_js, dst_js)
            print(f"✅ Copied: {src_js} -> {dst_js}")
        else:
            print(f"⚠️  Source file not found: {src_js}")
            
        # Copy any other static files if they exist
        static_files = ['config_panel.js']  # Add other files here if needed
        
        for filename in static_files:
            src_file = os.path.join(lovelace_dir, filename)
            dst_file = os.path.join(www_dir, filename)
            
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                print(f"✅ Copied: {src_file} -> {dst_file}")
            else:
                print(f"⚠️  File not found: {src_file}")
        
        print("🎉 Static files copied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error copying static files: {e}")
        return False

if __name__ == "__main__":
    success = copy_static_files()
    sys.exit(0 if success else 1)