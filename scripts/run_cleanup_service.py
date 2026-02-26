#!/usr/bin/env python3
"""Script to trigger the eedomus cleanup service."""

import asyncio
import sys
import os

# Add the custom_components directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
custom_components_path = os.path.join(parent_dir, 'custom_components')
sys.path.insert(0, custom_components_path)

def show_usage():
    """Show usage instructions."""
    print("🧹 Eedomus Cleanup Service Trigger")
    print("\nThis script provides alternative ways to trigger the cleanup functionality")
    print("since the menu option is not available in older Home Assistant versions.")
    print()
    print("🔧 Usage Options:")
    print()
    print("1. Call the service directly from Home Assistant:")
    print("   - Go to Developer Tools > Services")
    print("   - Select service: eedomus.cleanup_unused_entities")
    print("   - Click 'Call Service'")
    print()
    print("2. Create an automation to run cleanup periodically:")
    print("   automation:")
    print("     - alias: 'Monthly Eedomus Cleanup'")
    print("     trigger:")
    print("       - platform: time")
    print("       at: '03:00:00'")
    print("     action:")
    print("       - service: eedomus.cleanup_unused_entities")
    print()
    print("3. Use the Home Assistant CLI:")
    print("   ha services call eedomus.cleanup_unused_entities")
    print()
    print("4. Create a script button in your dashboard:")
    print("   type: button")
    print("   name: Cleanup Eedomus Entities")
    print("   tap_action:")
    print("     action: call-service")
    print("     service: eedomus.cleanup_unused_entities")
    print()
    print("📊 What the cleanup does:")
    print("   • Removes disabled eedomus entities")
    print("   • Removes eedomus entities with 'deprecated' in unique_id")
    print("   • Provides detailed logging of all actions")
    print("   • Safe operation - only affects eedomus entities")
    print()
    print("💡 Tips:")
    print("   • Check Home Assistant logs for cleanup results")
    print("   • Run during low-usage periods")
    print("   • Backup your configuration before major cleanup operations")

if __name__ == "__main__":
    show_usage()
    
    print("\n🎯 The cleanup service is now available!")
    print("   You can call it using any of the methods shown above.")
    print("   No need to modify configuration files or restart Home Assistant.")
