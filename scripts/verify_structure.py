#!/usr/bin/env python3
"""Verify repository structure for HACS compliance."""
import os
import json


def check_file_exists(path: str, required: bool = True) -> bool:
    """Check if file exists."""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {path}")
    return exists


def check_manifest():
    """Check manifest.json structure."""
    print("\n📋 Checking manifest.json...")
    
    try:
        with open("custom_components/eedomus/manifest.json") as f:
            manifest = json.load(f)
        
        required_fields = [
            "domain", "name", "version", "documentation",
            "issue_tracker", "category", "requirements", "iot_class"
        ]
        
        missing = [f for f in required_fields if f not in manifest]
        
        if missing:
            print(f"❌ Missing fields: {', '.join(missing)}")
            return False
        
        print("✅ All required fields present")
        print(f"   Domain: {manifest['domain']}")
        print(f"   Name: {manifest['name']}")
        print(f"   Version: {manifest['version']}")
        print(f"   Category: {manifest['category']}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading manifest: {e}")
        return False


def check_structure():
    """Check repository structure."""
    print("📁 Checking repository structure...")
    
    required_files = [
        "custom_components/__init__.py",
        "custom_components/eedomus/__init__.py",
        "custom_components/eedomus/manifest.json",
        "README.md",
        "INFO.md",
    ]
    
    all_ok = True
    for file in required_files:
        if not check_file_exists(file):
            all_ok = False
    
    return all_ok


def check_tests():
    """Check test structure."""
    print("\n🧪 Checking tests...")
    
    test_files = [
        "scripts/tests/__init__.py",
        "scripts/tests/test_sensor.py",
        "scripts/tests/test_switch.py",
        "scripts/tests/test_light.py",
        "scripts/tests/test_cover.py",
        "scripts/tests/test_energy_sensor.py",
    ]
    
    all_ok = True
    for file in test_files:
        if not check_file_exists(file):
            all_ok = False
    
    return all_ok


def main():
    """Main verification function."""
    print("🔍 Verifying HACS compliance...")
    print("=" * 60)
    
    results = []
    
    # Check structure
    results.append(("Repository Structure", check_structure()))
    
    # Check manifest
    results.append(("Manifest JSON", check_manifest()))
    
    # Check tests
    results.append(("Test Structure", check_tests()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    if passed == total:
        print(f"\n🎉 All checks passed ({passed}/{total})")
        print("✅ Repository is HACS compliant!")
    else:
        print(f"\n⚠️  {total - passed} check(s) failed")
        print("Please review the issues above")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)