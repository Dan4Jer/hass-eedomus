#!/usr/bin/env python3

"""
Vibe CLI script for eedomus history import.

This script provides a command-line interface to import historical data from eedomus
devices into Home Assistant using the optimized Recorder API method.

Usage:
    python3 eedomus_import_history.py --device-id <ID> [--start <ISO_TS>] [--end <ISO_TS>] [--batch-size <SIZE>] [--dry-run] [--resume]

Examples:
    # Import history for device 12345 from the beginning
    python3 eedomus_import_history.py --device-id 12345
    
    # Import history for a specific time range
    python3 eedomus_import_history.py --device-id 12345 --start "2024-01-01T00:00:00" --end "2024-01-31T23:59:59"
    
    # Import with custom batch size
    python3 eedomus_import_history.py --device-id 12345 --batch-size 100
    
    # Dry run (no actual import)
    python3 eedomus_import_history.py --device-id 12345 --dry-run
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

import aiohttp

# Configuration
HA_URL = "http://homeassistant.local:8123"
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI5ZmYyY2ZjZWY0MDI0MTAyOTE1Y2RmMDE3NmI0Y2ZiNSIsImlhdCI6MTc3MTAxODYyNSwiZXhwIjoyMDg2Mzc4NjI1fQ.5I5m9mPDTxPCqDCG8Tj4Ca2jUX6U1__hnQdXDeacDqA"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

async def call_eedomus_service(device_id: str, start_time: str = None, end_time: str = None, 
                             batch_size: int = 200, dry_run: bool = False) -> dict:
    """Call the eedomus.import_history service via Home Assistant API."""
    
    service_data = {
        "device_id": device_id,
        "batch_size": batch_size
    }
    
    if start_time:
        service_data["start_time"] = start_time
    if end_time:
        service_data["end_time"] = end_time
    
    if dry_run:
        print(f"🔍 [DRY RUN] Would call eedomus.import_history with: {service_data}")
        return {"status": "dry_run", "device_id": device_id, "imported": 0}
    
    url = f"{HA_URL}/api/services/eedomus/import_history"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=service_data, timeout=300) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
    except Exception as err:
        raise Exception(f"Failed to call service: {err}")

async def get_device_info(device_id: str) -> dict:
    """Get information about a specific device."""
    try:
        url = f"{HA_URL}/api/states/sensor.eedomus_{device_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                return {}
    except Exception:
        return {}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Eedomus History Import Tool - Import historical data from eedomus devices"
    )
    
    parser.add_argument("--device-id", required=True, help="Eedomus device ID")
    parser.add_argument("--start", help="Start timestamp in ISO format (e.g., 2024-01-01T00:00:00)")
    parser.add_argument("--end", help="End timestamp in ISO format (e.g., 2024-01-31T23:59:59)")
    parser.add_argument("--batch-size", type=int, default=200, 
                       help="Batch size for import (default: 200)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Dry run - show what would be done without actual import")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from last saved progress")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    return parser.parse_args()

def validate_timestamp(timestamp: str) -> bool:
    """Validate timestamp format."""
    if not timestamp:
        return True
    try:
        datetime.fromisoformat(timestamp)
        return True
    except ValueError:
        return False

async def main():
    """Main function."""
    args = parse_arguments()
    
    # Validate timestamp format
    if args.start and not validate_timestamp(args.start):
        print(f"❌ Invalid start timestamp format: {args.start}")
        print("   Expected format: YYYY-MM-DDTHH:MM:SS")
        sys.exit(1)
    
    if args.end and not validate_timestamp(args.end):
        print(f"❌ Invalid end timestamp format: {args.end}")
        print("   Expected format: YYYY-MM-DDTHH:MM:SS")
        sys.exit(1)
    
    print("🚀 Eedomus History Import Tool")
    print("=" * 50)
    print(f"📥 Device ID: {args.device_id}")
    print(f"📅 Start: {args.start or 'Beginning'}")
    print(f"📅 End: {args.end or 'Now'}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"🔍 Mode: {'DRY RUN' if args.dry_run else 'ACTUAL IMPORT'}")
    print()
    
    # Get device info
    device_info = await get_device_info(args.device_id)
    if device_info:
        friendly_name = device_info.get("attributes", {}).get("friendly_name", "Unknown")
        print(f"📊 Device: {friendly_name}")
    else:
        print(f"⚠️ Device info not available (may not exist yet)")
    
    print()
    print("🔄 Starting import process...")
    
    try:
        result = await call_eedomus_service(
            device_id=args.device_id,
            start_time=args.start,
            end_time=args.end,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        
        print()
        print("✅ Import completed successfully!")
        print(f"   Status: {result.get('status')}")
        print(f"   Device: {result.get('device_id')}")
        print(f"   Imported: {result.get('imported', 0)} data points")
        
        if args.verbose and result.get('status') == 'success':
            print()
            print("💡 Tips:")
            print("   - Check Home Assistant logs for detailed import information")
            print("   - Historical data should now be visible in the history graphs")
            print("   - Use the eedomus.history_progress sensor to monitor progress")
        
    except Exception as err:
        print()
        print(f"❌ Import failed: {err}")
        print()
        print("💡 Troubleshooting tips:")
        print("   - Verify Home Assistant is running and accessible")
        print("   - Check the API token is valid")
        print("   - Verify the device ID exists in eedomus")
        print("   - Check Home Assistant logs for detailed error information")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())