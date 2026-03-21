# Frontend Structure for Eedomus Integration

## Standard Home Assistant 2026+ Frontend Structure

### Directory Layout

```
custom_components/eedomus/
├── __init__.py                # Main integration
├── options_flow.py           # Configuration flow (uses our rich editor)
├── frontend.yaml             # Frontend resource declaration
├── www/                      # Frontend assets
│   ├── eedomus-rich-editor.js # Main editor component
│   ├── manifest.json          # Frontend manifest
│   └── eedomus-frontend-config.json # Additional config
└── ...                        # Other integration files
```

### How Frontend Assets Are Loaded in HA 2026

1. **Automatic Loading**: Home Assistant 2026+ automatically scans for `www/` directories in custom integrations
2. **Resource Declaration**: The `frontend.yaml` file declares which assets should be loaded
3. **Custom UI**: The `options_flow.py` uses `custom_ui` parameter to specify our component

### Frontend Files

#### 1. `eedomus-rich-editor.js`
- **Type**: Web Component (Custom Element)
- **Registration**: Auto-registered via `customElements.define()`
- **Features**: UI/YAML toggle, basic configuration editing
- **Compatibility**: Uses Shadow DOM for encapsulation

#### 2. `manifest.json`
- **Purpose**: Frontend component metadata
- **Format**: Standard HA frontend manifest
- **Contains**: Version, name, compatibility info

#### 3. `eedomus-frontend-config.json`
- **Purpose**: Additional configuration
- **Format**: Custom JSON configuration
- **Contains**: Component-specific settings

#### 4. `frontend.yaml`
- **Purpose**: Declare frontend resources to HA
- **Format**: HA 2026+ frontend resource format
- **Contains**: URL, type, version of frontend assets

### Integration with Options Flow

The `options_flow.py` uses our rich editor like this:

```python
return self.async_show_form(
    step_id="init",
    data_schema=vol.Schema({}),
    description_placeholders={
        "content": "Click below to open the rich configuration editor"
    },
    custom_ui={
        "component": "eedomus-rich-editor",  # Our component name
        "config": {
            "entry_id": self.config_entry.entry_id
        }
    }
)
```

### URL Access Patterns

- **JS File**: `/local/custom_components/eedomus/www/eedomus-rich-editor.js`
- **In Browser**: Accessible via HA frontend when integration is loaded
- **Testing**: Can be tested by loading the HTML test page

### Compatibility Notes

✅ **Home Assistant 2026+**: Fully compatible
✅ **Custom Elements v1**: Standard web components
✅ **Shadow DOM**: Encapsulation support
✅ **ES6 Modules**: Modern JavaScript
✅ **No External Dependencies**: Pure vanilla JS

### Testing the Frontend

1. **Check files are in place**: `scripts/check_frontend_files.py`
2. **Test in browser**: Access the options flow in HA UI
3. **Manual test page**: `scripts/test_rich_editor.html`

### Deployment Notes

- Files in `www/` are automatically served by HA
- No need for manual frontend registration in most cases
- The `frontend.yaml` helps HA discover the resources

### References

- [HA Frontend Documentation](https://developers.home-assistant.io/docs/frontend/)
- [Custom UI Components](https://developers.home-assistant.io/docs/frontend/custom-ui/)
- [Web Components Standard](https://developer.mozilla.org/en-US/docs/Web/Web_Components)