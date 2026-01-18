# Eedomus Table Generation Scripts

This directory contains scripts for generating device mapping tables from the eedomus API.

## 📁 Scripts Available

### `generate_simple_table.py`
**Purpose**: Generate a simple but complete device table from eedomus API

**Features**:
- Connects to eedomus API using standard urllib
- Handles multiple response encodings (UTF-8, ISO-8859-1, etc.)
- Simplifies Z-Wave classes to base numbers only
- Maps devices to Home Assistant entities based on usage_id
- Generates both Markdown table and JSON data

**Usage**:
```bash
# Set your credentials as environment variables
export EEDOMUS_API_HOST="your_eedomus_box_ip"
export EEDOMUS_API_USER="your_api_username"
export EEDOMUS_API_SECRET="your_api_secret"

# Run the script
python generate_simple_table.py

# Or modify the defaults in the script
```

## 🎯 Output Files

The scripts generate two types of files:

1. **Markdown Table** (`simple_device_table.md`)
   - Human-readable table with all devices
   - Columns: `parent_id/periph_id`, `usage_id:usage_name`, `SUPPORTED_CLASSES`, `ha_type:ha_subtype`, `name`, `room`
   - Sorted by periph_id

2. **JSON Data** (`simple_device_data.json`)
   - Complete raw data for all devices
   - Includes all original API fields plus mapping information
   - Useful for programmatic processing

## 🔧 Configuration

All scripts use environment variables for configuration:

```bash
export EEDOMUS_API_HOST="your_eedomus_box_ip"
export EEDOMUS_API_USER="your_api_username"
export EEDOMUS_API_SECRET="your_api_secret"
```

Or modify the default values directly in each script.

## 📊 Table Structure

The generated table has the following columns:

| Column | Description |
|--------|-------------|
| **parent_id/periph_id** | Combined parent and device ID (shows hierarchy) |
| **usage_id:usage_name** | Device usage ID and descriptive name |
| **SUPPORTED_CLASSES** | Simplified Z-Wave classes (base numbers only) |
| **ha_type:ha_subtype** | Mapped Home Assistant entity type and subtype |
| **name** | Device name from eedomus |
| **room** | Room where device is located |

## 🚀 Usage Examples

### Generate table with environment variables
```bash
export EEDOMUS_API_HOST="192.168.1.10"
export EEDOMUS_API_USER="api_user"
export EEDOMUS_API_SECRET="api_secret"
python generate_simple_table.py
```

### Generate table with modified script defaults
```bash
# Edit the script to set your credentials
nano scripts/generate_simple_table.py

# Then run it
python scripts/generate_simple_table.py
```

### Process the generated data
```bash
# View the markdown table
cat simple_device_table.md

# Analyze the JSON data
python -c "import json; data=json.load(open('simple_device_data.json')); print(f'Total devices: {len(data)}')"
```

## 📋 Device Mapping

The scripts use a comprehensive usage_id mapping system:

| usage_id | HA Entity | Description |
|----------|-----------|-------------|
| 1 | light:dimmable | Light devices |
| 2, 4 | switch | Basic switches |
| 7 | sensor:temperature | Temperature sensors |
| 37 | binary_sensor:motion | Motion detectors |
| 48 | cover:shutter | Shutters/blinds |
| 27 | binary_sensor:smoke | Smoke detectors |
| 36 | binary_sensor:moisture | Flood detectors |
| 19, 20 | climate:fil_pilote | Fil pilote heating |
| 26 | sensor:energy | Energy meters |

## 🔒 Security Notes

- **No sensitive data is stored** in the scripts
- **API credentials** are read from environment variables
- **Generated files** contain only device metadata, no credentials
- **Scripts use read-only API calls** (no modifications to your eedomus box)

## 📚 Reference Files

The reference files (`simple_device_table.md` and `simple_device_data.json`) in the parent directory contain a complete mapping of 176 devices from a real eedomus installation. These files serve as:

- **Mapping reference** for development
- **Test data** for validation
- **Documentation** of real device structures
- **Debugging aid** for troubleshooting

## 🎓 Development Notes

- Scripts are designed to be **safe** (read-only operations)
- Error handling is **comprehensive** (multiple encodings, data formats)
- Logging is **detailed** for troubleshooting
- Code is **well-commented** for maintainability

## 🤝 Contributing

To improve these scripts:

1. **Add more usage_id mappings** in the `map_device()` function
2. **Enhance error handling** for edge cases
3. **Add more statistics** to the output
4. **Improve documentation** and examples
5. **Add unit tests** for critical functions

## 📖 Related Files

- `docs/DEVICE_MAPPING_TABLE.md` - Documentation on device mapping
- `custom_components/eedomus/devices_class_mapping.py` - Main mapping logic
- `custom_components/eedomus/entity.py` - Entity base class with mapping

## 💡 Tips

1. **Start with small tests** before running on full installations
2. **Check API connectivity** with `ping` or `curl` first
3. **Review logs** for any warnings or errors
4. **Validate output** by spot-checking a few devices
5. **Use reference files** as examples for expected output