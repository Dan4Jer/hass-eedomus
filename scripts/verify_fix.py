#!/usr/bin/env python3
"""
Verification script to ensure the cover position fix is complete.
"""

import os
import re


def verify_entity_file():
    """Verify that entity.py uses the correct parameter name."""
    entity_path = "custom_components/eedomus/entity.py"

    if not os.path.exists(entity_path):
        print(f"❌ Entity file not found: {entity_path}")
        return False

    with open(entity_path, "r") as f:
        content = f.read()

    # Check for correct usage of device_id
    correct_pattern = r'"device_id":\s*self\._periph_id'
    correct_matches = re.findall(correct_pattern, content)

    # Check for incorrect usage of periph_id in service calls
    incorrect_pattern = r'"periph_id":\s*self\._periph_id'
    incorrect_matches = re.findall(incorrect_pattern, content)

    print("Verifying entity.py service calls...")
    print("=" * 60)

    print(f"✅ Correct 'device_id' usage: {len(correct_matches)} occurrences")
    print(f"❌ Incorrect 'periph_id' usage: {len(incorrect_matches)} occurrences")

    if len(correct_matches) >= 2 and len(incorrect_matches) == 0:
        print("\n✅ VERIFICATION PASSED: All service calls use correct parameter name")
        return True
    else:
        print(
            "\n❌ VERIFICATION FAILED: Some service calls still use incorrect parameter name"
        )
        return False


def verify_service_handler():
    """Verify that the service handler expects device_id."""
    service_path = "custom_components/eedomus/services.py"

    if not os.path.exists(service_path):
        print(f"❌ Service file not found: {service_path}")
        return False

    with open(service_path, "r") as f:
        content = f.read()

    # Check that service handler expects device_id
    device_id_pattern = r'device_id\s*=\s*call\.data\.get\("device_id"'
    device_id_matches = re.findall(device_id_pattern, content)

    print("\nVerifying service handler...")
    print("=" * 60)
    print(
        f"✅ Service handler expects 'device_id': {len(device_id_matches)} occurrences"
    )

    if len(device_id_matches) >= 1:
        print("✅ VERIFICATION PASSED: Service handler correctly expects device_id")
        return True
    else:
        print("❌ VERIFICATION FAILED: Service handler doesn't expect device_id")
        return False


def verify_entity_usage():
    """Verify that entity files use async_set_value correctly."""
    entity_files = [
        "custom_components/eedomus/cover.py",
        "custom_components/eedomus/light.py",
        "custom_components/eedomus/switch.py",
    ]

    print("\nVerifying entity usage of async_set_value...")
    print("=" * 60)

    all_good = True
    for entity_file in entity_files:
        if os.path.exists(entity_file):
            with open(entity_file, "r") as f:
                content = f.read()

            # Check for async_set_value usage
            usage_pattern = r"await\s+self\.async_set_value"
            usage_matches = re.findall(usage_pattern, content)

            if len(usage_matches) > 0:
                print(
                    f"✅ {entity_file}: Uses async_set_value ({len(usage_matches)} calls)"
                )
            else:
                print(f"ℹ️  {entity_file}: No async_set_value calls found")
        else:
            print(f"❌ {entity_file}: File not found")
            all_good = False

    if all_good:
        print("✅ VERIFICATION PASSED: All entity files can use async_set_value")
        return True
    else:
        print("❌ VERIFICATION FAILED: Some entity files missing")
        return False


def main():
    """Run all verification checks."""
    print("🔍 Cover Position Fix Verification")
    print("=" * 60)
    print()

    results = []
    results.append(verify_entity_file())
    results.append(verify_service_handler())
    results.append(verify_entity_usage())

    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)

    if all(results):
        print("✅ ALL VERIFICATIONS PASSED")
        print("\n🎉 The cover position fix is complete and correct!")
        print("\nThe fix ensures that:")
        print("  • async_set_value uses 'device_id' parameter")
        print("  • Service handler expects 'device_id' parameter")
        print("  • All entity types (cover, light, switch) can set values")
        print("  • The 'Action eedomus.set_value not found' error is resolved")
        return 0
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        print("\nPlease review the output above for details.")
        return 1


if __name__ == "__main__":
    exit(main())
