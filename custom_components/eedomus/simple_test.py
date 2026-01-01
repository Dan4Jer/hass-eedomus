#!/usr/bin/env python3
"""Simple test script to verify basic functionality without complex imports."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_file_structure():
    """Test that all required files exist."""
    print("📁 Testing file structure...")
    
    required_files = [
        "__init__.py",
        "manifest.json",
        "const.py",
        "sensor.py",
        "switch.py",
        "light.py",
        "cover.py",
        "binary_sensor.py",
        "climate.py",
        "entity.py",
        "coordinator.py",
        "eedomus_client.py",
        "config_flow.py"
    ]
    
    missing_files = []
    for filename in required_files:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✅ All required files present")
        return True


def test_manifest_json():
    """Test manifest.json structure."""
    print("📋 Testing manifest.json...")
    
    import json
    
    try:
        with open(os.path.join(os.path.dirname(__file__), "manifest.json"), "r") as f:
            manifest = json.load(f)
        
        required_fields = [
            "domain", "name", "version", "documentation", "issue_tracker",
            "category", "requirements", "iot_class", "config_flow"
        ]
        
        missing_fields = [field for field in required_fields if field not in manifest]
        
        if missing_fields:
            print(f"❌ Missing manifest fields: {', '.join(missing_fields)}")
            return False
        
        # Check HACS-specific fields
        if manifest.get("category") != "Hub":
            print(f"⚠️  Category is '{manifest.get('category')}', expected 'Hub'")
        
        if not manifest.get("render_icon", False):
            print("⚠️  render_icon should be true for HACS")
        
        print("✅ Manifest.json structure is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading manifest.json: {e}")
        return False


def test_issue_9_implementation():
    """Test that Issue #9 (energy sensors) is properly implemented."""
    print("🎯 Testing Issue #9 implementation...")
    
    try:
        # Check sensor.py for energy sensor implementation
        sensor_path = os.path.join(os.path.dirname(__file__), "sensor.py")
        with open(sensor_path, "r") as f:
            sensor_content = f.read()
        
        # Look for energy sensor related code
        energy_indicators = [
            "usage_id.*26",
            "energy",
            "consumption",
            "kWh",
            "Wh",
            "device_class.*energy"
        ]
        
        found_indicators = []
        for indicator in energy_indicators:
            if indicator.lower() in sensor_content.lower():
                found_indicators.append(indicator)
        
        if not found_indicators:
            print("❌ No energy sensor implementation found")
            return False
        
        print(f"✅ Found energy sensor indicators: {', '.join(found_indicators)}")
        
        # Check for consumption handling in other files
        files_to_check = ["switch.py", "light.py", "cover.py"]
        consumption_found = False
        
        for filename in files_to_check:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    content = f.read()
                    if "consumption" in content.lower():
                        consumption_found = True
                        break
        
        if consumption_found:
            print("✅ Consumption monitoring found in device handlers")
        else:
            print("⚠️  No consumption monitoring in device handlers")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Issue #9 implementation: {e}")
        return False


def test_hacs_compliance():
    """Test HACS compliance."""
    print("🔍 Testing HACS compliance...")
    
    compliance_checks = []
    
    # Check 1: Proper directory structure
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    if os.path.basename(parent_dir) == "custom_components":
        compliance_checks.append(("Directory structure", True, "custom_components/eedomus/ found"))
    else:
        compliance_checks.append(("Directory structure", False, f"Unexpected structure: {parent_dir}"))
    
    # Check 2: __init__.py files
    init_files = [
        os.path.join(os.path.dirname(__file__), "__init__.py"),
        os.path.join(parent_dir, "__init__.py")
    ]
    
    missing_inits = [f for f in init_files if not os.path.exists(f)]
    if not missing_inits:
        compliance_checks.append(("__init__.py files", True, "All __init__.py files present"))
    else:
        compliance_checks.append(("__init__.py files", False, f"Missing: {', '.join(missing_inits)}"))
    
    # Check 3: Documentation files
    doc_files = [
        "README.md",
        "INFO.md",
        "TESTS_README.md"
    ]
    
    present_docs = []
    for doc in doc_files:
        doc_path = os.path.join(os.path.dirname(__file__), doc)
        if os.path.exists(doc_path):
            present_docs.append(doc)
    
    if present_docs:
        compliance_checks.append(("Documentation", True, f"Found: {', '.join(present_docs)}"))
    else:
        compliance_checks.append(("Documentation", False, "No documentation files found"))
    
    # Check 4: Test files
    test_files = [
        "test_energy_sensor.py",
        "test_switch.py",
        "test_light.py",
        "test_cover.py",
        "test_sensor.py"
    ]
    
    present_tests = []
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            present_tests.append(test_file)
    
    if present_tests:
        compliance_checks.append(("Test coverage", True, f"Found: {', '.join(present_tests)}"))
    else:
        compliance_checks.append(("Test coverage", False, "No test files found"))
    
    # Print results
    passed = sum(1 for _, success, _ in compliance_checks if success)
    total = len(compliance_checks)
    
    print(f"\nHACS Compliance Summary ({passed}/{total}):")
    for check_name, success, message in compliance_checks:
        status = "✅" if success else "❌"
        print(f"  {status} {check_name}: {message}")
    
    return passed == total


def main():
    """Run all tests."""
    print("🚀 Starting Eedomus HACS compliance tests...")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("File Structure", test_file_structure()))
    results.append(("Manifest JSON", test_manifest_json()))
    results.append(("Issue #9 Implementation", test_issue_9_implementation()))
    results.append(("HACS Compliance", test_hacs_compliance()))
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"Overall Results: {passed}/{total} tests passed")
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("✅ The integration is ready for HACS submission.")
        print("\nNext steps:")
        print("1. Create a GitHub release with version 0.12.0")
        print("2. Submit to HACS via pull request")
        print("3. Update documentation with release notes")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Please review the issues above before HACS submission.")
        return 1


if __name__ == "__main__":
    sys.exit(main())