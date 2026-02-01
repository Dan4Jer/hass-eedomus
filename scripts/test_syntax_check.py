#!/usr/bin/env python3
"""
Simple syntax check to verify that the NoneType safety corrections are syntactically correct.
"""

import sys
import ast
import os

def check_file_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the file to check syntax
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def check_method_exists(filepath, class_name, method_name):
    """Check if a method exists in a class."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple string search for the method definition
        if f'def {method_name}(self' in content:
            return True
        return False
    except Exception as e:
        print(f"Error checking {method_name} in {filepath}: {e}")
        return False

def main():
    """Run syntax checks."""
    print("Running syntax checks for NoneType safety corrections...")
    print("=" * 60)
    
    files_to_check = [
        'custom_components/eedomus/entity.py',
        'custom_components/eedomus/light.py',
        'custom_components/eedomus/cover.py',
        'custom_components/eedomus/sensor.py',
    ]
    
    all_passed = True
    
    for filepath in files_to_check:
        full_path = os.path.join('/Users/danjer/mistral/hass-eedomus', filepath)
        print(f"Checking {filepath}...")
        
        # Check syntax
        syntax_ok, error = check_file_syntax(full_path)
        if syntax_ok:
            print(f"  ✓ Syntax is valid")
        else:
            print(f"  ✗ Syntax error: {error}")
            all_passed = False
            continue
        
        # Check for the _get_periph_data method in entity.py
        if filepath == 'custom_components/eedomus/entity.py':
            has_method = check_method_exists(full_path, 'EedomusEntity', '_get_periph_data')
            if has_method:
                print(f"  ✓ _get_periph_data method found")
            else:
                print(f"  ✗ _get_periph_data method not found")
                all_passed = False
        
        # Check for safe access patterns
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count remaining direct accesses (should be reduced)
        direct_accesses = content.count('self.coordinator.data[')
        safe_accesses = content.count('_get_periph_data()')
        
        print(f"  • Direct coordinator.data accesses: {direct_accesses}")
        print(f"  • Safe _get_periph_data() calls: {safe_accesses}")
        
        if direct_accesses > 0:
            print(f"  ⚠ Still has {direct_accesses} direct accesses that might need review")
        
        print()
    
    print("=" * 60)
    if all_passed:
        print("✓ All syntax checks passed!")
        print("✓ NoneType safety corrections appear to be syntactically correct.")
        return 0
    else:
        print("✗ Some syntax checks failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())