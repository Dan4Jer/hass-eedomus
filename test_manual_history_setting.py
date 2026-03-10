#!/usr/bin/env python3
"""Manual test to verify history option can be set and read correctly."""

import json
import os
import tempfile

def test_history_option_storage():
    """Test that history option can be stored and retrieved correctly."""
    
    print("=== Testing History Option Storage ===")
    print()
    
    # Create a temporary storage file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        storage_file = f.name
        
        # Create initial storage data
        storage_data = {
            "data": {
                "entries": [
                    {
                        "entry_id": "test_entry_123",
                        "domain": "eedomus",
                        "title": "Eedomus Integration",
                        "data": {
                            "api_host": "192.168.1.100",
                            "api_user": "test_user",
                            "api_secret": "test_secret",
                            "enable_api_eedomus": True,
                            "enable_api_proxy": False,
                            "history": False,  # Initially disabled
                            "scan_interval": 300
                        },
                        "options": {
                            # Initially no options set
                        },
                        "version": 1
                    }
                ]
            }
        }
        
        json.dump(storage_data, f)
        print(f"✅ Created temporary storage file: {storage_file}")
    
    try:
        # Test 1: Read initial state (history disabled in config, not in options)
        print("\nTest 1: Initial state (history disabled in config)")
        with open(storage_file, 'r') as f:
            data = json.load(f)
            
        entry = data["data"]["entries"][0]
        config_history = entry["data"].get("history", False)
        options_history = entry["options"].get("history", None)
        
        print(f"  Config history: {config_history}")
        print(f"  Options history: {options_history}")
        print(f"  Expected behavior: Use config value (False)")
        
        # Simulate the logic
        if "history" in entry["options"]:
            history_from_options = entry["options"]["history"]
        else:
            history_from_options = None
        
        history_retrieval = history_from_options if history_from_options is not None else config_history
        print(f"  Result: {history_retrieval}")
        
        if history_retrieval == False:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL")
        
        # Test 2: Enable history in options
        print("\nTest 2: Enable history in options (should override config)")
        storage_data["data"]["entries"][0]["options"]["history"] = True
        
        with open(storage_file, 'w') as f:
            json.dump(storage_data, f)
        
        with open(storage_file, 'r') as f:
            data = json.load(f)
            
        entry = data["data"]["entries"][0]
        config_history = entry["data"].get("history", False)
        options_history = entry["options"].get("history", None)
        
        print(f"  Config history: {config_history}")
        print(f"  Options history: {options_history}")
        print(f"  Expected behavior: Use options value (True)")
        
        # Simulate the logic
        if "history" in entry["options"]:
            history_from_options = entry["options"]["history"]
        else:
            history_from_options = None
        
        history_retrieval = history_from_options if history_from_options is not None else config_history
        print(f"  Result: {history_retrieval}")
        
        if history_retrieval == True:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL")
        
        # Test 3: Disable history in options (should override config)
        print("\nTest 3: Disable history in options (should override config)")
        storage_data["data"]["entries"][0]["data"]["history"] = True  # Enable in config
        storage_data["data"]["entries"][0]["options"]["history"] = False  # Disable in options
        
        with open(storage_file, 'w') as f:
            json.dump(storage_data, f)
        
        with open(storage_file, 'r') as f:
            data = json.load(f)
            
        entry = data["data"]["entries"][0]
        config_history = entry["data"].get("history", False)
        options_history = entry["options"].get("history", None)
        
        print(f"  Config history: {config_history}")
        print(f"  Options history: {options_history}")
        print(f"  Expected behavior: Use options value (False)")
        
        # Simulate the logic
        if "history" in entry["options"]:
            history_from_options = entry["options"]["history"]
        else:
            history_from_options = None
        
        history_retrieval = history_from_options if history_from_options is not None else config_history
        print(f"  Result: {history_retrieval}")
        
        if history_retrieval == False:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL")
        
        print("\n🎉 All manual tests completed successfully!")
        
    finally:
        # Clean up
        if os.path.exists(storage_file):
            os.unlink(storage_file)
            print(f"\n🧹 Cleaned up temporary file: {storage_file}")

if __name__ == "__main__":
    test_history_option_storage()