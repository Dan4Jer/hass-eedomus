"""Main test file to run all entity tests."""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_components/eedomus")))


async def main():
    """Run all tests."""
    print("🧪 Running Eedomus integration tests...")

    # Run pytest for all test files
    exit_code = pytest.main(
        [
            "test_cover.py",
            "test_switch.py",
            "test_light.py",
            "test_sensor.py",
            "test_energy_sensor.py",
            "test_integration.py",
            "test_color_mode_fix.py",
            "-v",
            "--tb=short",
        ]
    )

    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
