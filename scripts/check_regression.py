#!/usr/bin/env python3
"""
Script to check for regressions in the hass-eedomus integration.
This script verifies that the changes do not break existing functionality.
"""

import os
import sys
import json
import yaml

# Add the custom_components directory to the path
sys.path.insert(0, 'custom_components')

def check_manifest():
    """Check that the manifest.json is valid."""
    manifest_path = 'custom_components/eedomus/manifest.json'
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print("✅ Manifest.json is valid")
        return True
    except Exception as e:
        print(f"❌ Manifest.json is invalid: {e}")
        return False

def check_translations():
    """Check that the translation files are valid."""
    translations_dir = 'custom_components/eedomus/translations'
    if not os.path.exists(translations_dir):
        print("❌ Translations directory does not exist")
        return False
    
    for filename in os.listdir(translations_dir):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(translations_dir, filename), 'r') as f:
                    json.load(f)
                print(f"✅ Translation file {filename} is valid")
            except Exception as e:
                print(f"❌ Translation file {filename} is invalid: {e}")
                return False
    
    return True

def check_yaml_files():
    """Check that the YAML files are valid."""
    yaml_files = [
        'custom_components/eedomus/config/device_mapping.yaml',
        'custom_components/eedomus/config/custom_mapping.yaml'
    ]
    
    for yaml_file in yaml_files:
        if os.path.exists(yaml_file):
            try:
                with open(yaml_file, 'r') as f:
                    yaml.safe_load(f)
                print(f"✅ YAML file {yaml_file} is valid")
            except Exception as e:
                print(f"❌ YAML file {yaml_file} is invalid: {e}")
                return False
        else:
            print(f"⚠️  YAML file {yaml_file} does not exist")
    
    return True

def check_python_syntax():
    """Check that the Python files have valid syntax."""
    python_files = []
    for root, dirs, files in os.walk('custom_components/eedomus'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    for python_file in python_files:
        try:
            with open(python_file, 'r') as f:
                compile(f.read(), python_file, 'exec')
            print(f"✅ Python file {python_file} has valid syntax")
        except Exception as e:
            print(f"❌ Python file {python_file} has invalid syntax: {e}")
            return False
    
    return True

def main():
    """Run all regression checks."""
    print("Running regression checks for hass-eedomus...")
    
    checks = [
        ("Manifest", check_manifest),
        ("Translations", check_translations),
        ("YAML Files", check_yaml_files),
        ("Python Syntax", check_python_syntax)
    ]
    
    all_passed = True
    for name, check in checks:
        print(f"\nChecking {name}...")
        if not check():
            all_passed = False
    
    if all_passed:
        print("\n✅ All regression checks passed!")
    else:
        print("\n❌ Some regression checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()