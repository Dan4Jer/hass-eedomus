/**
 * Eedomus Rich Editor - Minimal Version
 * Provides UI and YAML editing modes for Eedomus configuration
 * 
 * Version: 1.0 (Minimal)
 * Compatible with Home Assistant 2026+
 */

class EedomusRichEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.hass = null;
    this.config = {};
    this.currentMode = 'ui'; // 'ui' or 'yaml'
    this.yamlContent = '';
  }

  setConfig(config) {
    if (!config) return;
    this.config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.config) {
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (this.hass) {
      this._render();
    }
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  _render() {
    if (!this.shadowRoot) return;

    this.shadowRoot.innerHTML = `
      <style>
        .editor-container {
          font-family: var(--ha-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
          max-width: 800px;
          margin: 0 auto;
          padding: 16px;
        }
        
        .toolbar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }
        
        .mode-toggle {
          display: flex;
          gap: 4px;
          margin-bottom: 16px;
        }
        
        .mode-button {
          padding: 8px 16px;
          border: 1px solid #ccc;
          background: white;
          cursor: pointer;
          border-radius: 4px;
          transition: all 0.2s;
        }
        
        .mode-button.active {
          background: var(--primary-color, #039be5);
          color: white;
          border-color: var(--primary-color, #039be5);
        }
        
        .editor-content {
          border: 1px solid #ddd;
          border-radius: 4px;
          min-height: 400px;
          padding: 16px;
          background: white;
        }
        
        textarea.yaml-editor {
          width: 100%;
          height: 380px;
          font-family: monospace;
          border: none;
          resize: vertical;
          outline: none;
          padding: 8px;
        }
        
        .ui-editor {
          padding: 8px;
        }
        
        .status-message {
          padding: 8px;
          margin: 8px 0;
          border-radius: 4px;
          display: none;
        }
        
        .status-success {
          background: #d4edda;
          color: #155724;
          display: block;
        }
        
        .status-error {
          background: #f8d7da;
          color: #721c24;
          display: block;
        }
        
        .section-header {
          font-size: 1.1em;
          font-weight: 500;
          margin: 16px 0 8px 0;
          color: var(--primary-text-color);
        }
        
        .form-group {
          margin-bottom: 16px;
        }
        
        .form-group label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
        }
        
        .form-group input,
        .form-group select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-family: inherit;
        }
        
        button {
          padding: 8px 16px;
          background: var(--primary-color, #039be5);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-family: inherit;
        }
        
        button:disabled {
          background: #cccccc;
          cursor: not-allowed;
        }
      </style>
      
      <div class="editor-container">
        <div class="toolbar">
          <div class="mode-toggle">
            <button class="mode-button ${this.currentMode === 'ui' ? 'active' : ''}" id="ui-mode">
              UI Mode
            </button>
            <button class="mode-button ${this.currentMode === 'yaml' ? 'active' : ''}" id="yaml-mode">
              YAML Mode
            </button>
          </div>
        </div>
        
        <div id="status-message" class="status-message"></div>
        
        <div class="editor-content">
          ${this.currentMode === 'yaml' ? this._renderYamlEditor() : this._renderUiEditor()}
        </div>
        
        <div class="toolbar" style="margin-top: 16px;">
          <button id="save-btn" disabled>Save Configuration</button>
          <button id="preview-btn">Preview YAML</button>
        </div>
      </div>
    `;

    // Add event listeners
    this.shadowRoot.getElementById('ui-mode').addEventListener('click', () => {
      this.currentMode = 'ui';
      this._render();
    });

    this.shadowRoot.getElementById('yaml-mode').addEventListener('click', () => {
      this.currentMode = 'yaml';
      this._render();
    });

    this.shadowRoot.getElementById('preview-btn').addEventListener('click', () => {
      this._showPreview();
    });
  }

  _renderYamlEditor() {
    return `
      <div class="yaml-editor-container">
        <textarea class="yaml-editor" id="yaml-editor">${this.yamlContent || this._configToYaml()}</textarea>
      </div>
    `;
  }

  _renderUiEditor() {
    return `
      <div class="ui-editor">
        <div class="section-header">Basic Configuration</div>
        
        <div class="form-group">
          <label for="config-name">Configuration Name</label>
          <input type="text" id="config-name" value="${this.config.name || ''}" placeholder="My Eedomus Config">
        </div>
        
        <div class="section-header">Devices</div>
        <p>Device configuration will be added in the full version.</p>
        
        <div class="section-header">Advanced Settings</div>
        <p>Advanced options will be available in the complete implementation.</p>
      </div>
    `;
  }

  _configToYaml() {
    // Simple YAML conversion for minimal version
    let yaml = '# Eedomus Configuration\n';
    yaml += '# Generated by Rich Editor (Minimal Version)\n';
    yaml += '\n';
    yaml += 'custom_devices:\n';
    
    // Add sample device if none exist
    if (!this.config.custom_devices || this.config.custom_devices.length === 0) {
      yaml += '  - device_id: "sample_device"\n';
      yaml += '    device_type: "light"\n';
      yaml += '    name: "Sample Light"\n';
      yaml += '    state: "on"\n';
    } else {
      this.config.custom_devices.forEach((device, index) => {
        yaml += `  - device_id: "${device.device_id || 'unknown'}"\n`;
        yaml += `    device_type: "${device.device_type || 'light'}"\n`;
        yaml += `    name: "${device.name || 'Unnamed Device'}"\n`;
        if (device.state) {
          yaml += `    state: "${device.state}"\n`;
        }
      });
    }
    
    return yaml;
  }

  _showPreview() {
    const statusElement = this.shadowRoot.getElementById('status-message');
    
    if (this.currentMode === 'yaml') {
      // Get YAML content
      const yamlContent = this.shadowRoot.getElementById('yaml-editor').value;
      this.yamlContent = yamlContent;
      
      statusElement.textContent = 'YAML content captured for preview.';
      statusElement.className = 'status-message status-success';
      
    } else {
      // Show YAML preview of UI configuration
      const yamlPreview = this._configToYaml();
      
      statusElement.textContent = 'YAML Preview generated from UI configuration.';
      statusElement.className = 'status-message status-success';
      
      // Switch to YAML mode to show preview
      this.currentMode = 'yaml';
      this.yamlContent = yamlPreview;
      this._render();
    }
  }

  // Method to get current configuration as YAML
  getCurrentYaml() {
    if (this.currentMode === 'yaml') {
      return this.shadowRoot.getElementById('yaml-editor')?.value || this.yamlContent;
    } else {
      return this._configToYaml();
    }
  }

  // Method to update configuration from external source
  updateConfig(config) {
    this.config = config;
    if (this.currentMode === 'ui') {
      this._render();
    }
  }
}

// Register the custom element
if (!customElements.get('eedomus-rich-editor')) {
  customElements.define('eedomus-rich-editor', EedomusRichEditor);
  console.log('Eedomus Rich Editor (Minimal) registered');
} else {
  console.log('Eedomus Rich Editor already registered');
}