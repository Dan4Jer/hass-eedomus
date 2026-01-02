#!/usr/bin/env python3
"""Generate documentation from code."""
import os
import json
from pathlib import Path


def generate_entity_documentation():
    """Generate documentation for all entities."""
    entities = [
        {"name": "sensor", "title": "Sensors"},
        {"name": "switch", "title": "Switches"},
        {"name": "light", "title": "Lights"},
        {"name": "cover", "title": "Covers"},
        {"name": "binary_sensor", "title": "Binary Sensors"},
        {"name": "climate", "title": "Climate"},
    ]
    
    docs = "# Entity Documentation\n\n"
    
    for entity in entities:
        file_path = f"custom_components/eedomus/{entity['name']}.py"
        if os.path.exists(file_path):
            docs += f"## {entity['title']}\n\n"
            docs += f"**File**: `{file_path}`\n\n"
            docs += f"**Purpose**: Manages {entity['name']} entities\n\n"
            docs += "---\n\n"
        else:
            docs += f"## {entity['title']}\n\n"
            docs += f"⚠️ File not found: `{file_path}`\n\n"
            docs += "---\n\n"
    
    with open("docs/ENTITY_DOCUMENTATION.md", "w") as f:
        f.write(docs)
    
    print("✅ Entity documentation generated")


def generate_manifest_info():
    """Generate info from manifest.json."""
    with open("custom_components/eedomus/manifest.json") as f:
        manifest = json.load(f)
    
    info = f"# Manifest Information\n\n"
    info += f"## {manifest['name']}\n\n"
    info += f"**Domain**: `{manifest['domain']}`\n\n"
    info += f"**Version**: `{manifest['version']}`\n\n"
    info += f"**Category**: `{manifest['category']}`\n\n"
    info += f"**IoT Class**: `{manifest['iot_class']}`\n\n"
    
    if "requirements" in manifest:
        info += "### Requirements\n\n"
        for req in manifest["requirements"]:
            info += f"- `{req}`\n"
    
    with open("docs/MANIFEST_INFO.md", "w") as f:
        f.write(info)
    
    print("✅ Manifest info generated")


def main():
    """Generate all documentation."""
    print("📚 Generating documentation...")
    
    # Create docs directory if not exists
    os.makedirs("docs", exist_ok=True)
    
    generate_entity_documentation()
    generate_manifest_info()
    
    print("\n🎉 Documentation generation complete!")
    print("Files created:")
    print("  - docs/ENTITY_DOCUMENTATION.md")
    print("  - docs/MANIFEST_INFO.md")


if __name__ == "__main__":
    main()